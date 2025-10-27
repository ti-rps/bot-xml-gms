"""
Script de teste para enviar mensagem de teste para RabbitMQ
e testar a integração do worker com o Maestro
"""

import pika
import json
import sys

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"  # Ajuste conforme necessário
RABBITMQ_PORT = 5672
RABBITMQ_USER = "guest"
RABBITMQ_PASSWORD = "guest"
RABBITMQ_QUEUE = "automation_jobs"

# Mensagem de teste no novo formato
test_message = {
    "job_id": "test-job-550e8400-e29b-41d4-a716-446655440000",
    "parameters": {
        "stores": [
            "Loja Teste 001",
            "Loja Teste 002"
        ],
        "document_type": "NFe",
        "start_date": "2025-10-01",
        "end_date": "2025-10-27",
        "gms_login_url": "https://gms.teste.com.br/login",
        "headless": True,
        "emitter": "Qualquer",
        "operation_type": "Qualquer",
        "file_type": "XML",
        "invoice_situation": "Qualquer",
        # gms_user e gms_password serão pegos das variáveis de ambiente
    }
}

def send_test_message():
    """Envia mensagem de teste para o RabbitMQ"""
    try:
        # Conectar ao RabbitMQ
        print(f"Conectando ao RabbitMQ em {RABBITMQ_HOST}:{RABBITMQ_PORT}...")
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Declarar fila (se não existir)
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        
        # Serializar mensagem
        message_body = json.dumps(test_message, indent=2, ensure_ascii=False)
        
        print("\n" + "="*60)
        print("ENVIANDO MENSAGEM DE TESTE")
        print("="*60)
        print(message_body)
        print("="*60 + "\n")
        
        # Enviar mensagem
        channel.basic_publish(
            exchange='',
            routing_key=RABBITMQ_QUEUE,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Mensagem persistente
                content_type='application/json'
            )
        )
        
        print(f"✅ Mensagem enviada com sucesso para a fila '{RABBITMQ_QUEUE}'")
        print(f"Job ID: {test_message['job_id']}")
        
        # Fechar conexão
        connection.close()
        print("\n✅ Teste concluído!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Erro ao enviar mensagem: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(send_test_message())
