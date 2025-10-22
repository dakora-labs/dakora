"""Project-scoped prompts API routes."""

from typing import List, Dict
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.engine import Engine

from ..core.vault import Vault
from ..core.model import InputSpec, TemplateSpec
from ..core.exceptions import TemplateNotFound, ValidationError
from ..core.prompt_manager import PromptManager
from ..core.database import get_engine
from ..auth import validate_project_access, get_project_vault
from .schemas import (
    TemplateResponse,
    CreateTemplateRequest,
    UpdateTemplateRequest,
)

router = APIRouter(
    prefix="/api/projects/{project_id}/prompts", tags=["project-prompts"]
)


def get_prompt_manager(
    project_id: UUID = Depends(validate_project_access),
    vault: Vault = Depends(get_project_vault),
    engine: Engine = Depends(get_engine),
) -> PromptManager:
    """Get a PromptManager instance for the project.

    Args:
        project_id: Validated project UUID
        vault: Project-scoped vault instance
        engine: Global database engine

    Returns:
        PromptManager instance
    """
    return PromptManager(vault.registry, engine, project_id)


@router.get("", response_model=List[str])
async def list_prompts(manager: PromptManager = Depends(get_prompt_manager)):
    """List all prompt IDs in the project."""
    try:
        return manager.list_ids()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{prompt_id}", response_model=TemplateResponse)
async def get_prompt(
    prompt_id: str, manager: PromptManager = Depends(get_prompt_manager)
):
    """Get a specific prompt with all its details."""
    try:
        template = manager.load(prompt_id)
        spec = template if isinstance(template, TemplateSpec) else template.spec

        # Strip trailing newline for consistent API responses
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
            status_code=404, detail=f"Prompt '{prompt_id}' not found"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_prompt(
    request: CreateTemplateRequest, manager: PromptManager = Depends(get_prompt_manager)
):
    """Create a new prompt in the project."""
    try:
        if not request.id or request.id.strip() == "":
            raise HTTPException(status_code=422, detail="Prompt ID cannot be empty")

        # Check if prompt already exists
        try:
            manager.load(request.id)
            raise HTTPException(
                status_code=400, detail=f"Prompt '{request.id}' already exists"
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

        spec = TemplateSpec(
            id=request.id,
            version=request.version,
            description=request.description,
            template=request.template,
            inputs=inputs_dict,
            metadata=request.metadata,
        )

        # Save to both blob storage and database
        manager.save(spec)

        # Return the created prompt
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


@router.put("/{prompt_id}", response_model=TemplateResponse)
async def update_prompt(
    prompt_id: str,
    request: UpdateTemplateRequest,
    manager: PromptManager = Depends(get_prompt_manager),
):
    """Update an existing prompt in the project."""
    try:
        # Load current prompt
        try:
            current_template = manager.load(prompt_id)
            current_spec = (
                current_template
                if isinstance(current_template, TemplateSpec)
                else current_template.spec
            )
        except TemplateNotFound:
            raise HTTPException(
                status_code=404, detail=f"Prompt '{prompt_id}' not found"
            )

        # Apply updates
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

        updated_spec = TemplateSpec(
            id=current_spec.id,
            version=updated_version,
            description=updated_description,
            template=updated_template,
            inputs=updated_inputs_dict,
            metadata=updated_metadata,
        )

        # Save to both blob storage and database
        manager.save(updated_spec)

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


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: str, manager: PromptManager = Depends(get_prompt_manager)
):
    """Delete a prompt from the project.

    Removes both the database record and the blob storage file.

    Args:
        prompt_id: The ID of the prompt to delete

    Returns:
        204 No Content on success

    Raises:
        404: Prompt not found
        500: Deletion failed
    """
    try:
        # Delete from both blob storage and database
        manager.delete(prompt_id)

        # Return 204 No Content
        return Response(status_code=204)

    except TemplateNotFound:
        raise HTTPException(
            status_code=404, detail=f"Prompt '{prompt_id}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete prompt: {str(e)}"
        )