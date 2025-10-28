import logging
import logging.config
import json
import time
import signal
import sys
from typing import Dict, Optional
import pika
import requests
from pika import PlainCredentials, ConnectionParameters, BlockingConnection
from pathlib import Path

from config import settings
from src.core.bot_runner import BotRunner

logging.config.dictConfig(settings.get_log_config())
logger = logging.getLogger(__name__)


class RabbitMQWorker:
    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.should_stop = False
        
        self.rabbitmq_host = settings.rabbitmq_host
        self.rabbitmq_port = settings.rabbitmq_port
        self.rabbitmq_user = settings.rabbitmq_user
        self.rabbitmq_password = settings.rabbitmq_password
        self.queue_name = settings.rabbitmq_queue
        
        self.maestro_url = settings.maestro_api_url
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Recebido sinal {signum}. Encerrando gracefully...")
        self.should_stop = True
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        sys.exit(0)
    
    def connect(self):
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Conectando ao RabbitMQ em {self.rabbitmq_host}:{self.rabbitmq_port}...")
                
                credentials = pika.PlainCredentials(
                    self.rabbitmq_user,
                    self.rabbitmq_password
                )
                
                parameters = pika.ConnectionParameters(
                    host=self.rabbitmq_host,
                    port=self.rabbitmq_port,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
                
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                self.channel.queue_declare(queue=self.queue_name, durable=True)
                
                self.channel.basic_qos(prefetch_count=1)
                
                logger.info(f"✅ Conectado ao RabbitMQ. Aguardando mensagens na fila '{self.queue_name}'...")
                return
                
            except Exception as e:
                logger.error(f"Falha ao conectar (tentativa {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Aguardando {retry_delay}s antes de tentar novamente...")
                    time.sleep(retry_delay)
                else:
                    raise
    
    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> bool:
        try:
            url = f"{self.maestro_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            logger.debug(f"Fazendo requisição {method} para {url}")
            
            response = requests.request(
                method=method,
                url=url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201, 204]:
                logger.debug(f"✅ Requisição bem sucedida: {method} {endpoint}")
                return True
            else:
                logger.warning(f"⚠️ Falha na requisição. HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao fazer requisição para Maestro: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao fazer requisição: {e}")
            return False
    
    def report_status_start(self, job_id: str) -> bool:
        endpoint = f"/api/v1/worker/jobs/{job_id}/start"
        logger.info(f"📤 Reportando início do job {job_id}")
        return self._make_request("POST", endpoint)
    
    def report_log(self, job_id: str, level: str, message: str) -> bool:
        endpoint = f"/api/v1/worker/jobs/{job_id}/log"
        payload = {
            "level": level,
            "message": message
        }
        logger.debug(f"📝 Enviando log [{level}]: {message}")
        return self._make_request("POST", endpoint, payload)
    
    def report_finish(self, job_id: str, status: str, result_data: Dict) -> bool:
        endpoint = f"/api/v1/worker/jobs/{job_id}/finish"
        payload = {
            "status": status,
            "result": result_data
        }
        logger.info(f"🏁 Reportando finalização do job {job_id} com status: {status}")
        return self._make_request("POST", endpoint, payload)
    
    def process_message(self, ch, method, properties, body):
        job_id = None
        
        try:
            message = json.loads(body)
            
            job_id = message.get("job_id")
            
            logger.info(f"📨 Mensagem recebida: {job_id}")
            logger.info(f"Payload: {json.dumps(message, indent=2)}")
            
            params = message.get("parameters", {})
            
            if not job_id:
                raise ValueError("Campo obrigatório 'job_id' não encontrado na mensagem")
            
            required_fields = ['stores', 'document_type', 'start_date', 'end_date', 'gms_login_url']
            missing_fields = [field for field in required_fields if not params.get(field)]
            
            if missing_fields:
                raise ValueError(f"Campos obrigatórios faltando em 'parameters': {', '.join(missing_fields)}")
            
            self.report_status_start(job_id)
            self.report_log(job_id, "INFO", f"Job {job_id} iniciado. Preparando execução...")
            
            bot_params = {
                'headless': params.get('headless', True),
                'stores': params.get('stores', []),
                'document_type': params.get('document_type'),
                'emitter': params.get('emitter', 'Qualquer'),
                'operation_type': params.get('operation_type', 'Qualquer'),
                'file_type': params.get('file_type', 'XML'),
                'invoice_situation': params.get('invoice_situation', 'Qualquer'),
                'start_date': params.get('start_date'),
                'end_date': params.get('end_date'),
                'gms_user': params.get('gms_user'),
                'gms_password': params.get('gms_password'),
                'gms_login_url': params.get('gms_login_url')
            }
            
            self.report_log(job_id, "INFO", f"Processando {len(bot_params['stores'])} loja(s)")
            self.report_log(job_id, "INFO", f"Período: {bot_params['start_date']} a {bot_params['end_date']}")
            self.report_log(job_id, "INFO", f"Tipo de documento: {bot_params['document_type']}")
            
            logger.info(f"🚀 Iniciando execução do job {job_id}")
            self.report_log(job_id, "INFO", "Iniciando execução da automação...")
            
            bot_runner = BotRunner(bot_params, job_id=job_id, log_callback=self.report_log)
            result = bot_runner.run()
            
            result['job_id'] = job_id
            
            if result.get("status") == "completed":
                self.report_log(job_id, "INFO", "Automação concluída com sucesso!")
                self.report_finish(job_id, "completed", result)
                logger.info(f"✅ Job {job_id} concluído com sucesso")
                
            elif result.get("status") == "completed_no_invoices":
                self.report_log(job_id, "INFO", "Automação concluída, porém nenhuma nota fiscal foi encontrada")
                self.report_finish(job_id, "completed_no_invoices", result)
                logger.info(f"✅ Job {job_id} concluído sem notas fiscais")
                
            else:
                error_msg = result.get("error", "Falha desconhecida na execução")
                self.report_log(job_id, "ERROR", f"Automação falhou: {error_msg}")
                self.report_finish(job_id, "failed", result)
                logger.error(f"❌ Job {job_id} falhou")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"✅ Mensagem processada e confirmada: {job_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar JSON: {e}")
            logger.error(f"Body recebido: {body}")
            if job_id:
                self.report_log(job_id, "ERROR", f"Erro ao decodificar JSON: {str(e)}")
                self.report_finish(job_id, "failed", {
                    "error": f"JSON inválido: {str(e)}",
                    "error_type": "JSONDecodeError"
                })
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except ValueError as e:
            logger.error(f"❌ Erro de validação: {e}")
            if job_id:
                self.report_log(job_id, "ERROR", f"Erro de validação: {str(e)}")
                self.report_finish(job_id, "failed", {
                    "error": str(e),
                    "error_type": "ValidationError"
                })
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}", exc_info=True)
            
            if job_id:
                try:
                    self.report_log(job_id, "ERROR", f"Erro inesperado: {str(e)}")
                    self.report_finish(job_id, "failed", {
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                except:
                    logger.error("Não foi possível reportar falha ao Maestro")
            
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start(self):
        logger.info("=" * 60)
        logger.info("🤖 Bot XML GMS Worker")
        logger.info("=" * 60)
        logger.info(f"Worker ID: {settings.worker_id}")
        logger.info(f"RabbitMQ: {self.rabbitmq_host}:{self.rabbitmq_port}")
        logger.info(f"Fila: {self.queue_name}")
        logger.info(f"Maestro API: {self.maestro_url}")
        logger.info("=" * 60)
        
        try:
            self.connect()
            
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message,
                auto_ack=False
            )
            
            logger.info("🎯 Worker pronto. Aguardando tarefas...")
            
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("\n⚠️ Interrompido pelo usuário")
        except Exception as e:
            logger.critical(f"❌ Erro fatal no worker: {e}", exc_info=True)
            raise
        finally:
            if self.connection and not self.connection.is_closed:
                logger.info("Fechando conexão com RabbitMQ...")
                self.connection.close()
            logger.info("Worker encerrado.")


def main():
    try:
        worker = RabbitMQWorker()
        worker.start()
        return 0
    except Exception as e:
        logger.critical(f"Falha ao iniciar worker: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
