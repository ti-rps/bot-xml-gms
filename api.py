# api.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from tasks import celery_app, run_automation_task
from celery.result import AsyncResult

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
        "result": task_result.result if task_result.ready() else None
    }
    return response

@app.post("/cancel/{task_id}", status_code=200, summary="Cancela a execução de uma tarefa")
def cancel_task(task_id: str):
    celery_app.control.revoke(task_id, terminate=True, signal='SIGTERM')
    return {"task_id": task_id, "message": "Sinal de cancelamento enviado para a tarefa."}