from __future__ import annotations
from typing import Any, Dict, Optional
from uuid import UUID
from jinja2 import Environment, StrictUndefined, BaseLoader
from sqlalchemy.engine import Engine
import yaml

def _yaml_dump(obj: Any) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True).rstrip()

def make_env(loader: Optional[BaseLoader] = None) -> Environment:
    """Create Jinja2 environment with optional custom loader.

    Args:
        loader: Optional Jinja2 loader for {% include %} statements
    """
    env = Environment(
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
        loader=loader
    )
    env.filters["default"] = lambda val, dflt="": (val if val not in (None, "", [], {}) else dflt)
    env.filters["yaml"] = _yaml_dump
    return env

class Renderer:
    def __init__(self, engine: Optional[Engine] = None, project_id: Optional[UUID] = None) -> None:
        """Initialize renderer with optional part loading support.

        Args:
            engine: SQLAlchemy engine for loading parts from DB
            project_id: Project UUID for scoping part access
        """
        if engine and project_id:
            # Import here to avoid circular dependency
            from .part_loader import PartLoader
            loader = PartLoader(engine, project_id)
            self.env = make_env(loader=loader)
        else:
            self.env = make_env()

    def render(self, template_text: str, variables: Dict[str, Any]) -> str:
        try:
            tmpl = self.env.from_string(template_text)
            return tmpl.render(**variables)
        except Exception as e:
            # bubble up as simple string; v0.1 doesn't need rich trace mapping
            raise RuntimeError(f"render error: {e}") from e

    def resolve_includes(self, template_text: str) -> str:
        """Resolve {% include %} directives but leave {{ variables }} as-is.

        This is useful for previewing templates with parts resolved but variables
        still visible as placeholders.
        """
        try:
            # First pass: render to resolve includes, but provide a custom
            # undefined class that returns the original variable syntax
            from jinja2 import Undefined

            class PreserveUndefined(Undefined):
                """Custom undefined that preserves the original variable syntax."""
                def __str__(self):
                    return f"{{{{ {self._undefined_name} }}}}"

                def __getattr__(self, name):
                    # Preserve dot notation like {{ var.field }}
                    return PreserveUndefined(name=f"{self._undefined_name}.{name}")

            # Create a temporary environment with our custom undefined
            temp_env = Environment(
                autoescape=False,
                undefined=PreserveUndefined,
                trim_blocks=False,
                lstrip_blocks=False,
                loader=self.env.loader
            )
            temp_env.filters.update(self.env.filters)

            tmpl = temp_env.from_string(template_text)
            return tmpl.render()
        except Exception as e:
            raise RuntimeError(f"render error: {e}") from e