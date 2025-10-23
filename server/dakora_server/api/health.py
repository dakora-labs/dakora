"""Health check API routes"""

import time
from typing import Any, cast
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from ..core.vault import Vault
from ..core.database import get_engine, get_connection
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


@router.get("/latency")
async def check_latency() -> dict[str, Any]:
    """Database latency test endpoint (no auth required).

    Tests database round-trip time with simple queries.

    Returns:
        dict containing single query latency, average latency over 5 queries.
    """
    try:
        engine = get_engine()

        # Single query test
        start = time.time()
        with get_connection(engine) as conn:
            conn.execute(text("SELECT 1"))
        single_latency_ms = (time.time() - start) * 1000

        # Multiple queries test
        start = time.time()
        with get_connection(engine) as conn:
            for _ in range(5):
                conn.execute(text("SELECT 1"))
        total_ms = (time.time() - start) * 1000
        avg_latency_ms = total_ms / 5

        return {
            "single_query_ms": round(single_latency_ms, 1),
            "avg_query_ms": round(avg_latency_ms, 1),
            "total_5_queries_ms": round(total_ms, 1),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")
