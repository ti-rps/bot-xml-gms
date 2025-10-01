# agent.py
import subprocess
import json
import tempfile
import os
import traceback
import uuid
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AutomationParameters(BaseModel):
    headless: bool = True
    stores: List[int]
    document_type: str
    emitter: str
    operation_type: str
    file_type: str
    invoice_situation: str
    start_date: str 
    end_date: str
    gms_user: str
    gms_password: str
    gms_login_url: str


class ExecutionRequest(BaseModel):
    parameters: AutomationParameters


class JobStatus(BaseModel):
    status: str
    log_data: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

app = FastAPI(
    title="Bot-XML-GMS Agent",
    description="Agente para execução e monitoramento da automação de extração de XMLs."
)

# Um dicionário em memória para "simular" um banco de dados de jobs.
# Em produção, isso poderia ser substituído por Redis ou um BD.
jobs: Dict[str, JobStatus] = {}


def run_automation_background(job_id: str, params: dict):
    log_data = ""
    summary = None
    error_details = None
    
    jobs[job_id].status = "rodando"
    jobs[job_id].started_at = datetime.now()

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as temp_file:
        json.dump(params, temp_file, ensure_ascii=False, indent=4)
        params_file_path = temp_file.name

    try:
        process = subprocess.run(
            ['python3', "./main.py", '--params-file', params_file_path],
            capture_output=True,
            check=True,
            text=True, 
            encoding='utf-8'
        )
        
        log_data = process.stdout
        
        try:
            summary_str = log_data.split("---SUMMARY_START---")[1].split("---SUMMARY_END---")[0]
            summary = json.loads(summary_str)
            jobs[job_id].status = "concluído"
        except (IndexError, json.JSONDecodeError):
            jobs[job_id].status = "concluído_sem_resumo"
            log_data += "\n\nAVISO: O resumo da execução não foi encontrado na saída do processo."

    except subprocess.CalledProcessError as e:
        jobs[job_id].status = "falhou"
        stdout_log = e.stdout or "N/A"
        stderr_log = e.stderr or "N/A"
        log_data = f"--- SAÍDA PADRÃO (STDOUT) ---\n{stdout_log}\n\n--- SAÍDA DE ERRO (STDERR) ---\n{stderr_log}"
        error_details = stderr_log

    except Exception:
        jobs[job_id].status = "falhou"
        error_details = f"Falha crítica no Agente ao tentar executar o script:\n{traceback.format_exc()}"
        log_data = error_details
    
    finally:
        os.remove(params_file_path)
        jobs[job_id].log_data = log_data
        jobs[job_id].summary = summary
        jobs[job_id].error_details = error_details
        jobs[job_id].finished_at = datetime.now()

@app.post("/execute", status_code=202)
def execute_automation(
    request: ExecutionRequest, 
    background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = JobStatus(status="pendente")
    
    background_tasks.add_task(run_automation_background, job_id, request.parameters.model_dump())
    
    return {"job_id": job_id, "message": "Execução da automação iniciada."}


@app.get("/status/{job_id}", response_model=JobStatus)
def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado.")
    
    if job.status in ["pendente", "rodando"]:
         return JobStatus(status=job.status, started_at=job.started_at)
         
    return job