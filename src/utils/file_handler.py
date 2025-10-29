# src/utils/file_handler.py
import logging
import time
import zipfile
import shutil
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict, Counter
from config import settings

logger = logging.getLogger(__name__)


def log_directory_state(directory: Path, header: str):
    logger.info(f"--- {header} ---")
    if not directory.exists() or not directory.is_dir():
        logger.info(f"Diretório '{directory}' não encontrado.")
        return

    subdirs = [d for d in directory.iterdir() if d.is_dir()]
    if not subdirs:
        items = list(directory.glob('*'))
        if not items:
            logger.info(f"Diretório '{directory}' está vazio.")
        else:
            logger.info(f"Diretório '{directory}' contém {len(items)} arquivos/pastas na raiz.")
    else:
        logger.info(f"Resumo do conteúdo de '{directory}':")
        for subdir in sorted(subdirs):
            try:
                files = [f for f in subdir.rglob('*') if f.is_file()]
                if not files:
                    logger.info(f"└── [PASTA] {subdir.name}/ (Vazia)")
                else:
                    file_types = Counter(f.suffix for f in files)
                    summary = ", ".join([f"{ext} ({count})" for ext, count in file_types.items()])
                    logger.info(f"└── [PASTA] {subdir.name}/ -> Contém: {summary}")
            except OSError as e:
                logger.error(f"Não foi possível acessar a subpasta '{subdir.name}'. Erro: {e}")

    logger.info(f"--- Fim da Verificação de '{directory}' ---")


def analyze_xml_files_and_log_summary(directory: Path):
    logger.info(f"🔎 Iniciando análise dos arquivos XML em '{directory}'...")
    
    xml_files = list(directory.rglob('*.xml'))

    if not xml_files:
        logger.warning("Nenhum arquivo XML encontrado para análise.")
        return {}

    stats = defaultdict(int)
    lojas = {}
    xml_dates = set()
    invalid_files_count = 0
    
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

    for xml_file in xml_files:
        stats['total_xml'] += 1
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            infNFe = root.find('.//nfe:infNFe', ns)
            if infNFe is None:
                invalid_files_count += 1
                continue

            ide = infNFe.find('nfe:ide', ns)
            emit = infNFe.find('nfe:emit', ns)

            if ide is not None:
                mod_element = ide.find('nfe:mod', ns)
                if mod_element is not None:
                    mod = mod_element.text.strip()
                    if mod == '55': stats['nfe'] += 1
                    elif mod == '65': stats['nfce'] += 1
                
                tpNF_element = ide.find('nfe:tpNF', ns)
                if tpNF_element is not None:
                    tpNF = tpNF_element.text
                    if tpNF == '0': stats['entrada'] += 1
                    elif tpNF == '1': stats['saida'] += 1
                
                dhEmi_element = ide.find('nfe:dhEmi', ns)
                if dhEmi_element is not None:
                    xml_dates.add(dhEmi_element.text.split('T')[0])
            
            if emit is not None:
                cnpj_element = emit.find('nfe:CNPJ', ns)
                nome_loja_element = emit.find('nfe:xNome', ns)
                if cnpj_element is not None and nome_loja_element is not None:
                    cnpj, nome_loja = cnpj_element.text, nome_loja_element.text
                    if cnpj not in lojas:
                        lojas[cnpj] = nome_loja

        except ET.ParseError:
            logger.error(f"Erro de parsing no XML '{xml_file.name}'. O arquivo pode estar corrompido.")
        except Exception as e:
            logger.error(f"Erro inesperado ao processar o arquivo '{xml_file.name}': {e}")

    if invalid_files_count > 0:
        logger.warning(f"{invalid_files_count} arquivos XML foram ignorados por não serem NF-e/NFC-e válidas (tag 'infNFe' não encontrada).")

    sorted_dates_list = sorted(list(xml_dates))
    log_message = (
        f"\n\n{'='*50}\n"
        f"📊 --- RESUMO DA EXTRAÇÃO DE DOCUMENTOS FISCAIS --- 📊\n"
        f"{'='*50}\n"
        f"Total de arquivos XML analisados: {stats['total_xml']}\n"
        f"Total de NF-e/NFC-e válidas encontradas: {stats['nfe'] + stats['nfce']}\n"
        f"\n--- Tipos de Documento ---\n"
        f"  - NF-e (Modelo 55): {stats['nfe']}\n"
        f"  - NFC-e (Modelo 65): {stats['nfce']}\n"
        f"\n--- Natureza da Operação ---\n"
        f"  - Notas de Saída: {stats['saida']}\n"
        f"  - Notas de Entrada: {stats['entrada']}\n"
    )
    if sorted_dates_list:
        log_message += "\n--- Período dos Documentos (Datas de Emissão) ---\n"
        for date in sorted_dates_list:
            log_message += f"  - {date}\n"
    if lojas:
        log_message += "\n--- Lojas (Emitentes) Encontradas ---\n"
        for cnpj, nome in lojas.items():
            log_message += f"  - {nome} (CNPJ: {cnpj})\n"
    log_message += f"{'='*50}\n"
    logger.info(log_message)

    summary_data = {
        "total_xml_files_analyzed": stats['total_xml'],
        "valid_invoices_found": stats['nfe'] + stats['nfce'],
        "document_types": {
            "nfe_model_55": stats['nfe'],
            "nfce_model_65": stats['nfce']
        },
        "operation_nature": {
            "exit_notes": stats['saida'],
            "entry_notes": stats['entrada']
        },
        "period_of_documents": sorted_dates_list,
        "stores_found": [{"cnpj": cnpj, "name": nome} for cnpj, nome in lojas.items()]
    }
    
    return summary_data

