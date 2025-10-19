from __future__ import annotations
from typing import Any, Dict
from jinja2 import Environment, StrictUndefined
import yaml

def _yaml_dump(obj: Any) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True).rstrip()

def make_env() -> Environment:
    env = Environment(autoescape=False, undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.filters["default"] = lambda val, dflt="": (val if val not in (None, "", [], {}) else dflt)
    env.filters["yaml"] = _yaml_dump
    return env

class Renderer:
    def __init__(self) -> None:
        self.env = make_env()

    def render(self, template_text: str, variables: Dict[str, Any]) -> str:
        try:
            tmpl = self.env.from_string(template_text)
            return tmpl.render(**variables)
        except Exception as e:
            # bubble up as simple string; v0.1 doesn't need rich trace mapping
            raise RuntimeError(f"render error: {e}") from e