from __future__ import annotations
from typing import Dict, Optional, Any
from pathlib import Path
import yaml
from threading import RLock

from .renderer import Renderer
from .registry.local import LocalRegistry
from .model import TemplateSpec
from .exceptions import ValidationError, RenderError, TemplateNotFound, DakoraError
from .logging import Logger
from .llm.client import LLMClient
from .llm.models import ExecutionResult

class Vault:
    """
    Public API.
    - load templates from local dir
    - render with validated variables
    - optional logging
    - hot-reload via invalidate_cache()
    """
    def __init__(self, config_path: str | None = None, prompt_dir: str | None = None):
        if not (config_path or prompt_dir):
            raise DakoraError("pass config_path or prompt_dir")
        self.config = self._load_config(config_path) if config_path else {"prompt_dir": prompt_dir, "logging": {"enabled": False}}
        self.registry = LocalRegistry(self.config["prompt_dir"])
        self.renderer = Renderer()
        self.logger = Logger(self.config["logging"]["db_path"]) if self.config.get("logging", {}).get("enabled") else None
        self._cache: Dict[str, TemplateSpec] = {}
        self._lock = RLock()

    @staticmethod
    def _load_config(path: str) -> Dict:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if "prompt_dir" not in data:
            raise DakoraError("dakora.yaml missing prompt_dir")
        if "logging" not in data:
            data["logging"] = {"enabled": False}
        return data

    def list(self):
        return list(self.registry.list_ids())

    def invalidate_cache(self):
        with self._lock:
            self._cache.clear()

    def get_spec(self, template_id: str) -> TemplateSpec:
        with self._lock:
            if template_id in self._cache:
                return self._cache[template_id]
            spec = self.registry.load(template_id)
            self._cache[template_id] = spec
            return spec

    # public surface used by apps
    def get(self, template_id: str) -> "TemplateHandle":
        spec = self.get_spec(template_id)
        return TemplateHandle(self, spec)

class TemplateHandle:
    def __init__(self, vault: Vault, spec: TemplateSpec):
        self.vault = vault
        self.spec = spec
        self._llm_client: Optional[LLMClient] = None

    @property
    def id(self): return self.spec.id
    @property
    def version(self): return self.spec.version
    @property
    def inputs(self): return self.spec.inputs

    def render(self, **kwargs) -> str:
        try:
            vars = self.spec.coerce_inputs(kwargs)
        except Exception as e:
            raise ValidationError(str(e)) from e
        try:
            return self.vault.renderer.render(self.spec.template, vars)
        except Exception as e:
            raise RenderError(str(e)) from e

    def execute(self, model: str, **kwargs: Any) -> ExecutionResult:
        """
        Execute template against an LLM model with full LiteLLM parameter support.

        Args:
            model: LLM model identifier (e.g., 'gpt-4', 'claude-3-opus', 'gemini-pro')
            **kwargs: Template inputs merged with LiteLLM parameters
                     Template inputs are extracted based on spec.inputs
                     Remaining kwargs are passed directly to LiteLLM

        Returns:
            ExecutionResult with output, provider, model, tokens, cost, and latency

        Raises:
            ValidationError: Invalid template inputs
            RenderError: Template rendering failed
            LLMError: LLM execution failed (APIKeyError, RateLimitError, ModelNotFoundError)
        """
        if self._llm_client is None:
            self._llm_client = LLMClient()

        template_input_names = set(self.spec.inputs.keys())
        template_inputs = {k: v for k, v in kwargs.items() if k in template_input_names}
        llm_params = {k: v for k, v in kwargs.items() if k not in template_input_names}

        try:
            vars = self.spec.coerce_inputs(template_inputs)
        except Exception as e:
            raise ValidationError(str(e)) from e

        try:
            prompt = self.vault.renderer.render(self.spec.template, vars)
        except Exception as e:
            raise RenderError(str(e)) from e

        result = self._llm_client.execute(prompt, model, **llm_params)

        if self.vault.logger:
            self.vault.logger.write(
                prompt_id=self.id,
                version=self.version,
                inputs=vars,
                output=result.output,
                cost=None,
                latency_ms=result.latency_ms,
                provider=result.provider,
                model=result.model,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cost_usd=result.cost_usd
            )

        return result

    def run(self, func, **kwargs):
        """
        Execute a call with logging.
        Usage:
            out = tmpl.run(lambda prompt: call_llm(prompt), input_text="...")
        """
        vars = self.spec.coerce_inputs(kwargs)
        prompt = self.vault.renderer.render(self.spec.template, vars)
        rec = {"inputs": vars, "output": None, "cost": None, "latency_ms": None}
        out = func(prompt)
        rec["output"] = out
        if self.vault.logger:
            self.vault.logger.write(self.id, self.version, rec["inputs"], rec["output"])
        return out