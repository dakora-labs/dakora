from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable
from ..model import TemplateSpec

class Registry(ABC):
    """Base template registry interface.
    
    All registries support reading (list_ids, load) and writing (save) templates.
    """
    
    @abstractmethod
    def list_ids(self) -> Iterable[str]: ...

    @abstractmethod
    def load(self, template_id: str) -> TemplateSpec: ...

    @abstractmethod
    def save(self, spec: TemplateSpec) -> None: ...