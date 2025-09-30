# src/utils/file_handler.py
import logging
import time
import zipfile
import shutil
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

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

def process_downloaded_files(start_date: str, end_date: str):
    logger.info("🚀 Iniciando o processo de tratamento dos arquivos baixados...")

    pending_dir = settings.PENDING_DIR
    processed_dir = settings.PROCESSED_DIR

    initial_zip_path = pending_dir / "documentos_eletronicos.zip"
    first_extract_folder = pending_dir / "documentos_eletronicos"

    try:
        wait_for_file(initial_zip_path)

        logger.info(f"Descompactando '{initial_zip_path.name}'...")
        with zipfile.ZipFile(initial_zip_path, 'r') as zip_ref:
            zip_ref.extractall(pending_dir)
  
        logger.info("Aguardando a criação do arquivo ZIP interno após a extração...")
        
        timeout = time.time() + 60
        second_zip_path = None
        
        while time.time() < timeout:
            inner_zip_files = list(first_extract_folder.glob('*.zip'))
            if inner_zip_files:
                if wait_for_file(inner_zip_files[0], timeout_seconds=30):
                    second_zip_path = inner_zip_files[0]
                    break
            time.sleep(1)
        
        if not second_zip_path:
            raise FileNotFoundError("Nenhum arquivo ZIP foi encontrado dentro de 'documentos_eletronicos' após a extração.")

        second_extract_folder = first_extract_folder / second_zip_path.stem
        
        logger.info(f"Descompactando '{second_zip_path.name}' para '{second_extract_folder}'...")
        with zipfile.ZipFile(second_zip_path, 'r') as zip_ref:
            zip_ref.extractall(second_extract_folder)

        docs_fiscais_path = second_extract_folder / "docs-fiscais"
        subfolders = [p for p in docs_fiscais_path.iterdir() if p.is_dir()]
        if not subfolders:
            raise FileNotFoundError("Nenhuma subpasta encontrada dentro de 'docs-fiscais'.")

        final_source_path = subfolders[0]
        logger.info(f"Arquivos de origem encontrados em: '{final_source_path}'")

        start_date_fmt = start_date.replace('/', '-')
        end_date_fmt = end_date.replace('/', '-')
        destination_folder_name = f"{start_date_fmt} a {end_date_fmt}"
        final_destination_path = processed_dir / destination_folder_name

        final_destination_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Diretório de destino criado/verificado: '{final_destination_path}'")

        files_to_move = list(final_source_path.glob('*.*'))
        logger.info(f"Movendo {len(files_to_move)} arquivos para o destino final...")
        for file in files_to_move:
            shutil.move(str(file), str(final_destination_path))

        logger.info("✅ Arquivos movidos com sucesso!")

    except Exception as e:
        logger.critical(f"❌ Falha crítica durante o processamento de arquivos: {e}", exc_info=True)
        raise
    finally:
        logger.info("Realizando limpeza do diretório 'pending'...")
        if initial_zip_path.exists():
            initial_zip_path.unlink()
        if first_extract_folder.exists():
            shutil.rmtree(first_extract_folder)
        logger.info("Limpeza concluída.")