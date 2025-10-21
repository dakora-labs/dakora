"""Health check API routes"""

from typing import Any, cast
from fastapi import APIRouter, HTTPException, Depends
from ..core.vault import Vault
from ..config import get_vault

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check(vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    """Health check endpoint.

    Returns:
        dict containing health status, template count, and vault configuration.

    Raises:
        HTTPException: 503 if vault is unhealthy or cannot be accessed.
    """
    try:
        template_count = len(list(vault.list()))
        config = vault.config
        registry_type: str = str(config.get("registry", "local"))

        vault_config: dict[str, Any] = {
            "registry_type": registry_type,
            "logging_enabled": cast(dict[str, Any], config.get("logging", {})).get(
                "enabled", False
            ),
        }

        if registry_type == "local":
            vault_config["prompt_dir"] = config.get("prompt_dir")
        elif registry_type == "azure":
            container: str = str(config.get("azure_container", ""))
            prefix: str = str(config.get("azure_prefix", ""))
            location: str = f"{container}/{prefix}".rstrip("/") if prefix else container
            vault_config["cloud_location"] = location

        return {
            "status": "healthy",
            "templates_loaded": template_count,
            "vault_config": vault_config,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unhealthy: {str(e)}")
