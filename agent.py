# agent.py
from flask import Flask, request, jsonify
import subprocess
import json
import tempfile
import os
import traceback
from datetime import datetime

app = Flask(__name__)

@app.route('/execute', methods=['POST'])
def execute_automation():
    print(f"[{datetime.now()}] Requisição de execução recebida.")
    
    try:
        data = request.get_json()
        script_path = data['script_path']
        parameters = data['parameters']
    except Exception as e:
        print(f"Erro ao ler o JSON da requisição: {e}")
        return jsonify({"status": "Falha", "log_data": f"JSON inválido ou ausente: {e}"}), 400

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as temp_file:
        json.dump(parameters, temp_file, ensure_ascii=False, indent=4)
        params_file_path = temp_file.name

    print(f"Parâmetros salvos em: {params_file_path}")
    print(f"Executando script: {script_path}")

    log_data = ""
    final_status = "Falha"

    try:
        process = subprocess.run(
            ['python3', script_path, '--params-file', params_file_path],
            capture_output=True,
            check=True
        )
        final_status = "Sucesso"
        log_data = process.stdout.decode('utf-8', errors='replace')
        print("Execução concluída com sucesso.")

    except subprocess.CalledProcessError as e:
        stdout_log = e.stdout.decode('utf-8', errors='replace')
        stderr_log = e.stderr.decode('utf-8', errors='replace')
        log_data = f"--- SAÍDA PADRÃO (STDOUT) ---\n{stdout_log}\n\n--- SAÍDA DE ERRO (STDERR) ---\n{stderr_log}"
        print(f"O script retornou um erro.")
    
    except Exception as e:
        log_data = f"Falha crítica no Agente ao tentar executar o script:\n{traceback.format_exc()}"
        print(log_data)
    
    finally:
        os.remove(params_file_path)

    return jsonify({
        "status": final_status,
        "log_data": log_data
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)