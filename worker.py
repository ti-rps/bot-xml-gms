import logging
import logging.config
import json
import time
import signal
import sys
import threading
from datetime import datetime, timezone
from typing import Dict, Optional
import pika
import requests
from pika import PlainCredentials, ConnectionParameters, BlockingConnection
from pathlib import Path

from config import settings
from src.core.bot_runner import BotRunner
from src.utils.cancellation_watcher import CancellationWatcher
from src.utils.exceptions import ConfigurationError, ElementNotFoundError, LoginError

# Interval (seconds) between heartbeat pumps while a long job runs in a thread.
# Keep well below RabbitMQ heartbeat (600s) so two consecutive misses are impossible.
_HEARTBEAT_PUMP_INTERVAL = 30

# Cadência do polling de cancelamento. 15s dá ~20 polls de margem dentro da
# janela de 5min do retry worker do maestro (last_heartbeat_at), e mantém a
# latência clique-Cancelar → worker abortar em ~15s + a sleep ativa do bot.
_CANCELLATION_POLL_INTERVAL = 15.0

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
        logger.info(f"Recebido sinal {signum}. Encerrando...")
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
                
                self.channel.queue_declare(queue=self.queue_name, durable=True, arguments={"x-dead-letter-exchange": "maestro.dlx"})
                
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
    
    def _headers(self) -> Dict[str, str]:
        # WHY: middleware do maestro tem bypass-se-vazio. Quando MAESTRO_WORKER_API_KEY
        # não está populada, o worker não envia o header e o maestro aceita.
        # Quando populada, mandamos em todos os callbacks (start/log/finish/cancellation)
        # — coerência total, não dá pra metade autenticar e metade não.
        headers = {"Content-Type": "application/json"}
        if settings.maestro_worker_api_key:
            headers["X-Worker-API-Key"] = settings.maestro_worker_api_key
        return headers

    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> bool:
        try:
            url = f"{self.maestro_url.rstrip('/')}/{endpoint.lstrip('/')}"

            logger.debug(f"Fazendo requisição {method} para {url}")

            response = requests.request(
                method=method,
                url=url,
                json=payload,
                timeout=10,
                headers=self._headers()
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

    def check_cancellation(self, job_id: str) -> bool:
        """Polla o endpoint de cancelamento do maestro.

        Cada chamada também atualiza last_heartbeat_at no maestro — é o sinal
        de vida que o retry worker usa pra detectar worker morto (janela 5min).

        Retorna True se o usuário pediu cancelamento, False caso contrário.
        Propaga exceções em erros transientes (rede/timeout/5xx) para que o
        CancellationWatcher logue warning e tente de novo no próximo ciclo
        sem derrubar o job. 404 não propaga: trata como "sem cancelamento".
        """
        url = f"{self.maestro_url.rstrip('/')}/api/v1/worker/jobs/{job_id}/cancellation"
        response = requests.get(url, headers=self._headers(), timeout=10)

        if response.status_code == 200:
            data = response.json()
            return bool(data.get("cancellation_requested", False))

        if response.status_code == 404:
            # Job sumiu do maestro — não derruba o job em execução, só loga.
            logger.warning(f"check_cancellation: job {job_id} retornou 404 (job não encontrado)")
            return False

        # 400 (UUID inválido) e 5xx: propaga pro watcher tratar como transiente.
        response.raise_for_status()
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

    def _run_bot_with_heartbeat(
        self,
        bot_params: Dict,
        job_id: str,
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict:
        """Run BotRunner on a worker thread; pump pika data events on the main
        thread so heartbeats stay alive during long (~1h) GMS exports.

        cancel_event é repassado pro BotRunner pra que os loops longos de
        polling do Selenium possam abortar quando o CancellationWatcher
        sinalizar.

        Returns the bot's result dict, or re-raises whatever the bot raised.
        """
        result_holder: Dict = {}
        exc_holder: Dict = {}

        def _target():
            try:
                bot_runner = BotRunner(
                    bot_params,
                    job_id=job_id,
                    log_callback=self.report_log,
                    cancel_event=cancel_event,
                )
                result_holder["result"] = bot_runner.run()
            except BaseException as e:  # capture everything; main thread re-raises
                exc_holder["exc"] = e

        thread = threading.Thread(target=_target, name=f"bot-{job_id}", daemon=True)
        thread.start()

        while thread.is_alive():
            # process_data_events drives the heartbeat frames and detects a dead
            # connection early. We don't expect to receive other messages here
            # because prefetch_count=1 and we haven't ack'd yet.
            try:
                self.connection.process_data_events(time_limit=_HEARTBEAT_PUMP_INTERVAL)
            except Exception as e:
                # If the connection died mid-job, keep waiting for the bot to
                # finish so we don't leak a browser; reconnection happens after.
                logger.warning(f"⚠️ process_data_events falhou durante job longo: {e}")
                thread.join()
                raise

        if "exc" in exc_holder:
            raise exc_holder["exc"]
        return result_holder.get("result", {})
    
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
                'headless': params.get('headless', settings.headless),
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

            # Watcher vive entre /start e /finish. Cada GET dele atualiza
            # last_heartbeat_at no maestro (mantém o job vivo aos olhos do
            # retry worker) e detecta cancelamento solicitado via UI.
            def _notify_cancel():
                self.report_log(
                    job_id,
                    "WARNING",
                    "Cancelamento solicitado pelo usuário. Encerrando após operação atual."
                )

            with CancellationWatcher(
                check_fn=self.check_cancellation,
                job_id=job_id,
                poll_interval=_CANCELLATION_POLL_INTERVAL,
                on_cancel=_notify_cancel,
            ) as watcher:
                result = self._run_bot_with_heartbeat(bot_params, job_id, watcher.cancel_event)

            result['job_id'] = job_id

            if result.get("status") == "completed":
                self.report_log(job_id, "INFO", "Automação concluída com sucesso!")
                self.report_finish(job_id, "completed", result)
                logger.info(f"✅ Job {job_id} concluído com sucesso")

            elif result.get("status") == "completed_no_invoices":
                self.report_log(job_id, "INFO", "Automação concluída, porém nenhuma nota fiscal foi encontrada")
                self.report_finish(job_id, "completed_no_invoices", result)
                logger.info(f"✅ Job {job_id} concluído sem notas fiscais")

            elif result.get("status") == "canceled":
                stage = result.get("stage", "desconhecida")
                self.report_log(job_id, "WARNING", f"Job cancelado pelo usuário (etapa: {stage}).")
                self.report_finish(job_id, "canceled", result)
                logger.info(f"🛑 Job {job_id} cancelado pelo usuário (etapa: {stage})")

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
                except requests.exceptions.RequestException as api_error:
                    logger.critical(f"❌ FALHA CRÍTICA ao reportar falha ao Maestro (problema de conexão/rede): {api_error}", exc_info=True)
                except Exception as unexpected_error:
                    logger.critical(f"❌ FALHA CRÍTICA ao reportar falha ao Maestro (erro inesperado): {unexpected_error}", exc_info=True)

            # Falhas transitórias (rede, browser, timeout) são requeue=True para nova tentativa.
            # Falhas permanentes (config inválida, seletor não encontrado, credenciais) são requeue=False.
            _PERMANENT_EXCEPTIONS = (ConfigurationError, ElementNotFoundError, LoginError)
            is_transient = isinstance(e, (ConnectionError, TimeoutError)) and not isinstance(e, _PERMANENT_EXCEPTIONS)
            if is_transient:
                logger.warning(f"⚠️ Falha transitória detectada ({type(e).__name__}). Mensagem será reprocessada.")
            else:
                logger.error(f"❌ Falha permanente detectada ({type(e).__name__}). Mensagem descartada.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=is_transient)
    
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
