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
    
    def report_status(self, task_id: str, status: str, data: Optional[Dict] = None):
        """
        Reporta status da tarefa para o Maestro via HTTP
        
        Args:
            task_id: ID da tarefa
            status: Status atual (started, progress, completed, failed)
            data: Dados adicionais
        """
        try:
            url = f"{self.maestro_url}/api/tasks/{task_id}/status"
            
            payload = {
                "task_id": task_id,
                "status": status,
                "timestamp": time.time(),
                "worker_id": settings.worker_id,
                "data": data or {}
            }
            
            logger.debug(f"Reportando status '{status}' para tarefa {task_id}")
            
            response = requests.post(
                url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.debug(f"✅ Status reportado com sucesso: {status}")
            else:
                logger.warning(f"⚠️ Falha ao reportar status. HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao reportar status para Maestro: {e}")
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao reportar status: {e}")
    
    def process_message(self, ch, method, properties, body):
        """
        Processa mensagem recebida do RabbitMQ
        
        Args:
            ch: Canal
            method: Método de entrega
            properties: Propriedades da mensagem
            body: Corpo da mensagem
        """
        task_id = None
        
        try:
            # Parse da mensagem
            message = json.loads(body)
            task_id = message.get("task_id")
            
            logger.info(f"📨 Mensagem recebida: {task_id}")
            logger.info(f"Payload: {json.dumps(message, indent=2)}")
            
            # Validar campos obrigatórios
            required_fields = ['task_id', 'stores', 'document_type', 'start_date', 'end_date', 'gms_login_url']
            missing_fields = [field for field in required_fields if not message.get(field)]
            
            if missing_fields:
                raise ValueError(f"Campos obrigatórios faltando: {', '.join(missing_fields)}")
            
            # Preparar parâmetros para o BotRunner
            params = {
                'headless': message.get('headless', True),
                'stores': message.get('stores', []),
                'document_type': message.get('document_type'),
                'emitter': message.get('emitter', 'Qualquer'),
                'operation_type': message.get('operation_type', 'Qualquer'),
                'file_type': message.get('file_type', 'XML'),
                'invoice_situation': message.get('invoice_situation', 'Qualquer'),
                'start_date': message.get('start_date'),
                'end_date': message.get('end_date'),
                'gms_user': message.get('gms_user'),
                'gms_password': message.get('gms_password'),
                'gms_login_url': message.get('gms_login_url')
            }
            
            # Reportar início
            self.report_status(task_id, "started", {
                "document_type": params['document_type'],
                "start_date": params['start_date'],
                "end_date": params['end_date'],
                "stores": params['stores']
            })
            
            # Executar tarefa
            logger.info(f"🚀 Iniciando execução da tarefa {task_id}")
            bot_runner = BotRunner(params)
            result = bot_runner.run()
            
            # Adicionar task_id ao resultado
            result['task_id'] = task_id
            
            # Reportar resultado
            if result.get("status") == "completed":
                self.report_status(task_id, "completed", result)
                logger.info(f"✅ Tarefa {task_id} concluída com sucesso")
            elif result.get("status") == "completed_no_invoices":
                self.report_status(task_id, "completed", result)
                logger.info(f"✅ Tarefa {task_id} concluída sem notas fiscais")
            else:
                self.report_status(task_id, "failed", result)
                logger.error(f"❌ Tarefa {task_id} falhou")
            
            # ACK da mensagem
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"✅ Mensagem processada e confirmada: {task_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar JSON: {e}")
            logger.error(f"Body recebido: {body}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except ValueError as e:
            logger.error(f"❌ Erro de validação: {e}")
            if task_id:
                self.report_status(task_id, "failed", {
                    "error": str(e),
                    "error_type": "ValidationError"
                })
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}", exc_info=True)
            
            # Tentar reportar falha
            if task_id:
                try:
                    self.report_status(task_id, "failed", {
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
