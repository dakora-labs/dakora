"""Project-scoped prompts API routes."""

from typing import List, Dict, Any, Tuple
import logging
import re
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.engine import Engine

from ..core.vault import Vault
from ..core.model import InputSpec, TemplateSpec
from ..core.exceptions import TemplateNotFound, ValidationError
from ..core.prompt_manager import PromptManager
from ..core.database import get_engine, prompts_table, get_connection, projects_table
from ..auth import validate_project_access, get_project_vault
from sqlalchemy import select, func
from .schemas import (
    TemplateResponse,
    CreateTemplateRequest,
    UpdateTemplateRequest,
    RenderRequest,
    RenderResponse,
    VersionHistoryResponse,
    VersionHistoryItem,
    RollbackRequest,
    ValidateTemplateRequest,
    ValidateTemplateResponse,
    ValidationIssue,
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


def _get_version_number(project_id: UUID, prompt_id: str, engine: Engine) -> int | None:
    """Helper to get version_number from database.

    Args:
        project_id: Project UUID
        prompt_id: Prompt ID
        engine: Database engine

    Returns:
        Version number or None if not found/no-auth mode
    """
    with get_connection(engine) as conn:
        # Check if project exists (no-auth mode check)
        project_exists = conn.execute(
            select(projects_table.c.id).where(projects_table.c.id == project_id)
        ).fetchone()

        if not project_exists:
            return None

        # Get version number from prompts table
        result = conn.execute(
            select(prompts_table.c.version_number).where(
                prompts_table.c.project_id == project_id,
                prompts_table.c.prompt_id == prompt_id,
            )
        ).fetchone()

        return result[0] if result else None


@router.get("", response_model=List[TemplateResponse])
async def list_prompts(
    manager: PromptManager = Depends(get_prompt_manager),
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
):
    """List all prompts in the project with summary information from database.

    This endpoint returns prompt metadata from the database without loading
    template content from blob storage, making it much faster for listing views.
    """
    try:
        with get_connection(engine) as conn:
            result = conn.execute(
                select(
                    prompts_table.c.prompt_id,
                    prompts_table.c.version,
                    prompts_table.c.version_number,
                    prompts_table.c.description,
                    prompts_table.c.metadata,
                )
                .where(prompts_table.c.project_id == project_id)
                .order_by(prompts_table.c.last_updated_at.desc())
            ).fetchall()

            return [
                TemplateResponse(
                    id=row[0],
                    version=row[1],
                    version_number=row[2],
                    description=row[3],
                    template="",  # Not loaded for list view
                    inputs={},  # Not loaded for list view
                    metadata=row[4] or {},
                )
                for row in result
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{prompt_id}", response_model=TemplateResponse)
async def get_prompt(
    prompt_id: str,
    manager: PromptManager = Depends(get_prompt_manager),
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
):
    """Get a specific prompt with all its details."""
    try:
        template = manager.load(prompt_id)
        spec = template if isinstance(template, TemplateSpec) else template.spec

        # Strip trailing newline for consistent API responses
        tmpl = spec.template[:-1] if spec.template.endswith("\n") else spec.template

        # Get version_number from database
        version_number = _get_version_number(project_id, prompt_id, engine)

        return TemplateResponse(
            id=spec.id,
            version=spec.version,
            version_number=version_number,
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
    request: CreateTemplateRequest,
    manager: PromptManager = Depends(get_prompt_manager),
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
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

        # Get version_number from database
        version_number = _get_version_number(project_id, request.id, engine)

        # Return the created prompt
        tmpl = spec.template[:-1] if spec.template.endswith("\n") else spec.template
        return TemplateResponse(
            id=spec.id,
            version=spec.version,
            version_number=version_number,
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
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
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

        # Get updated version_number from database
        version_number = _get_version_number(project_id, prompt_id, engine)

        return TemplateResponse(
            id=updated_spec.id,
            version=updated_spec.version,
            version_number=version_number,
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


@router.post("/{prompt_id}/render", response_model=RenderResponse)
async def render_prompt(
    prompt_id: str,
    request: RenderRequest,
    project_id: UUID = Depends(validate_project_access),
    manager: PromptManager = Depends(get_prompt_manager),
    engine: Engine = Depends(get_engine),
):
    """Render a prompt template with variables.

    This endpoint resolves {% include %} directives by loading prompt parts
    from the database and renders Jinja2 templates with provided input variables.

    Args:
        prompt_id: The ID of the prompt to render
        request: Render request with input variables
        project_id: Validated project UUID
        manager: PromptManager instance

    Returns:
        RenderResponse with rendered template text

    Raises:
        404: Prompt not found
        400: Validation or rendering error
        500: Internal server error
    """
    try:
        from ..core.renderer import Renderer

        template = manager.load(prompt_id)
        spec = template if isinstance(template, TemplateSpec) else template.spec

        renderer = Renderer(engine=engine, project_id=project_id)

        if request.resolve_includes_only:
            # Only resolve includes, keep variables as placeholders
            rendered = renderer.resolve_includes(spec.template)
        else:
            # Full render with variable substitution
            rendered = renderer.render(spec.template, request.inputs)

        return RenderResponse(rendered=rendered, inputs_used=request.inputs)

    except TemplateNotFound:
        raise HTTPException(
            status_code=404, detail=f"Prompt '{prompt_id}' not found"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"Render error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _line_col_from_index(source: str, index: int) -> Tuple[int, int]:
    """Convert a string index to 1-based (line, column)."""
    line = source.count("\n", 0, index) + 1
    last_newline = source.rfind("\n", 0, index)
    if last_newline == -1:
        col = index + 1
    else:
        col = index - last_newline
    return line, col


RAW_BLOCK_PATTERN = re.compile(
    r"{%\s*raw\s*%}.*?{%\s*endraw\s*%}",
    re.IGNORECASE | re.DOTALL,
)


def _detect_brace_issues(template: str) -> list[ValidationIssue]:
    """Detect unmatched double-curly braces commonly caused by typos."""
    issues: list[ValidationIssue] = []
    raw_spans = [(m.start(), m.end()) for m in RAW_BLOCK_PATTERN.finditer(template)]
    span_idx = 0
    current_span = raw_spans[span_idx] if raw_spans else None

    def advance_span(pos: int):
        nonlocal span_idx, current_span
        while current_span and pos >= current_span[1]:
            span_idx += 1
            current_span = raw_spans[span_idx] if span_idx < len(raw_spans) else None

    stack: list[int] = []
    i = 0
    length = len(template)

    while i < length:
        if current_span and current_span[0] <= i < current_span[1]:
            i = current_span[1]
            advance_span(i)
            continue

        if template[i] == "{" and i + 1 < length and template[i + 1] == "{":
            stack.append(i)
            i += 2
            continue

        if template[i] == "}" and i + 1 < length and template[i + 1] == "}":
            if stack:
                stack.pop()
            else:
                line, col = _line_col_from_index(template, i)
                issues.append(
                    ValidationIssue(
                        message="Unmatched closing '}}'. Check for a missing opening '{{'.",
                        line=line,
                        column=col,
                        type="brace",
                    )
                )
            i += 2
            continue

        i += 1

    for idx in stack:
        line, col = _line_col_from_index(template, idx)
        issues.append(
            ValidationIssue(
                message="Opening '{{' is missing a closing '}}'.",
                line=line,
                column=col,
                type="brace",
            )
        )

    return issues


@router.post("/validate", response_model=ValidateTemplateResponse)
async def validate_template(
    request: ValidateTemplateRequest,
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
):
    """Validate a Jinja2 template for syntax and variable usage.

    - Parses the template to report syntax errors (line/column when available)
    - Extracts used variables via Jinja2's meta analysis
    - Optionally compares against declared variables to report missing/unused
    - Attempts to resolve include directives to catch missing parts
    """
    from jinja2 import TemplateSyntaxError
    from jinja2 import meta as jinja_meta

    errors: list[ValidationIssue] = []
    variables_used: set[str] = set()
    declared = set(request.declared_variables or [])

    # Build env with part loader for include resolution
    try:
        from ..core.renderer import Renderer, make_env

        # Use env without loader for parse/meta to avoid IO on syntax pass
        parse_env = make_env()
        try:
            ast = parse_env.parse(request.template)
            variables_used = set(jinja_meta.find_undeclared_variables(ast))
        except TemplateSyntaxError as e:
            errors.append(
                ValidationIssue(
                    message=str(e),
                    line=getattr(e, "lineno", None),
                    column=getattr(e, "offset", None),
                    type="syntax",
                )
            )

        # Try resolving includes to surface missing include parts (ignore variables)
        try:
            renderer = Renderer(engine=engine, project_id=project_id)
            # Will raise if include part is missing or loader fails
            _ = renderer.resolve_includes(request.template)
        except RuntimeError as e:
            errors.append(
                ValidationIssue(
                    message=str(e),
                    line=None,
                    column=None,
                    type="include",
                )
            )

        variables_missing = sorted(list(variables_used - declared)) if declared else []
        variables_unused = sorted(list(declared - variables_used)) if declared else []

        errors.extend(_detect_brace_issues(request.template))

        return ValidateTemplateResponse(
            ok=len(errors) == 0,
            variables_used=sorted(list(variables_used)),
            variables_missing=variables_missing,
            variables_unused=variables_unused,
            errors=errors,
        )

    except Exception as e:
        # Any unexpected error -> return as a generic issue but keep request working
        logging.getLogger(__name__).exception("Template validation failed")
        raise HTTPException(status_code=500, detail="Template validation failed")


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


@router.get("/{prompt_id}/versions", response_model=VersionHistoryResponse)
async def get_version_history(
    prompt_id: str, manager: PromptManager = Depends(get_prompt_manager)
):
    """Get version history for a prompt.

    Args:
        prompt_id: The ID of the prompt

    Returns:
        List of all versions with metadata

    Raises:
        404: Prompt not found
        500: Internal server error
    """
    try:
        versions = manager.get_version_history(prompt_id)

        return VersionHistoryResponse(
            versions=[
                VersionHistoryItem(
                    version=v["version"],
                    content_hash=v["content_hash"],
                    created_at=v["created_at"].isoformat(),
                    created_by=str(v["created_by"]),
                    metadata=v.get("metadata", {}),
                )
                for v in versions
            ]
        )
    except TemplateNotFound:
        raise HTTPException(
            status_code=404, detail=f"Prompt '{prompt_id}' not found"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{prompt_id}/versions/{version}", response_model=TemplateResponse)
async def get_version_content(
    prompt_id: str, version: int, manager: PromptManager = Depends(get_prompt_manager)
):
    """Get content of a specific prompt version.

    Args:
        prompt_id: The ID of the prompt
        version: Version number to retrieve

    Returns:
        Full prompt spec for the specified version

    Raises:
        404: Prompt or version not found
        500: Internal server error
    """
    try:
        spec = manager.get_version_content(prompt_id, version)

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
            status_code=404, detail=f"Prompt '{prompt_id}' or version {version} not found"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{prompt_id}/rollback", response_model=TemplateResponse)
async def rollback_prompt(
    prompt_id: str,
    request: RollbackRequest,
    manager: PromptManager = Depends(get_prompt_manager),
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
):
    """Rollback prompt to a previous version.

    Creates a new version with content from the specified version.

    Args:
        prompt_id: The ID of the prompt
        request: Rollback request with version number

    Returns:
        Updated prompt with new version number

    Raises:
        404: Prompt or version not found
        400: Invalid version number
        500: Internal server error
    """
    try:
        spec = manager.rollback_to_version(prompt_id, request.version)

        # Get new version_number from database
        version_number = _get_version_number(project_id, prompt_id, engine)

        return TemplateResponse(
            id=spec.id,
            version=spec.version,
            version_number=version_number,
            description=spec.description,
            template=spec.template,
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
            status_code=404, detail=f"Prompt '{prompt_id}' or version {request.version} not found"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
