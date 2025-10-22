"""Template rendering API routes"""

from fastapi import APIRouter, HTTPException, Depends
from ..core.vault import Vault
from ..core.exceptions import TemplateNotFound, ValidationError, RenderError
from ..auth import get_user_vault
from .schemas import RenderRequest, RenderResponse

router = APIRouter(prefix="/api/templates", tags=["render"])


@router.post("/{template_id}/render", response_model=RenderResponse)
async def render_template(
    template_id: str, request: RenderRequest, vault: Vault = Depends(get_user_vault)
):
    """Render a template with provided inputs from the user's storage."""
    try:
        template = vault.get(template_id)
        rendered = template.render(**request.inputs)
        inputs_used = template.spec.coerce_inputs(request.inputs)

        return RenderResponse(rendered=rendered, inputs_used=inputs_used)
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