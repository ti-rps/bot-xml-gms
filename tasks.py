import subprocess
import json
import tempfile
import os
import time
from celery import Celery
from celery.exceptions import Terminated

celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@celery_app.task(bind=True, name='run_automation_task')
def run_automation_task(self, params: dict):
    summary = None
    log_data = ""

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as temp_file:
        json.dump(params, temp_file, ensure_ascii=False, indent=4)
        params_file_path = temp_file.name

    process = None
    try:
        process = subprocess.Popen(
            ['python3', "-u", "main.py", '--params-file', params_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        while process.poll() is None:
            time.sleep(1)

        stdout, stderr = process.communicate()
        log_data = stdout

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, stdout, stderr)
            
        try:
            summary_str = log_data.split("---SUMMARY_START---")[1].split("---SUMMARY_END---")[0]
            summary = json.loads(summary_str)
        except (IndexError, json.JSONDecodeError):
            summary = {"warning": "O resumo da execução não foi encontrado na saída."}

        return {
            "status": "concluído",
            "summary": summary,
            "log": log_data
        }

    except Terminated:
        print(f"TAREFA {self.request.id} FOI CANCELADA! Encerrando o subprocesso...")
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        raise

    except subprocess.CalledProcessError as e:
        log_data = f"--- STDOUT ---\n{e.stdout}\n\n--- STDERR ---\n{e.stderr}"
        raise Exception(f"A automação falhou com código de saída {e.returncode}. Log: {log_data}")

    except Exception as exc:
        if process and process.poll() is None:
            process.kill()
        raise exc
    
    finally:
        if os.path.exists(params_file_path):
            os.remove(params_file_path)