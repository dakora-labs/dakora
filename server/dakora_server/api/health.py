"""Health check API routes"""

from fastapi import APIRouter, HTTPException, Depends
from ..core.vault import Vault
from ..config import get_vault

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check(vault: Vault = Depends(get_vault)):
    """Health check endpoint."""
    try:
        template_count = len(list(vault.list()))
        registry_type = vault.config.get("registry", "local")

        vault_config = {
            "registry_type": registry_type,
            "logging_enabled": vault.config.get("logging", {}).get("enabled", False),
        }

        if registry_type == "local":
            vault_config["prompt_dir"] = vault.config.get("prompt_dir")
        elif registry_type == "azure":
            container = vault.config.get("azure_container", "")
            prefix = vault.config.get("azure_prefix", "")
            location = f"{container}/{prefix}".rstrip("/") if prefix else container
            vault_config["cloud_location"] = location

        return {
            "status": "healthy",
            "templates_loaded": template_count,
            "vault_config": vault_config,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unhealthy: {str(e)}")