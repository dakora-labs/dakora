"""Template/Prompts API routes"""

from typing import List, Dict
from fastapi import APIRouter, HTTPException, Depends, Response
from ..core.vault import Vault
from ..core.model import InputSpec
from ..core.exceptions import TemplateNotFound, ValidationError
from ..config import get_vault
from .schemas import (
    TemplateResponse,
    CreateTemplateRequest,
    UpdateTemplateRequest,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=List[str])
async def list_templates(vault: Vault = Depends(get_vault)):
    """List all available template IDs."""
    try:
        return list(vault.list())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str, vault: Vault = Depends(get_vault)):
    """Get a specific template with all its details."""
    try:
        template = vault.get(template_id)
        spec = template.spec
        tmpl = spec.template[:-1] if spec.template.endswith("\n") else spec.template
        return TemplateResponse(
            id=spec.id,
            version=spec.version,
            description=spec.description,
            template=tmpl,
            inputs={
                name: {
                    "type": input_spec.type,
                    "required": input_spec.required,
                    "default": input_spec.default,
                }
                for name, input_spec in spec.inputs.items()
            },
            metadata=spec.metadata,
        )
    except TemplateNotFound:
        raise HTTPException(
            status_code=404, detail=f"Template '{template_id}' not found"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=TemplateResponse)
async def create_template(
    request: CreateTemplateRequest, vault: Vault = Depends(get_vault)
):
    """Create a new template and save it to the filesystem."""
    try:
        if not request.id or request.id.strip() == "":
            raise HTTPException(status_code=422, detail="Template ID cannot be empty")

        try:
            vault.get(request.id)
            raise HTTPException(
                status_code=400, detail=f"Template '{request.id}' already exists"
            )
        except TemplateNotFound:
            pass

        # Build inputs dict for the TemplateSpec
        inputs_dict: Dict[str, InputSpec] = {}
        for input_name, input_data in request.inputs.items():
            inputs_dict[input_name] = InputSpec(
                type=input_data.get("type", "string"),
                required=input_data.get("required", True),
                default=input_data.get("default"),
            )

        from ..core.model import TemplateSpec

        spec = TemplateSpec(
            id=request.id,
            version=request.version,
            description=request.description,
            template=request.template,
            inputs=inputs_dict,
            metadata=request.metadata,
        )

        vault.registry.save(spec)
        vault.invalidate_cache()

        tmpl = spec.template[:-1] if spec.template.endswith("\n") else spec.template
        return TemplateResponse(
            id=spec.id,
            version=spec.version,
            description=spec.description,
            template=tmpl,
            inputs={
                name: {
                    "type": input_spec.type,
                    "required": input_spec.required,
                    "default": input_spec.default,
                }
                for name, input_spec in spec.inputs.items()
            },
            metadata=spec.metadata,
        )

    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str, request: UpdateTemplateRequest, vault: Vault = Depends(get_vault)
):
    """Update an existing template and save it to the filesystem."""
    try:
        try:
            current_template = vault.get(template_id)
            current_spec = current_template.spec
        except TemplateNotFound:
            raise HTTPException(
                status_code=404, detail=f"Template '{template_id}' not found"
            )

        updated_version = (
            request.version if request.version is not None else current_spec.version
        )
        updated_description = (
            request.description
            if request.description is not None
            else current_spec.description
        )
        updated_template = (
            request.template if request.template is not None else current_spec.template
        )

        updated_inputs_dict: Dict[str, InputSpec] = {}
        if request.inputs is not None:
            for input_name, input_data in request.inputs.items():
                updated_inputs_dict[input_name] = InputSpec(
                    type=input_data.get("type", "string"),
                    required=input_data.get("required", True),
                    default=input_data.get("default"),
                )
        else:
            updated_inputs_dict = current_spec.inputs

        updated_metadata = (
            request.metadata if request.metadata is not None else current_spec.metadata
        )

        from ..core.model import TemplateSpec

        updated_spec = TemplateSpec(
            id=current_spec.id,
            version=updated_version,
            description=updated_description,
            template=updated_template,
            inputs=updated_inputs_dict,
            metadata=updated_metadata,
        )

        vault.registry.save(updated_spec)
        vault.invalidate_cache()

        return TemplateResponse(
            id=updated_spec.id,
            version=updated_spec.version,
            description=updated_spec.description,
            template=updated_spec.template,
            inputs={
                name: {
                    "type": input_spec.type,
                    "required": input_spec.required,
                    "default": input_spec.default,
                }
                for name, input_spec in updated_spec.inputs.items()
            },
            metadata=updated_spec.metadata,
        )

    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str, vault: Vault = Depends(get_vault)
):
    """Delete a template from the registry.
    
    For Azure registries with versioning enabled, this marks the current version
    as deleted but preserves version history. The template will no longer appear
    in listings or be loadable, but previous versions remain accessible through
    the versioning API.
    
    For local registries, the template file is permanently deleted.
    
    Args:
        template_id: The ID of the template to delete
        
    Returns:
        204 No Content on success
        
    Raises:
        404: Template not found
        500: Deletion failed
    """
    try:
        # First check if template exists
        try:
            vault.get(template_id)
        except TemplateNotFound:
            raise HTTPException(
                status_code=404, 
                detail=f"Template '{template_id}' not found"
            )
        
        # Delete the template
        vault.registry.delete(template_id)
        
        # Invalidate cache
        vault.invalidate_cache()
        
        # Return 204 No Content (standard for successful DELETE)
        return Response(status_code=204)
        
    except HTTPException:
        raise
    except TemplateNotFound:
        raise HTTPException(
            status_code=404, 
            detail=f"Template '{template_id}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete template: {str(e)}"
        )