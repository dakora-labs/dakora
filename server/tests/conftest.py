"""
Test configuration and fixtures for Dakora tests
"""

import tempfile
import os
from pathlib import Path
import yaml
import pytest
import threading
import time
import requests
from contextlib import contextmanager

from dakora_server.core.vault import Vault

try:
    from dakora.playground import create_playground  # type: ignore
except Exception:
    # Fallback: create a minimal playground wrapper using the local FastAPI app
    from dakora_server.main import create_app
    import uvicorn

    class _FallbackPlayground:
        def __init__(self, host: str, port: int, vault: Vault):
            self.host = host
            self.port = port
            self.vault: Vault = vault
            self.app = create_app()

        def run(self, debug: bool = False):
            uvicorn.run(self.app, host=self.host, port=self.port, reload=debug)

    from typing import Optional

    def create_playground(
        config_path: Optional[str] = None,
        prompt_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> _FallbackPlayground:
        # Create a Vault instance and return a simple Playground-like object
        vault = Vault(registry=None, prompt_dir=prompt_dir)
        return _FallbackPlayground(host=host, port=port or 3000, vault=vault)


from typing import Generator


@pytest.fixture
def temp_project_dir() -> Generator[tuple[str, Path], None, None]:
    """Create a temporary directory with a Dakora project setup"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config file
        config: dict[str, object] = {
            "registry": "local",
            "prompt_dir": "./prompts",
            "logging": {"enabled": False},  # Disable logging for tests
        }

        config_path = Path(tmpdir) / "dakora.yaml"
        config_path.write_text(yaml.safe_dump(config))

        # Create prompts directory
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()
        # Create test templates
        test_templates: list[dict[str, object]] = [
            {
                "id": "simple-greeting",
                "version": "1.0.0",
                "description": "A simple greeting template",
                "template": "Hello {{ name }}!",
                "inputs": {"name": {"type": "string", "required": True}},
            },
            {
                "id": "complex-template",
                "version": "2.1.0",
                "description": "A complex template with multiple inputs",
                "template": """Welcome {{ name }}!
{% if age %}You are {{ age }} years old.{% endif %}
{% if hobbies %}Your hobbies: {{ hobbies | join(", ") }}{% endif %}
{{ message | default("Have a great day!") }}""",
                "inputs": {
                    "name": {"type": "string", "required": True},
                    "age": {"type": "number", "required": False},
                    "hobbies": {"type": "array<string>", "required": False},
                    "message": {
                        "type": "string",
                        "required": False,
                        "default": "Welcome to Dakora!",
                    },
                },
                "metadata": {"category": "greeting", "tags": ["test", "complex"]},
            },
            {
                "id": "error-template",
                "version": "1.0.0",
                "description": "Template that will cause render errors",
                "template": "Hello {{ undefined_var.missing_attr }}!",
                "inputs": {"name": {"type": "string", "required": True}},
            },
        ]

        for template in test_templates:
            template_path = prompts_dir / f"{template['id']}.yaml"
            template_path.write_text(yaml.safe_dump(template))

        yield tmpdir, config_path


@pytest.fixture
def test_vault(temp_project_dir: tuple[str, Path]) -> Generator[Vault, None, None]:
    """Create a Vault instance for testing"""
    tmpdir, config_path = temp_project_dir
    original_cwd = os.getcwd()
    os.chdir(tmpdir)

    try:
        vault = Vault(str(config_path))
        yield vault
    finally:
        os.chdir(original_cwd)


@contextmanager
def playground_server(vault: Vault, port: int = 0):
    """Context manager that starts a playground server and yields the base URL"""
    # Find available port if port=0
    if port == 0:
        import socket

        sock = socket.socket()
        sock.bind(("", 0))
        port = sock.getsockname()[1]
        sock.close()

    playground = create_playground(
        config_path=None,
        prompt_dir=vault.config["prompt_dir"],
        host="127.0.0.1",
        port=port,
    )

    # Start server in thread
    server_thread = threading.Thread(
        target=lambda: playground.run(debug=False), daemon=True
    )
    server_thread.start()

    # Wait for server to start
    base_url = f"http://127.0.0.1:{port}"
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/api/health", timeout=1)
            if response.status_code == 200:
                break
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            time.sleep(0.1)
    else:
        raise RuntimeError("Playground server failed to start")

    try:
        yield base_url
    finally:
        # Server will be stopped when thread exits
        pass


@pytest.fixture
def playground_url(test_vault: Vault) -> Generator[str, None, None]:
    """Fixture that provides a running playground server URL"""
    with playground_server(test_vault) as url:
        yield url
