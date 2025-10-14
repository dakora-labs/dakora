from __future__ import annotations
from typing import Dict, Optional, Any, List
from pathlib import Path
import yaml
from threading import RLock

from .renderer import Renderer
from .registry import LocalRegistry, Registry
from .model import TemplateSpec
from .exceptions import ValidationError, RenderError, DakoraError
from .logging import Logger
from .llm.client import LLMClient
from .llm.models import ExecutionResult, ComparisonResult

class Vault:
    """
    Vault manages prompt templates with flexible storage backends.
    
    Examples:
        # Direct registry injection (recommended)
        from dakora.registry import LocalRegistry, AzureRegistry
        vault = Vault(LocalRegistry("./prompts"))
        
        # With logging
        vault = Vault(
            LocalRegistry("./prompts"),
            logging_enabled=True,
            logging_db_path="./dakora.db"
        )
        
        # Azure storage
        vault = Vault(AzureRegistry(
            container="prompts",
            account_url="https://..."
        ))
        
        # Legacy config file (still supported)
        vault = Vault.from_config("dakora.yaml")
    """
    def __init__(
        self,
        registry: Registry | str | None = None,
        *,
        logging_enabled: bool = False,
        logging_db_path: str = "./dakora.db",
        # Legacy support
        prompt_dir: str | None = None,
    ):
        """Initialize Vault with a registry.
        
        Args:
            registry: A Registry instance (LocalRegistry, AzureRegistry, etc.) 
                     OR a path to dakora.yaml config file
            logging_enabled: Enable execution logging
            logging_db_path: Path to SQLite database for logs
            prompt_dir: (Legacy) Shorthand for LocalRegistry(prompt_dir)
            
        Raises:
            DakoraError: If no registry provided or configuration is invalid
        """
        # Handle different initialization patterns
        if isinstance(registry, str):
            # String could be config path - try to load as config
            if registry.endswith(('.yaml', '.yml')) or '/' in registry or '\\' in registry:
                # Looks like a file path, use legacy config loading
                config = self._load_config(registry)
                self.registry = self._create_registry(config)
                self.config = config
            else:
                raise DakoraError(f"String registry must be a config file path, got: {registry}")
        elif isinstance(registry, Registry):
            self.registry = registry
            self.config = {
                "logging": {
                    "enabled": logging_enabled,
                    "db_path": logging_db_path
                }
            }
        elif prompt_dir is not None:
            # Legacy: prompt_dir shorthand
            self.registry = LocalRegistry(prompt_dir)
            self.config = {
                "registry": "local",
                "prompt_dir": prompt_dir,
                "logging": {
                    "enabled": logging_enabled,
                    "db_path": logging_db_path
                }
            }
        elif registry is None:
            raise DakoraError(
                "Must provide a registry. Examples:\n"
                "  Vault(LocalRegistry('./prompts'))\n"
                "  Vault(AzureRegistry(container='prompts', ...))\n"
                "  Vault.from_config('dakora.yaml')\n"
                "  Vault(prompt_dir='./prompts')  # legacy"
            )
        else:
            raise DakoraError(f"Invalid registry type: {type(registry)}")
        
        self.renderer = Renderer()
        self.logger = Logger(self.config["logging"]["db_path"]) if self.config.get("logging", {}).get("enabled") else None
        self._cache: Dict[str, TemplateSpec] = {}
        self._lock = RLock()

    @classmethod
    def from_config(cls, config_path: str) -> "Vault":
        """Create Vault from a configuration file.
        
        Args:
            config_path: Path to dakora.yaml configuration file
            
        Returns:
            Configured Vault instance
            
        Example:
            vault = Vault.from_config("dakora.yaml")
        """
        config = cls._load_config(config_path)
        registry = cls._create_registry(config)
        
        # Create instance with the registry
        instance = cls.__new__(cls)
        instance.registry = registry
        instance.config = config
        instance.renderer = Renderer()
        instance.logger = Logger(config["logging"]["db_path"]) if config.get("logging", {}).get("enabled") else None
        instance._cache = {}
        instance._lock = RLock()
        return instance

    @staticmethod
    def _load_config(path: str) -> Dict:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        registry_type = data.get("registry", "local")
        if registry_type == "local":
            if "prompt_dir" not in data:
                raise DakoraError("dakora.yaml missing prompt_dir for local registry")
        elif registry_type == "azure":
            if "azure_container" not in data:
                raise DakoraError("dakora.yaml missing azure_container for azure registry")
        else:
            raise DakoraError(f"Unknown registry type: {registry_type}")
        if "logging" not in data:
            data["logging"] = {"enabled": False}
        return data

    @staticmethod
    def _create_registry(config: Dict) -> Registry:
        registry_type = config.get("registry", "local")
        if registry_type == "local":
            return LocalRegistry(config["prompt_dir"])
        if registry_type == "azure":  # lazy import so azure deps are optional
            try:
                from .registry import AzureRegistry
            except ImportError as e:  # pragma: no cover - runtime only
                raise DakoraError("Azure support requires installing optional dependencies: pip install 'dakora[azure]'") from e
            return AzureRegistry(
                container=config["azure_container"],
                prefix=config.get("azure_prefix", "prompts/"),
                connection_string=config.get("azure_connection_string"),
                account_url=config.get("azure_account_url"),
            )
        raise DakoraError(f"Unsupported registry type: {registry_type}")

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

    # Resource management -------------------------------------------------
    def close(self) -> None:
        if self.logger:
            try:
                self.logger.close()
            except Exception:
                pass

    def __enter__(self):  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - convenience
        self.close()

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

    async def compare(self, models: List[str], **kwargs: Any) -> ComparisonResult:
        """
        Execute template against multiple LLM models in parallel.

        Args:
            models: List of LLM model identifiers (e.g., ['gpt-4', 'claude-3-opus', 'gemini-pro'])
            **kwargs: Template inputs merged with LiteLLM parameters
                     Template inputs are extracted based on spec.inputs
                     Remaining kwargs are passed directly to LiteLLM

        Returns:
            ComparisonResult with results for each model and aggregate statistics

        Raises:
            ValidationError: Invalid template inputs
            RenderError: Template rendering failed
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

        comparison = await self._llm_client.compare(prompt, models, **llm_params)

        if self.vault.logger:
            for result in comparison.results:
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

        return comparison

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