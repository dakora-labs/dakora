"""Server configuration"""

from pathlib import Path
from pydantic_settings import BaseSettings
from .core.vault import Vault


class Settings(BaseSettings):
    mode: str = "local"
    prompt_dir: str = "/app/prompts"
    config_path: str | None = None
    database_url: str | None = None
    redis_url: str | None = None

    # Azure Blob Storage settings
    azure_storage_connection_string: str | None = None
    azure_storage_container: str | None = None
    azure_storage_account_url: str | None = None

    # Authentication settings
    clerk_jwt_issuer: str | None = None  # e.g., "https://your-domain.clerk.accounts.dev"
    clerk_jwks_url: str | None = None  # e.g., "https://your-domain.clerk.accounts.dev/.well-known/jwks.json"
    clerk_webhook_secret: str | None = None  # Clerk webhook signing secret
    clerk_secret_key: str | None = None  # Clerk secret key for creating invitations
    invite_redirect_url: str | None = None  # Redirect URL for invitations (leave None for Clerk default Account Portal)
    auth_required: bool = False  # Set to True to enforce authentication

    # Azure OpenAI settings (shared instance for all workspaces)
    azure_openai_endpoint: str = ""  # e.g., "https://your-resource.openai.azure.com/"
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = "gpt-4o"  # Default model deployment

    # Google Gemini settings (shared instance for all workspaces)
    google_gemini_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

_vault_instance: Vault | None = None


def get_vault() -> Vault:
    """Get or create the Vault instance (dependency injection for FastAPI)"""
    global _vault_instance

    if _vault_instance is None:
        # Priority 1: Check for Azure Blob Storage configuration
        if settings.azure_storage_container:
            from .core.registry import AzureRegistry
            _vault_instance = Vault(
                AzureRegistry(
                    container=settings.azure_storage_container,
                    connection_string=settings.azure_storage_connection_string,
                    account_url=settings.azure_storage_account_url,
                )
            )
        # Priority 2: Use config file if provided
        elif settings.config_path and Path(settings.config_path).exists():
            _vault_instance = Vault.from_config(settings.config_path)
        # Priority 3: Use local prompt directory
        elif Path(settings.prompt_dir).exists():
            _vault_instance = Vault(prompt_dir=settings.prompt_dir)
        # Priority 4: Create local prompt directory
        else:
            prompt_dir = Path(settings.prompt_dir)
            prompt_dir.mkdir(parents=True, exist_ok=True)
            _vault_instance = Vault(prompt_dir=settings.prompt_dir)

    return _vault_instance


def get_settings() -> Settings:
    """Get the Settings instance (dependency injection for FastAPI)"""
    return settings
