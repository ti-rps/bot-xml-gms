#config/settings.py
import os
import socket
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    worker_id: str = Field(default_factory=lambda: f"worker-{socket.gethostname()}")
    
    gms_username: str = Field(default="", alias="GMS_USER")
    gms_password: str = Field(default="", alias="GMS_PASSWORD")
    
    rabbitmq_host: str = Field(default="localhost")
    rabbitmq_port: int = Field(default=5672)
    rabbitmq_user: str = Field(default="guest")
    rabbitmq_password: str = Field(default="guest")
    rabbitmq_queue: str = Field(default="bot-xml-tasks")
    
    maestro_api_url: str = Field(default="http://localhost:8080")
    # WHY: middleware do maestro tem bypass-se-vazio. Quando string vazia,
    # worker não envia o header X-Worker-API-Key e o maestro aceita. Quando
    # populada, worker passa em todos os callbacks. Forward-compatible:
    # ligar auth depois é só popular esta env e a do maestro + restart.
    maestro_worker_api_key: str = Field(default="", alias="MAESTRO_WORKER_API_KEY")

    maestro_db_host: str = Field(default="postgres")
    maestro_db_port: int = Field(default=5432)
    maestro_db_user: str = Field(default="user")
    maestro_db_password: str = Field(default="password")
    maestro_db_name: str = Field(default="maestro_db")
    
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    chrome_driver_path: Optional[str] = None
    headless: bool = Field(default=True)
    
    page_load_timeout: int = Field(default=30, ge=5, le=120)
    implicit_wait: int = Field(default=10, ge=1, le=60)
    download_timeout: int = Field(default=900, ge=60, le=3600)
    default_timeout: int = Field(default=30)
    
    log_level: str = Field(default="INFO")
    log_file: str = "logs/bot.log"
    log_max_bytes: int = Field(default=10485760)
    log_backup_count: int = Field(default=5)
    
    @property
    def BASE_DIR(self) -> Path:
        return self.base_dir
    
    @property
    def LOGS_DIR(self) -> Path:
        path = self.base_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def DOWNLOADS_DIR(self) -> Path:
        path = self.base_dir / "downloads"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def PENDING_DIR(self) -> Path:
        # WHY: in containers the downloads dir is often a host bind-mount
        # (e.g. /mnt/c/... on WSL). Extracting thousands of XMLs there
        # triggers cross-fs permission errors on move and ENOMEM on traversal.
        # Keep pending on the container's native fs; only processed/ stays on the mount.
        override = os.environ.get("BOT_PENDING_DIR")
        path = Path(override) if override else Path("/tmp/bot-xml-gms/pending")
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def PROCESSED_DIR(self) -> Path:
        path = self.DOWNLOADS_DIR / "processed"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def DESTINATION_DIR(self) -> Path:
        return self.PROCESSED_DIR
    
    @property
    def DEFAULT_TIMEOUT(self) -> int:
        return self.default_timeout
    
    @property
    def SELECTORS_FILE(self) -> Path:
        return self.base_dir / "config" / "selectors.yaml"
    
    def get_log_config(self) -> dict:
        """Retorna configuração completa de logging"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                },
                "simple": {
                    "format": "%(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": self.log_level,
                    "formatter": "detailed",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": self.log_level,
                    "formatter": "detailed",
                    "filename": str(self.LOGS_DIR / Path(self.log_file).name),
                    "maxBytes": self.log_max_bytes,
                    "backupCount": self.log_backup_count,
                    "encoding": "utf-8"
                }
            },
            "root": {
                "level": self.log_level,
                "handlers": ["console", "file"]
            }
        }


settings = Settings()