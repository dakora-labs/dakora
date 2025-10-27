from __future__ import annotations
from typing import Dict, Optional, Any, List, Callable
from types import TracebackType
from pathlib import Path
import yaml
from threading import RLock

from .renderer import Renderer
from .registry import LocalRegistry, Registry
from .model import TemplateSpec
from .exceptions import ValidationError, RenderError, DakoraError


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

    # Type annotations for instance attributes
    registry: Registry
    config: Dict[str, Any]
    renderer: Renderer
    _cache: Dict[str, TemplateSpec]
    _lock: RLock

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
            if (
                registry.endswith((".yaml", ".yml"))
                or "/" in registry
                or "\\" in registry
            ):
                # Looks like a file path, use legacy config loading
                config = self._load_config(registry)
                self.registry = self._create_registry(config)
                self.config = config
            else:
                raise DakoraError(
                    f"String registry must be a config file path, got: {registry}"
                )
        elif isinstance(registry, Registry):
            self.registry = registry
            self.config: Dict[str, Any] = {
                "logging": {"enabled": logging_enabled, "db_path": logging_db_path}
            }
        elif prompt_dir is not None:
            # Legacy: prompt_dir shorthand
            self.registry = LocalRegistry(prompt_dir)
            self.config: Dict[str, Any] = {
                "registry": "local",
                "prompt_dir": prompt_dir,
                "logging": {"enabled": logging_enabled, "db_path": logging_db_path},
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
        instance._cache = {}
        instance._lock = RLock()
        return instance

    @staticmethod
    def _load_config(path: str) -> Dict[str, Any]:
        data: Dict[str, Any] = (
            yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        )
        registry_type: str = str(data.get("registry", "local"))
        if registry_type == "local":
            if "prompt_dir" not in data:
                raise DakoraError("dakora.yaml missing prompt_dir for local registry")
        elif registry_type == "azure":
            if "azure_container" not in data:
                raise DakoraError(
                    "dakora.yaml missing azure_container for azure registry"
                )
        else:
            raise DakoraError(f"Unknown registry type: {registry_type}")
        if "logging" not in data:
            data["logging"] = {"enabled": False}
        return data

    @staticmethod
    def _create_registry(config: Dict[str, Any]) -> Registry:
        registry_type: str = str(config.get("registry", "local"))
        if registry_type == "local":
            return LocalRegistry(str(config["prompt_dir"]))
        if registry_type == "azure":  # lazy import so azure deps are optional
            try:
                from .registry import AzureRegistry
            except ImportError as e:  # pragma: no cover - runtime only
                raise DakoraError(
                    "Azure support requires installing optional dependencies: pip install 'dakora[azure]'"
                ) from e
            return AzureRegistry(
                container=str(config["azure_container"]),
                prefix=str(config.get("azure_prefix", "")),
                connection_string=config.get("azure_connection_string"),
                account_url=config.get("azure_account_url"),
            )
        raise DakoraError(f"Unsupported registry type: {registry_type}")

    def list(self) -> List[str]:
        """List all template IDs in the vault.

        Returns:
            List of template IDs.
        """
        return list(self.registry.list_ids())

    def invalidate_cache(self) -> None:
        """Clear the template cache."""
        with self._lock:
            self._cache.clear()

    def delete(self, template_id: str) -> None:
        """Delete a template from the vault.

        Args:
            template_id: The template ID to delete

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        self.registry.delete(template_id)
        self.invalidate_cache()

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
        pass

    def __enter__(self) -> "Vault":  # pragma: no cover - convenience
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:  # pragma: no cover - convenience
        self.close()


class TemplateHandle:
    """Handle for interacting with a specific template in the vault."""

    def __init__(self, vault: Vault, spec: TemplateSpec) -> None:
        self.vault = vault
        self.spec = spec

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def version(self) -> str:
        return self.spec.version

    @property
    def template(self) -> str:
        return self.spec.template

    @property
    def inputs(self) -> Dict[str, Any]:
        return self.spec.inputs

    def render(self, **kwargs: Any) -> str:
        try:
            vars = self.spec.coerce_inputs(kwargs)
        except Exception as e:
            raise ValidationError(str(e)) from e
        try:
            return self.vault.renderer.render(self.spec.template, vars)
        except Exception as e:
            raise RenderError(str(e)) from e

    def run(self, func: Callable[[str], Any], **kwargs: Any) -> Any:
        """Execute a call with logging.

        Args:
            func: Function that takes a prompt string and returns output
            **kwargs: Template input variables

        Returns:
            Output from the provided function

        Example:
            out = tmpl.run(lambda prompt: call_llm(prompt), input_text="...")
        """
        vars: Dict[str, Any] = self.spec.coerce_inputs(kwargs)
        prompt: str = self.vault.renderer.render(self.spec.template, vars)
        rec: Dict[str, Any] = {
            "inputs": vars,
            "output": None,
            "cost": None,
            "latency_ms": None,
        }
        out: Any = func(prompt)
        rec["output"] = out
        return out
