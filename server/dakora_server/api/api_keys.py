"""Project-scoped API keys routes."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Engine

from ..core.api_keys import (
    APIKeyService,
    APIKeyLimitExceeded,
    InvalidExpiration,
    APIKeyNotFound,
)
from ..core.api_keys.models import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyListResponse,
)
from ..core.database import get_engine
from ..auth import validate_project_access, get_current_user_id


router = APIRouter(
    prefix="/api/projects/{project_id}/api-keys",
    tags=["api-keys"],
)


def get_api_key_service(
    engine: Engine = Depends(get_engine),
) -> APIKeyService:
    """
    Get an APIKeyService instance.

    Args:
        engine: Global database engine

    Returns:
        APIKeyService instance
    """
    return APIKeyService(engine)


@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    project_id: UUID,
    request: APIKeyCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: APIKeyService = Depends(get_api_key_service),
    _project_validation: UUID = Depends(validate_project_access),
):
    """
    Generate a new API key for the project.

    The full key is only shown once during creation. After that, only a masked
    preview will be available.

    **Request Body:**
    - `name` (optional): Human-readable name for the key
    - `expires_in_days` (optional): Expiration period (30, 90, 365, or null for never)

    **Response:**
    - `id`: Key ID
    - `name`: Key name
    - `key`: Full API key (shown only once)
    - `key_prefix`: First 12 characters for identification
    - `created_at`: Creation timestamp
    - `expires_at`: Expiration timestamp (null if never expires)

    **Errors:**
    - `400`: Maximum keys exceeded or invalid expiration
    """
    try:
        result = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name=request.name,
            expires_in_days=request.expires_in_days,
        )
        return result

    except InvalidExpiration as e:
        raise HTTPException(status_code=400, detail=str(e))
    except APIKeyLimitExceeded as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: APIKeyService = Depends(get_api_key_service),
    _project_validation: UUID = Depends(validate_project_access),
):
    """
    List all active API keys for the project.

    Returns masked keys with metadata. Full keys are never retrievable after creation.

    **Response:**
    - `keys`: List of API keys with masked previews
    - `count`: Current number of active keys
    - `limit`: Maximum allowed keys per project
    """
    try:
        result = service.list_keys(user_id=user_id, project_id=project_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    project_id: UUID,
    key_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: APIKeyService = Depends(get_api_key_service),
    _project_validation: UUID = Depends(validate_project_access),
):
    """
    Get details of a specific API key.

    Returns masked key with metadata. The full key is not retrievable.

    **Path Parameters:**
    - `project_id`: Project UUID
    - `key_id`: API key UUID

    **Response:**
    - `id`: Key ID
    - `name`: Key name
    - `key_preview`: Masked key (e.g., "dkr_1a2b***...***")
    - `created_at`: Creation timestamp
    - `last_used_at`: Last usage timestamp (null if never used)
    - `expires_at`: Expiration timestamp (null if never expires)

    **Errors:**
    - `404`: Key not found or access denied
    """
    try:
        result = service.get_key(user_id=user_id, project_id=project_id, key_id=key_id)
        return result
    except APIKeyNotFound:
        raise HTTPException(status_code=404, detail="API key not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    project_id: UUID,
    key_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: APIKeyService = Depends(get_api_key_service),
    _project_validation: UUID = Depends(validate_project_access),
):
    """
    Revoke an API key.

    Once revoked, the key can no longer be used for authentication.
    This operation is irreversible.

    **Path Parameters:**
    - `project_id`: Project UUID
    - `key_id`: API key UUID

    **Response:**
    - `204 No Content`: Key successfully revoked

    **Errors:**
    - `404`: Key not found or access denied
    """
    try:
        service.revoke_key(user_id=user_id, project_id=project_id, key_id=key_id)
        return None
    except APIKeyNotFound:
        raise HTTPException(status_code=404, detail="API key not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")