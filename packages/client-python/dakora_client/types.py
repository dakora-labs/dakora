"""Type definitions for Dakora client"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class TemplateInfo(BaseModel):
    id: str
    version: str
    description: Optional[str]
    template: str
    inputs: Dict[str, Any]
    metadata: Dict[str, Any]


class RenderResult(BaseModel):
    rendered: str
    inputs_used: Dict[str, Any]


class CompareResult(BaseModel):
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]