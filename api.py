# api.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from tasks import celery_app, run_automation_task
from celery.result import AsyncResult
import time
import json

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
    gms_login_url: str
    gms_user: Optional[str] = None
    gms_password: Optional[str] = None

app = FastAPI(
    title="Bot-XML-GMS API",
    description="API para enfileirar, monitorar e cancelar tarefas de extração de XMLs."
)

@app.post("/execute", status_code=202, summary="Enfileira uma nova tarefa de automação")
def execute_automation(params: AutomationParameters):
    task = run_automation_task.delay(params.model_dump())
    return {"task_id": task.id, "message": "Automação enfileirada para execução."}


@app.get("/status/{task_id}", status_code=200, summary="Verifica o status de uma tarefa")
def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "info": task_result.info if task_result.info else {},
        "result": task_result.result if task_result.ready() else None
    }
    
    if hasattr(task_result, 'info') and isinstance(task_result.info, dict):
        response["meta"] = task_result.info
    
    return response


@app.get("/logs/{task_id}", status_code=200, summary="Obtém os logs de uma tarefa")
def get_task_logs(task_id: str):
    log_key = f"task_logs:{task_id}"
    redis_client = celery_app.backend.client
    
    logs = redis_client.lrange(log_key, 0, -1)
    
    if not logs:
        return {
            "task_id": task_id,
            "logs": [],
            "message": "Nenhum log disponível ainda"
        }
    
    decoded_logs = [log.decode('utf-8') if isinstance(log, bytes) else log for log in logs]
    
    return {
        "task_id": task_id,
        "logs": decoded_logs,
        "total_lines": len(decoded_logs)
    }


@app.get("/logs/{task_id}/stream", summary="Stream de logs em tempo real")
async def stream_task_logs(task_id: str):
    
    async def log_generator():
        log_key = f"task_logs:{task_id}"
        redis_client = celery_app.backend.client
        last_index = 0
        task_result = AsyncResult(task_id, app=celery_app)
        
        yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id})}\n\n"
        
        while True:
            logs = redis_client.lrange(log_key, last_index, -1)
            
            if logs:
                for log in logs:
                    decoded_log = log.decode('utf-8') if isinstance(log, bytes) else log
                    yield f"data: {json.dumps({'type': 'log', 'message': decoded_log})}\n\n"
                    last_index += 1
            
            if task_result.ready():
                status = task_result.status
                result = task_result.result if task_result.successful() else str(task_result.info)
                yield f"data: {json.dumps({'type': 'completed', 'status': status, 'result': result})}\n\n"
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/cancel/{task_id}", status_code=200, summary="Cancela a execução de uma tarefa")
def cancel_task(task_id: str):
    celery_app.control.revoke(task_id, terminate=True, signal='SIGTERM')
    return {"task_id": task_id, "message": "Sinal de cancelamento enviado para a tarefa."}


@app.get("/logs/{task_id}/tail", summary="Obtém as últimas N linhas de log")
def tail_logs(task_id: str, lines: int = 50):
    log_key = f"task_logs:{task_id}"
    redis_client = celery_app.backend.client
    
    logs = redis_client.lrange(log_key, -lines, -1)
    
    if not logs:
        return {
            "task_id": task_id,
            "logs": [],
            "message": "Nenhum log disponível"
        }
    
    decoded_logs = [log.decode('utf-8') if isinstance(log, bytes) else log for log in logs]
    
    return {
        "task_id": task_id,
        "logs": decoded_logs,
        "lines_returned": len(decoded_logs)
    }