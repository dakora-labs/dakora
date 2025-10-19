"""Server configuration"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from .core.vault import Vault


class Settings(BaseSettings):
    mode: str = "local"
    prompt_dir: str = "/app/prompts"
    config_path: str | None = None
    database_url: str | None = None
    redis_url: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

_vault_instance: Vault | None = None


def get_vault() -> Vault:
    """Get or create the Vault instance (dependency injection for FastAPI)"""
    global _vault_instance

    if _vault_instance is None:
        if settings.config_path and Path(settings.config_path).exists():
            _vault_instance = Vault.from_config(settings.config_path)
        elif Path(settings.prompt_dir).exists():
            _vault_instance = Vault(prompt_dir=settings.prompt_dir)
        else:
            prompt_dir = Path(settings.prompt_dir)
            prompt_dir.mkdir(parents=True, exist_ok=True)
            _vault_instance = Vault(prompt_dir=settings.prompt_dir)

    return _vault_instance