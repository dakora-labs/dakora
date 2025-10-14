from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator
from .types import InputType


class InputSpec(BaseModel):
    type: InputType = "string"
    required: bool = True
    default: Optional[Any] = None

    @field_validator("default")
    @classmethod
    def check_default(cls, v, info):
        # type sanity; strict enough for v0.1
        t: str = info.data.get("type", "string")
        if v is None:
            return v
        match t:
            case "string":
                if not isinstance(v, str):
                    raise ValueError("default must be str")
            case "number":
                if not isinstance(v, (int, float)):
                    raise ValueError("default must be number")
            case "boolean":
                if not isinstance(v, bool):
                    raise ValueError("default must be bool")
            case "array<string>":
                if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                    raise ValueError("default must be list[str]")
            case "object":
                if not isinstance(v, dict):
                    raise ValueError("default must be dict")
        return v


class TemplateSpec(BaseModel):
    id: str
    version: str = "0.1.0"
    description: Optional[str] = None
    template: str
    inputs: Dict[str, InputSpec] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def coerce_inputs(self, provided: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        # apply defaults, check required, type coercion
        for name, spec in self.inputs.items():
            if name in provided:
                val = provided[name]
            else:
                if spec.required and spec.default is None:
                    raise ValueError(f"missing input: {name}")
                val = spec.default
            out[name] = self._coerce_type(name, val, spec.type)
        # ignore extra keys
        return out

    @staticmethod
    def _coerce_type(name: str, val: Any, t: str) -> Any:
        if val is None:
            return None
        try:
            match t:
                case "string":
                    return str(val)
                case "number":
                    if isinstance(val, bool):  # avoid bool as int
                        raise TypeError()
                    return float(val) if not isinstance(val, (int, float)) else val
                case "boolean":
                    if isinstance(val, bool):
                        return val
                    if isinstance(val, str):
                        return val.lower() in {"1", "true", "yes", "y"}
                    if isinstance(val, (int, float)):
                        return val != 0
                    raise TypeError()
                case "array<string>":
                    if isinstance(val, str):
                        return [val]
                    if isinstance(val, list) and all(isinstance(x, str) for x in val):
                        return val
                    raise TypeError()
                case "object":
                    if isinstance(val, dict):
                        return val
                    raise TypeError()
                case _:
                    raise TypeError()
        except TypeError:
            raise ValueError(f"type mismatch for '{name}': expected {t}")
