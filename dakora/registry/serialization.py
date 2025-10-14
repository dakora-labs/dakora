from __future__ import annotations
from typing import Optional, Dict, Any
import yaml

from ..model import TemplateSpec

"""Template serialization utilities shared by all registries.

Responsibilities:
- Parse YAML text into dict (lossy – like previous behavior).
- Render TemplateSpec into deterministic YAML, preserving select original metadata/inputs.

NOTE: We intentionally keep logic conservative; unknown top-level keys from the
original text are preserved when provided.
"""

__all__ = ["parse_yaml", "render_yaml"]


def parse_yaml(text: str) -> Dict[str, Any]:
    return yaml.safe_load(text) or {}


def _needs_quote(s: str) -> bool:
    return (
        s != s.strip()
        or any(ch in s for ch in [":", "#"])
        or s.startswith(
            ("-", "?", "{", "}", "[", "]", "!", "*", "&", ">", "|", "@", "`")
        )
        or "\n" in s
    )


def _q(s: str) -> str:
    return '"' + s.replace('"', '\\"') + '"'


def render_yaml(spec: TemplateSpec, original_text: Optional[str]) -> str:
    original: Dict[str, Any] | None = None
    if original_text:
        try:
            original = parse_yaml(original_text)
        except Exception:  # pragma: no cover
            original = None

    orig_inputs = original.get("inputs", {}) if isinstance(original, dict) else {}
    orig_metadata = original.get("metadata", {}) if isinstance(original, dict) else {}

    lines: list[str] = []
    lines.append(f"id: {spec.id}")
    lines.append(f"version: {spec.version}")

    if spec.description is not None:
        orig_desc = original.get("description") if isinstance(original, dict) else None
        if orig_desc and orig_desc == spec.description and not _needs_quote(orig_desc):
            lines.append(f"description: {orig_desc}")
        else:
            if _needs_quote(spec.description):
                lines.append(f"description: {_q(spec.description)}")
            else:
                lines.append(f"description: {spec.description}")

    # Template rendering
    # Note: For multiline templates, YAML block scalar (|) automatically adds a trailing newline.
    # The load logic will normalize this by stripping trailing newlines to preserve the original intent.
    tmpl = spec.template or ""
    if '\n' not in tmpl:
        # Single-line template: keep inline without quotes if safe
        if _needs_quote(tmpl):
            lines.append(f"template: {_q(tmpl)}")
        else:
            lines.append(f"template: {tmpl}")
    else:
        # Multiline template: use block scalar format
        # Ensure template ends with newline for proper YAML block scalar formatting
        if not tmpl.endswith('\n'):
            tmpl += '\n'
        lines.append('template: |')
        for line in tmpl.split('\n')[:-1]:
            lines.append(f"  {line}" if line else "")

    # Inputs
    if spec.inputs or orig_inputs:
        lines.append("")
        lines.append("inputs:")
        for name, inp in spec.inputs.items():
            lines.append(f"  {name}:")
            lines.append(f"    type: {inp.type}")
            lines.append(f"    required: {'true' if inp.required else 'false'}")
            if inp.default is not None:
                if isinstance(inp.default, str):
                    lines.append(f"    default: {_q(inp.default)}")
                else:
                    lines.append(f"    default: {inp.default}")
            if name in orig_inputs:
                for k, v in orig_inputs[name].items():
                    if k in {"type", "required", "default"}:
                        continue
                    if isinstance(v, str):
                        lines.append(f"    {k}: {_q(v)}")
                    else:
                        lines.append(f"    {k}: {v}")

    # Metadata
    merged_meta: Dict[str, Any] = {}
    if orig_metadata and isinstance(orig_metadata, dict):
        merged_meta.update(orig_metadata)
    merged_meta.update(spec.metadata)

    if merged_meta:
        lines.append("")
        lines.append("metadata:")
        ordering = ["tags", "author", "use_cases"] + [
            k for k in merged_meta if k not in {"tags", "author", "use_cases"}
        ]
        for key in ordering:
            if key not in merged_meta:
                continue
            val = merged_meta[key]
            if key in {"tags", "use_cases"} and isinstance(val, (list, tuple)):
                items = ", ".join(_q(str(x)) for x in val)
                lines.append(f"  {key}: [{items}]")
            elif isinstance(val, str):
                if _needs_quote(val):
                    lines.append(f"  {key}: {_q(val)}")
                else:
                    lines.append(f"  {key}: {val}")
            else:
                lines.append(f"  {key}: {val}")

    return "\n".join(lines).rstrip() + "\n"