def wait_for_file(file_path: Path, timeout_seconds: int = 300):
    logger.info(f"Aguardando o arquivo: {file_path.name}...")
    timeout = time.time() + timeout_seconds
    last_size = -1

    while time.time() < timeout:
        if file_path.exists():
            current_size = file_path.stat().st_size
            if current_size > 0 and current_size == last_size:
                logger.info(f"✅ Arquivo '{file_path.name}' está estável e pronto para uso.")
                return True
            last_size = current_size
        time.sleep(2)

    raise TimeoutError(f"O arquivo '{file_path.name}' não foi encontrado ou não estabilizou no tempo limite de {timeout_seconds} segundos.")


def process_downloaded_files(document_type: str, start_date: str, end_date: str):
    summary = None
    logger.info("🚀 Iniciando o processo de tratamento dos arquivos baixados...")

    pending_dir = settings.PENDING_DIR
    processed_dir = settings.PROCESSED_DIR
    initial_zip_path = pending_dir / "documentos_eletronicos.zip"
    
    second_zip_path = None
    second_extract_folder = None
    operation_successful = False
    final_destination_path = None
    
    try:
        wait_for_file(initial_zip_path)

        logger.info(f"Descompactando '{initial_zip_path.name}'...")
        with zipfile.ZipFile(initial_zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                try:
                    filename = member.filename.encode('cp437').decode('utf-8', 'ignore')
                    target_path = pending_dir / Path(filename).name
                    with zip_ref.open(member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                except Exception as e:
                    logger.warning(f"Não foi possível extrair o arquivo '{member.filename}' do zip inicial. Erro: {e}")
                    zip_ref.extract(member, pending_dir)

        logger.info("Procurando o segundo arquivo ZIP no diretório 'pending'...")
        inner_zip_files = [p for p in pending_dir.glob('*.zip') if p.resolve() != initial_zip_path.resolve()]
        if not inner_zip_files:
            raise FileNotFoundError("Nenhum arquivo ZIP secundário foi encontrado em 'pending' após a primeira extração.")
        
        second_zip_path = inner_zip_files[0]
        wait_for_file(second_zip_path)
        logger.info(f"Segundo arquivo ZIP encontrado: '{second_zip_path.name}'")

        second_extract_folder = pending_dir / second_zip_path.stem
        
        logger.info(f"Descompactando '{second_zip_path.name}' para '{second_extract_folder}'...")
        with zipfile.ZipFile(second_zip_path, 'r') as zip_ref:
             for member in zip_ref.infolist():
                try:
                    filename = member.filename.encode('cp437').decode('utf-8', 'ignore')
                    member.filename = filename
                    zip_ref.extract(member, second_extract_folder)
                except Exception as e:
                    logger.warning(f"Não foi possível extrair o arquivo '{member.filename}' do segundo zip. Erro: {e}")
                    zip_ref.extract(member, second_extract_folder)
        
        logger.info("Iniciando busca profunda pela pasta que contém os documentos...")
        traversal_path = second_extract_folder
        source_folders_parent = None
        for _ in range(10):
            subdirectories = [item for item in traversal_path.iterdir() if item.is_dir()]
            if len(subdirectories) == 1:
                traversal_path = subdirectories[0]
                logger.info(f"Navegando para a subpasta: {traversal_path.name}")
            else:
                source_folders_parent = traversal_path
                logger.info(f"Pasta-mãe contendo os documentos encontrada: '{source_folders_parent}'")
                break
        
        if not source_folders_parent:
            raise FileNotFoundError("Não foi possível localizar a pasta de origem dos documentos. Estrutura de pastas inesperada.")
        
        summary = analyze_xml_files_and_log_summary(source_folders_parent)

        folders_to_move = [d for d in source_folders_parent.iterdir() if d.is_dir()]

        try:
            day, month, year = start_date.split('/')
        except ValueError:
            logger.error(f"Formato de data inválido: '{start_date}'. Usando estrutura padrão.")
            year, month = "ANO_INVALIDO", "MES_INVALIDO"

        start_date_fmt = start_date.replace('/', '-')
        end_date_fmt = end_date.replace('/', '-')

        destination_folder_name = start_date_fmt if start_date_fmt == end_date_fmt else f"{start_date_fmt} a {end_date_fmt}"

        month_folder = f"{month}-{year}"

        final_destination_path = processed_dir / document_type.upper() / year / month_folder / destination_folder_name

        if final_destination_path.exists() and final_destination_path.is_dir():
            logger.warning(f"O diretório de destino '{final_destination_path}' já existe. Removendo-o...")
            shutil.rmtree(final_destination_path)

        final_destination_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Diretório de destino criado/verificado: '{final_destination_path}'")
        
        if not folders_to_move:
            logger.warning("A pasta de origem está vazia. Nenhuma pasta para mover.")
            operation_successful = True
        else:
            logger.info(f"Movendo {len(folders_to_move)} pastas para o destino final...")
            for folder in folders_to_move:
                destination_for_folder = final_destination_path / folder.name
                shutil.move(str(folder), str(destination_for_folder))
            logger.info("✅ Pastas movidas com sucesso!")
            operation_successful = True

    except Exception as e:
        logger.critical(f"❌ Falha crítica durante o processamento de arquivos: {e}", exc_info=True)
        operation_successful = False
        raise
    finally:
        if operation_successful:
            logger.info("Operação bem-sucedida. Realizando limpeza do diretório 'pending'...")
            if initial_zip_path and initial_zip_path.exists():
                initial_zip_path.unlink()
                logger.info(f"Removido: {initial_zip_path.name}")
            if second_zip_path and second_zip_path.exists():
                second_zip_path.unlink()
                logger.info(f"Removido: {second_zip_path.name}")
            if second_extract_folder and second_extract_folder.exists():
                shutil.rmtree(second_extract_folder)
                logger.info(f"Removido diretório: {second_extract_folder.name}")
            logger.info("Limpeza concluída.")
        else:
            logger.warning("A operação falhou. Nenhum arquivo temporário será removido de 'pending' para permitir análise manual.")

        logger.info("Verificando estado final dos diretórios...")
        log_directory_state(pending_dir, "ESTADO FINAL DO DIRETÓRIO 'PENDING'")
        log_directory_state(processed_dir, "ESTADO FINAL DO DIRETÓRIO 'PROCESSED'")
        
        return summary