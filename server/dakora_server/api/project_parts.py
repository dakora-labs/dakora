"""Project-scoped prompt parts API routes."""

from typing import List, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..core.part_manager import PartManager
from ..core.database import create_db_engine
from ..core.exceptions import PartNotFound, ValidationError
from ..auth import validate_project_access


router = APIRouter(
    prefix="/api/projects/{project_id}/parts", tags=["project-parts"]
)


class PartResponse(BaseModel):
    """Response model for a single prompt part."""

    id: str
    part_id: str
    category: str
    name: str
    description: Optional[str]
    content: str
    tags: List[str] = []
    version: Optional[str] = None
    created_at: Optional[str]
    updated_at: Optional[str]


class PartListResponse(BaseModel):
    """Response model for parts list grouped by category."""

    by_category: Dict[str, List[PartResponse]]


class CreatePartRequest(BaseModel):
    """Request model for creating a new part."""

    part_id: str
    category: str
    name: str
    content: str
    description: Optional[str] = None
    tags: List[str] = []
    version: Optional[str] = None


class UpdatePartRequest(BaseModel):
    """Request model for updating a part."""

    category: Optional[str] = None
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    version: Optional[str] = None


def get_part_manager(
    project_id: UUID = Depends(validate_project_access),
) -> PartManager:
    """Get a PartManager instance for the project.

    Args:
        project_id: Validated project UUID

    Returns:
        PartManager instance
    """
    engine = create_db_engine()
    return PartManager(engine, project_id)


@router.get("", response_model=PartListResponse)
async def list_parts(manager: PartManager = Depends(get_part_manager)):
    """List all prompt parts in the project, grouped by category."""
    try:
        by_category = manager.list_by_category()

        # Convert to response format
        response_by_category = {}
        for category, parts in by_category.items():
            response_by_category[category] = [
                PartResponse(**part.to_dict()) for part in parts
            ]

        return PartListResponse(by_category=response_by_category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{part_id}", response_model=PartResponse)
async def get_part(part_id: str, manager: PartManager = Depends(get_part_manager)):
    """Get a specific prompt part by ID."""
    try:
        part = manager.get(part_id)
        return PartResponse(**part.to_dict())
    except PartNotFound:
        raise HTTPException(status_code=404, detail=f"Part '{part_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=PartResponse, status_code=201)
async def create_part(
    request: CreatePartRequest, manager: PartManager = Depends(get_part_manager)
):
    """Create a new prompt part in the project."""
    try:
        part = manager.create(
            part_id=request.part_id,
            category=request.category,
            name=request.name,
            content=request.content,
            description=request.description,
        )
        return PartResponse(**part.to_dict())
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{part_id}", response_model=PartResponse)
async def update_part(
    part_id: str,
    request: UpdatePartRequest,
    manager: PartManager = Depends(get_part_manager),
):
    """Update an existing prompt part."""
    try:
        part = manager.update(
            part_id=part_id,
            category=request.category,
            name=request.name,
            content=request.content,
            description=request.description,
        )
        return PartResponse(**part.to_dict())
    except PartNotFound:
        raise HTTPException(status_code=404, detail=f"Part '{part_id}' not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{part_id}", status_code=204)
async def delete_part(part_id: str, manager: PartManager = Depends(get_part_manager)):
    """Delete a prompt part."""
    try:
        manager.delete(part_id)
    except PartNotFound:
        raise HTTPException(status_code=404, detail=f"Part '{part_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))