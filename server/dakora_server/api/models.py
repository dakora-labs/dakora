"""LLM models execution API routes"""

from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from ..core.vault import Vault
from ..core.exceptions import TemplateNotFound, ValidationError, RenderError
from ..auth import get_user_vault
from .schemas import ExecuteRequest

router = APIRouter(prefix="/api/templates", tags=["models"])


@router.post("/{template_id}/compare")
async def compare_template(
    template_id: str, request: ExecuteRequest, vault: Vault = Depends(get_user_vault)
):
    """Compare template execution across one or more LLM models using the user's template."""
    try:
        template = vault.get(template_id)

        llm_params: dict[str, Any] = {}
        if request.temperature is not None:
            llm_params["temperature"] = request.temperature
        if request.max_tokens is not None:
            llm_params["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            llm_params["top_p"] = request.top_p
        llm_params.update(request.params)

        all_kwargs: dict[str, Any] = {**request.inputs, **llm_params}

        result = await template.compare(models=request.models, **all_kwargs)

        return result.model_dump()
    except TemplateNotFound:
        raise HTTPException(
            status_code=404, detail=f"Template '{template_id}' not found"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except RenderError as e:
        raise HTTPException(status_code=400, detail=f"Render error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))