#!/usr/bin/env python3
"""
Script de teste para simular requisição HTTP ao bot-xml-gms sem Docker
Testa o BotRunner com os parâmetros fornecidos
"""

import sys
import json
import logging
from datetime import datetime
from uuid import uuid4

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

# Parâmetros de teste
TEST_BODY = {
    "headless": False,
    "stores": [4814, 6861, 11118, 12147, 12270, 12325, 12330, 13481, 13483, 13887, 14448, 14521, 14522, 14523, 14528, 18476, 18478, 18479, 18480, 18481, 19077, 19081, 21407, 23315, 23331, 23332, 23924],
    "document_type": "NFE",
    "emitter": "PROPRIO",
    "operation_type": "TODAS",
    "file_type": "XML",
    "invoice_situation": "TODAS",
    "start_date": "01/10/2025",
    "end_date": "26/10/2025",
    "gms_user": "setor fiscal",
    "gms_password": "rps@317309",
    "gms_login_url": "https://cp10307.retaguarda.grupoboticario.com.br/app/#/login"
}


def test_bot_runner():
    """Testa o BotRunner com os parâmetros fornecidos"""
    
    print("\n" + "=" * 80)
    print("🧪 TESTE DO BOT-XML-GMS SEM DOCKER")
    print("=" * 80 + "\n")
    
    # Gerar job_id único
    job_id = f"test_{uuid4().hex[:8]}"
    print(f"📝 Job ID: {job_id}")
    print(f"🕒 Timestamp: {datetime.now().isoformat()}\n")
    
    # Exibir parâmetros do teste
    print("📦 Parâmetros Fornecidos:")
    print(json.dumps(TEST_BODY, indent=2, default=str))
    print()
    
    # Tentar importar e inicializar BotRunner
    try:
        print("📥 Importando BotRunner...")
        from src.core.bot_runner import BotRunner
        logger.info("✅ BotRunner importado com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Falha ao importar BotRunner: {e}")
        return False
    
    # Tentar inicializar o runner
    try:
        print("\n🔧 Inicializando BotRunner...")
        
        def log_callback(job_id, level, message):
            """Callback para logs do Maestro"""
            print(f"📤 [Callback] [{level}] {message}")
        
        runner = BotRunner(
            params=TEST_BODY,
            job_id=job_id,
            log_callback=log_callback
        )
        
        logger.info("✅ BotRunner inicializado com sucesso!")
        print_runner_status(runner)
        
    except FileNotFoundError as e:
        logger.error(f"❌ Arquivo não encontrado: {e}")
        logger.info("💡 Dica: Verifique se 'config/selectors.yaml' existe")
        return False
        
    except ValueError as e:
        logger.error(f"❌ Erro de validação: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar BotRunner: {e}", exc_info=True)
        return False
    
    # Tentar rodar setup
    try:
        print("\n⚙️  Executando setup()...")
        result = runner.setup()
        
        if result:
            logger.info("✅ Setup executado com sucesso")
            print_runner_status(runner)
        else:
            logger.warning("⚠️  Setup retornou False")
            return False
            
    except FileNotFoundError as e:
        logger.error(f"❌ Arquivo não encontrado no setup: {e}")
        logger.info("💡 Dica: Verifique se 'config/selectors.yaml' existe e está formatado corretamente")
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar setup: {e}", exc_info=True)
        return False
    
    # Aviso sobre execução completa
    print("\n" + "=" * 80)
    print("⚠️  NOTA IMPORTANTE: Teste interrompido antes de run()")
    print("=" * 80)
    print("""
A execução de run() iniciaria um navegador real e tentaria:
1. Fazer login no GMS
2. Navegar para a página de exportação
3. Submeter os parâmetros de filtro
4. Aguardar a exportação
5. Fazer download dos arquivos
6. Processar e organizar os dados

Para executar o teste completo (with headless=true para testes mais rápidos):
  python test_api_simulation.py --full

Ou para execução em headless (sem interface):
  python test_api_simulation.py --headless
""")
    
    return True


def print_runner_status(runner):
    """Exibe o status do BotRunner"""
    print("\n📊 Status do BotRunner:")
    print(f"  • Status: {runner.status}")
    print(f"  • Progress: {runner.progress}%")
    print(f"  • Message: {runner.current_message}")
    print(f"  • Headless: {runner.headless}")
    print(f"  • Lojas: {len(runner.stores_to_process)} lojas a processar")
    print(f"  • Período: {runner.start_date} a {runner.end_date}")
    print(f"  • URL GMS: {runner.gms_login_url.split('/')[-2]}")  # Apenas domínio
    print(f"  • Seletores carregados: {len(runner.selectors) if runner.selectors else 0} seções")


def main():
    """Função principal do teste"""
    
    success = test_bot_runner()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ TESTE BÁSICO CONCLUÍDO COM SUCESSO")
        print("O bot está pronto para executar automações!")
    else:
        print("❌ TESTE FALHOU - Verifique os erros acima")
    print("=" * 80 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
