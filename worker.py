#!/usr/bin/env python3
"""
Worker RabbitMQ para bot-xml-gms
Consome tarefas do RPS Maestro e reporta status via HTTP
"""

import logging
import logging.config
import json
import time
import signal
import sys
from typing import Dict, Optional
import pika
import requests
from pathlib import Path

from config.settings import settings
from src.core.bot_runner import BotRunner

# Configurar logging
logging.config.dictConfig(settings.get_log_config())
logger = logging.getLogger(__name__)


class RabbitMQWorker:
    """Worker que consome tarefas do RabbitMQ e reporta status via HTTP"""
    
    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.should_stop = False
        
        # Configurações do RabbitMQ
        self.rabbitmq_host = settings.rabbitmq_host
        self.rabbitmq_port = settings.rabbitmq_port
        self.rabbitmq_user = settings.rabbitmq_user
        self.rabbitmq_password = settings.rabbitmq_password
        self.queue_name = settings.rabbitmq_queue
        
        # Configurações do Maestro
        self.maestro_url = settings.maestro_api_url
        
        # Registrar handlers de sinal
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de interrupção"""
        logger.info(f"Recebido sinal {signum}. Encerrando gracefully...")
        self.should_stop = True
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        sys.exit(0)
    
    def connect(self):
        """Estabelece conexão com RabbitMQ"""
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
                
                # Declarar fila
                self.channel.queue_declare(queue=self.queue_name, durable=True)
                
                # Configurar QoS
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
        """
        Helper para fazer requisições HTTP ao Maestro
        
        Args:
            method: Método HTTP (POST, PUT, etc)
            endpoint: Endpoint da API (ex: /api/v1/jobs/{job_id}/start)
            payload: Dados a serem enviados
            
        Returns:
            True se a requisição foi bem sucedida, False caso contrário
        """
        try:
            url = f"{self.maestro_url}{endpoint}"
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
        """
        Reporta início da execução do job
        
        Args:
            job_id: ID do job
            
        Returns:
            True se reportado com sucesso
        """
        endpoint = f"/api/v1/jobs/{job_id}/start"
        logger.info(f"📤 Reportando início do job {job_id}")
        return self._make_request("POST", endpoint)
    
    def report_log(self, job_id: str, level: str, message: str) -> bool:
        """
        Envia log para o Maestro
        
        Args:
            job_id: ID do job
            level: Nível do log (INFO, WARNING, ERROR)
            message: Mensagem do log
            
        Returns:
            True se enviado com sucesso
        """
        endpoint = f"/api/v1/jobs/{job_id}/log"
        payload = {
            "level": level,
            "message": message
        }
        logger.debug(f"📝 Enviando log [{level}]: {message}")
        return self._make_request("POST", endpoint, payload)
    
    def report_status_complete(self, job_id: str, result_data: Dict) -> bool:
        """
        Reporta conclusão bem sucedida do job
        
        Args:
            job_id: ID do job
            result_data: Dados do resultado da execução
            
        Returns:
            True se reportado com sucesso
        """
        endpoint = f"/api/v1/jobs/{job_id}/complete"
        logger.info(f"✅ Reportando conclusão do job {job_id}")
        return self._make_request("POST", endpoint, result_data)
    
    def report_status_fail(self, job_id: str, error_data: Dict) -> bool:
        """
        Reporta falha na execução do job
        
        Args:
            job_id: ID do job
            error_data: Dados do erro
            
        Returns:
            True se reportado com sucesso
        """
        endpoint = f"/api/v1/jobs/{job_id}/fail"
        logger.error(f"❌ Reportando falha do job {job_id}")
        return self._make_request("POST", endpoint, error_data)
    
    def process_message(self, ch, method, properties, body):
        """
        Processa mensagem recebida do RabbitMQ
        
        Args:
            ch: Canal
            method: Método de entrega
            properties: Propriedades da mensagem
            body: Corpo da mensagem
        """
        job_id = None
        
        try:
            # Parse da mensagem
            message = json.loads(body)
            job_id = message.get("job_id")
            
            logger.info(f"📨 Mensagem recebida: {job_id}")
            logger.info(f"Payload: {json.dumps(message, indent=2)}")
            
            # Extrair parâmetros aninhados
            params = message.get("parameters", {})
            
            # Validar campos obrigatórios na raiz
            if not job_id:
                raise ValueError("Campo obrigatório 'job_id' não encontrado")
            
            # Validar campos obrigatórios em parameters
            required_fields = ['stores', 'document_type', 'start_date', 'end_date', 'gms_login_url']
            missing_fields = [field for field in required_fields if not params.get(field)]
            
            if missing_fields:
                raise ValueError(f"Campos obrigatórios faltando em 'parameters': {', '.join(missing_fields)}")
            
            # Reportar início da execução
            self.report_status_start(job_id)
            self.report_log(job_id, "INFO", f"Job {job_id} iniciado. Preparando execução...")
            
            # Preparar parâmetros para o BotRunner
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
            
            # Log dos parâmetros
            self.report_log(job_id, "INFO", f"Processando {len(bot_params['stores'])} loja(s)")
            self.report_log(job_id, "INFO", f"Período: {bot_params['start_date']} a {bot_params['end_date']}")
            self.report_log(job_id, "INFO", f"Tipo de documento: {bot_params['document_type']}")
            
            # Executar tarefa
            logger.info(f"🚀 Iniciando execução do job {job_id}")
            self.report_log(job_id, "INFO", "Iniciando execução da automação...")
            
            bot_runner = BotRunner(bot_params)
            result = bot_runner.run()
            
            # Adicionar job_id ao resultado
            result['job_id'] = job_id
            
            # Reportar resultado baseado no status
            if result.get("status") == "completed":
                self.report_log(job_id, "INFO", "Automação concluída com sucesso!")
                self.report_status_complete(job_id, result)
                logger.info(f"✅ Job {job_id} concluído com sucesso")
                
            elif result.get("status") == "completed_no_invoices":
                self.report_log(job_id, "INFO", "Automação concluída, porém nenhuma nota fiscal foi encontrada")
                self.report_status_complete(job_id, result)
                logger.info(f"✅ Job {job_id} concluído sem notas fiscais")
                
            else:
                error_msg = result.get("error", "Falha desconhecida na execução")
                self.report_log(job_id, "ERROR", f"Automação falhou: {error_msg}")
                self.report_status_fail(job_id, result)
                logger.error(f"❌ Job {job_id} falhou")
            
            # ACK da mensagem
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"✅ Mensagem processada e confirmada: {job_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar JSON: {e}")
            logger.error(f"Body recebido: {body}")
            if job_id:
                self.report_log(job_id, "ERROR", f"Erro ao decodificar JSON: {str(e)}")
                self.report_status_fail(job_id, {
                    "error": f"JSON inválido: {str(e)}",
                    "error_type": "JSONDecodeError"
                })
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except ValueError as e:
            logger.error(f"❌ Erro de validação: {e}")
            if job_id:
                self.report_log(job_id, "ERROR", f"Erro de validação: {str(e)}")
                self.report_status_fail(job_id, {
                    "error": str(e),
                    "error_type": "ValidationError"
                })
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}", exc_info=True)
            
            # Tentar reportar falha
            if job_id:
                try:
                    self.report_log(job_id, "ERROR", f"Erro inesperado: {str(e)}")
                    self.report_status_fail(job_id, {
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                except:
                    logger.error("Não foi possível reportar falha ao Maestro")
            
            # NACK sem requeue (envia para DLQ se configurado)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start(self):
        """Inicia o worker"""
        logger.info("=" * 60)
        logger.info("🤖 Bot XML GMS Worker")
        logger.info("=" * 60)
        logger.info(f"Worker ID: {settings.worker_id}")
        logger.info(f"RabbitMQ: {self.rabbitmq_host}:{self.rabbitmq_port}")
        logger.info(f"Fila: {self.queue_name}")
        logger.info(f"Maestro API: {self.maestro_url}")
        logger.info("=" * 60)
        
        try:
            # Conectar ao RabbitMQ
            self.connect()
            
            # Configurar consumidor
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message,
                auto_ack=False
            )
            
            logger.info("🎯 Worker pronto. Aguardando tarefas...")
            
            # Iniciar consumo
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
    """Função principal"""
    try:
        worker = RabbitMQWorker()
        worker.start()
        return 0
    except Exception as e:
        logger.critical(f"Falha ao iniciar worker: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
