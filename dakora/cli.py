import sys
import time
import subprocess
import webbrowser
import threading
import json
import asyncio
import typer
from pathlib import Path
import yaml
from dotenv import load_dotenv
from .vault import Vault
from .watcher import Watcher
from .playground import create_playground
from .exceptions import (
    ValidationError,
    RenderError,
    TemplateNotFound,
    APIKeyError,
    RateLimitError,
    ModelNotFoundError,
    LLMError,
)
from typing_extensions import Annotated
from typing import Optional
import os
import shutil

app = typer.Typer(add_completion=False)

load_dotenv()


@app.command()
def init():
    root = Path.cwd()
    (root / "prompts").mkdir(exist_ok=True, parents=True)
    cfg = {
        "registry": "local",
        "prompt_dir": "./prompts",
        "logging": {"enabled": True, "backend": "sqlite", "db_path": "./dakora.db"},
    }
    (root / "dakora.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8"
    )
    example = {
        "id": "summarizer",
        "version": "1.0.0",
        "description": "Summarize text into exactly 3 bullets.",
        "template": "Summarize the following into exactly 3 bullet points:\n\n{{ input_text }}\n",
        "inputs": {"input_text": {"type": "string", "required": True}},
    }
    (root / "prompts" / "summarizer.yaml").write_text(
        yaml.safe_dump(example, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    typer.echo("Initialized Dakora project.")


@app.command()
def list():
    v = Vault("dakora.yaml")
    for tid in v.list():
        typer.echo(tid)


@app.command()
def get(id: str):
    v = Vault("dakora.yaml")
    tmpl = v.get(id)
    # print raw template without rendering
    sys.stdout.write(tmpl.spec.template)


@app.command()
def bump(id: str, patch: bool = False, minor: bool = False, major: bool = False):
    # naive semantic bump: finds the file containing id and rewrites version
    prompt_dir = Path(yaml.safe_load(Path("dakora.yaml").read_text())["prompt_dir"])
    target = None
    for p in prompt_dir.rglob("*.y*ml"):
        data = yaml.safe_load(p.read_text()) or {}
        if data.get("id") == id:
            target = p
            ver = data.get("version", "0.0.1")
            x, y, z = [int(n) for n in ver.split(".")]
            if major:
                x, y, z = x + 1, 0, 0
            elif minor:
                y, z = y + 1, 0
            else:
                z += 1
            data["version"] = f"{x}.{y}.{z}"
            p.write_text(yaml.safe_dump(data, sort_keys=False))
            typer.echo(f"Bumped {id} -> {data['version']}")
            break
    if not target:
        raise SystemExit(f"Template '{id}' not found")


@app.command()
def watch():
    v = Vault("dakora.yaml")
    pd = Path(yaml.safe_load(Path("dakora.yaml").read_text())["prompt_dir"]).resolve()
    typer.echo(f"Watching {pd} for changes. Ctrl+C to stop.")
    w = Watcher(pd, on_change=v.invalidate_cache)
    w.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        w.stop()


@app.command()
def config(
    provider: Annotated[
        Optional[str],
        typer.Option(
            help="Supported providers: OpenAI, Anthropic, Google, Vertex, AWS, Recraft, XInference, NScale"
        ),
    ] = None,
):
    """
    Check which supported API Keys have been set.
    """
    supported_keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "VERTEX_API_KEY",
        "AWS_API_KEY",
        "RECRAFT_API_KEY",
        "XINFERENCE_API_KEY",
        "NSCALE_API_KEY",
    ]

    if provider:
        key = f"{provider.upper()}_API_KEY"
        if key not in supported_keys:
            typer.echo(f"Provider {provider} is not yet supported. ")
            typer.Exit(1)
        if os.getenv(key):
            typer.echo(f"✓ {key} found")
            typer.Exit(0)
        else:
            typer.echo(f"✗ {key} not set")
            sys.exit(1)

    else:
        for key in supported_keys:
            if os.getenv(key):
                typer.echo(f"✓ {key} found")
            else:
                typer.echo(f"✗ {key} not set")
    raise typer.Exit(0)


def _build_ui():
    """Build the React UI for the playground."""
    package_root = Path(__file__).parent.parent
    web_dir = package_root / "web"
    playground_dir = package_root / "playground"

    # Check if playground is already built (e.g., from PyPI package)
    if (playground_dir / "index.html").exists() and not web_dir.exists():
        typer.echo("✅ Using pre-built UI from package")
        return True

    # For development installs, check if we need to build
    if not web_dir.exists():
        typer.echo(
            "❌ Web UI source not found. This may be a development installation issue.",
            err=True,
        )
        return False

    # Check if playground is already built and recent
    if (playground_dir / "index.html").exists():
        ui_build_time = (playground_dir / "index.html").stat().st_mtime

        # Check if any source files are newer than the build
        newest_source_time = 0
        for source_file in web_dir.rglob("*"):
            if source_file.is_file() and not source_file.name.startswith("."):
                newest_source_time = max(
                    newest_source_time, source_file.stat().st_mtime
                )

        if ui_build_time > newest_source_time:
            typer.echo("✅ UI is already built and up to date")
            return True

    typer.echo("🔨 Building React UI...")

    try:
        npm_executable = _resolve_npm()
        if not npm_executable:
            typer.echo(
                "❌ npm not found in PATH. Set DAKORA_NPM_PATH or install Node.js + npm.",
                err=True,
            )
            _debug_path()
            return False

        # Show detected versions (best-effort, non-fatal)
        try:
            node_ver = subprocess.run(
                [
                    (
                        npm_executable.replace("npm", "node")
                        if "npm" in npm_executable
                        else "node"
                    ),
                    "--version",
                ],
                capture_output=True,
                text=True,
            )
            npm_ver = subprocess.run(
                [npm_executable, "--version"], capture_output=True, text=True
            )
            if node_ver.stdout.strip():
                typer.echo(
                    f"🧪 Node: {node_ver.stdout.strip()} | npm: {npm_ver.stdout.strip()}"
                )
        except Exception:
            pass

        # Install dependencies if needed
        if not (web_dir / "node_modules").exists():
            typer.echo("📦 Installing npm dependencies...")
            result = subprocess.run(
                [npm_executable, "install"],
                cwd=web_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                typer.echo(
                    f"❌ Failed to install dependencies: {result.stderr}", err=True
                )
                return False

        # Build the React app
        typer.echo("🏗️  Building production bundle...")
        result = subprocess.run(
            [npm_executable, "run", "build"],
            cwd=web_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            typer.echo("✅ UI built successfully!")
            return True
        else:
            typer.echo(f"❌ Build failed: {result.stderr}", err=True)
            return False

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Build failed: {e.stderr if e.stderr else str(e)}", err=True)
        return False
    except FileNotFoundError:
        typer.echo("❌ npm not found. Please install Node.js and npm.", err=True)
        _debug_path()
        return False


def _resolve_npm():
    """Attempt to find the npm executable on Windows/macOS/Linux.

    Order:
      1. Environment variable DAKORA_NPM_PATH (explicit override)
      2. shutil.which('npm')
      3. Windows specific: search for npm.cmd / npm.exe next to node.exe
      4. Fallback None
    """
    override = os.getenv("DAKORA_NPM_PATH")
    if override and Path(override).exists():
        return override

    # Standard lookup
    found = shutil.which("npm")
    if found:
        return found

    # Windows special cases
    if sys.platform.startswith("win"):
        node_path = shutil.which("node")
        if node_path:
            node_dir = Path(node_path).parent
            for cand in ["npm.cmd", "npm.exe", "npm"]:
                candidate = node_dir / cand
                if candidate.exists():
                    return str(candidate)
        # Common default install directory
        for base in [
            Path(os.environ.get("ProgramFiles", "")) / "nodejs",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "nodejs",
        ]:
            for cand in ["npm.cmd", "npm.exe"]:
                candidate = base / cand
                if candidate.exists():
                    return str(candidate)

    return None


def _debug_path():
    """Emit path diagnostics to help users troubleshoot missing npm."""
    try:
        typer.echo("🔍 PATH diagnostic:")
        typer.echo(
            f"PATH entries ({len(os.environ.get('PATH','').split(os.pathsep))}):"
        )
        for p in os.environ.get("PATH", "").split(os.pathsep):
            if p:
                typer.echo(f"  - {p}")
        typer.echo(
            "Set DAKORA_NPM_PATH to full path of npm (e.g. C:/Program Files/nodejs/npm.cmd)"
        )
    except Exception:
        pass


def _open_browser_delayed(url: str, delay: float = 2.0):
    """Open browser after a delay to ensure server is ready."""

    def open_browser():
        time.sleep(delay)
        try:
            webbrowser.open(url)
            typer.echo(f"🌐 Opened browser at {url}")
        except Exception as e:
            typer.echo(f"❌ Could not open browser: {e}", err=True)
            typer.echo(f"💡 Please manually open: {url}")

    thread = threading.Thread(target=open_browser, daemon=True)
    thread.start()


@app.command()
def playground(
    port: int = typer.Option(3000, help="Port to run playground on"),
    host: str = typer.Option("localhost", help="Host to bind to"),
    config: str = typer.Option("dakora.yaml", help="Config file path"),
    prompt_dir: str = typer.Option(None, help="Prompt directory (overrides config)"),
    dev: bool = typer.Option(False, "--dev", help="Development mode with auto-reload"),
    no_build: bool = typer.Option(False, "--no-build", help="Skip building the UI"),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Don't open browser automatically"
    ),
    demo: bool = typer.Option(
        False, "--demo", help="Demo mode with session isolation and terminal UI"
    ),
):
    """Launch the interactive playground web interface.

    This command will automatically:
    - Build the React UI (unless --no-build is specified)
    - Start the FastAPI server
    - Open your browser to the playground (unless --no-browser is specified)

    Similar to 'jupyter notebook', this provides a one-command experience.
    """
    try:
        # Build UI unless explicitly skipped
        if not no_build:
            if not _build_ui():
                typer.echo(
                    "⚠️  UI build failed, starting with fallback interface", err=True
                )

        # Create the server
        if demo:
            typer.echo("🎮 Starting in DEMO mode - session isolation enabled")
            playground_server = create_playground(host=host, port=port, demo_mode=True)
        elif prompt_dir:
            playground_server = create_playground(
                prompt_dir=prompt_dir, host=host, port=port
            )
        else:
            playground_server = create_playground(
                config_path=config, host=host, port=port
            )

        # Prepare browser opening
        if not no_browser:
            url = f"http://{host}:{port}"
            _open_browser_delayed(url)

        # Start the server
        if dev:
            typer.echo("🚀 Starting playground in development mode...")
        elif demo:
            typer.echo("🎮 Starting Dakora Playground in demo mode...")
        else:
            typer.echo("🎯 Starting Dakora Playground...")

        typer.echo("📍 Press Ctrl+C to stop the server")
        typer.echo("")

        playground_server.run(debug=dev)

    except FileNotFoundError as e:
        if demo:
            typer.echo(f"❌ Unexpected error in demo mode: {e}", err=True)
        else:
            typer.echo(f"❌ Config file not found: {e}", err=True)
            typer.echo("💡 Run 'dakora init' to create a new project", err=True)
        raise typer.Exit(1)
    except KeyboardInterrupt:
        typer.echo("\n👋 Stopping playground server...")
        raise typer.Exit(0)
    except Exception as e:
        typer.echo(f"❌ Failed to start playground: {e}", err=True)
        raise typer.Exit(1)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def run(
    ctx: typer.Context,
    template_id: str = typer.Argument(..., help="Template ID to execute"),
    model: str = typer.Option(
        ..., "--model", "-m", help="LLM model to use (e.g., 'gpt-4', 'claude-3-opus')"
    ),
    config: str = typer.Option("dakora.yaml", help="Config file path"),
    temperature: float = typer.Option(
        None, "--temperature", "-t", help="Sampling temperature (0.0-2.0)"
    ),
    max_tokens: int = typer.Option(
        None, "--max-tokens", help="Maximum tokens to generate"
    ),
    top_p: float = typer.Option(None, "--top-p", help="Nucleus sampling probability"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON result"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only output response text"
    ),
):
    """Execute a template against an LLM model.

    Template inputs should be provided as --<input-name> <value> flags.
    Any parameter not matching a template input will be passed to LiteLLM.

    Examples:
      dakora run summarizer --model gpt-4 --input-text "Article content..."
      dakora run summarizer --model gpt-5-nano --input-text "Text" --temperature 0.7
      dakora run chatbot --model claude-3-opus --message "Hello" --max-tokens 100
    """
    try:
        vault = Vault(config)
    except FileNotFoundError:
        typer.echo(f"❌ Config file not found: {config}", err=True)
        typer.echo("💡 Run 'dakora init' to create a new project", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Failed to load config: {e}", err=True)
        raise typer.Exit(1)

    try:
        template = vault.get(template_id)
    except TemplateNotFound:
        typer.echo(f"❌ Template '{template_id}' not found", err=True)
        typer.echo("💡 Run 'dakora list' to see available templates", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Failed to load template: {e}", err=True)
        raise typer.Exit(1)

    template_input_names = set(template.spec.inputs.keys())

    extra_args = ctx.args
    template_kwargs = {}
    llm_kwargs = {}

    if temperature is not None:
        llm_kwargs["temperature"] = temperature
    if max_tokens is not None:
        llm_kwargs["max_tokens"] = max_tokens
    if top_p is not None:
        llm_kwargs["top_p"] = top_p

    i = 0
    while i < len(extra_args):
        arg = extra_args[i]

        if arg.startswith("--") and i + 1 < len(extra_args):
            key = arg[2:].replace("-", "_")
            value = extra_args[i + 1]

            if key in template_input_names:
                template_kwargs[key] = value
            else:
                try:
                    parsed_value = json.loads(value)
                    llm_kwargs[key] = parsed_value
                except (json.JSONDecodeError, ValueError):
                    llm_kwargs[key] = value

            i += 2
        else:
            i += 1

    required_inputs = {
        name for name, spec in template.spec.inputs.items() if spec.required
    }
    missing_inputs = required_inputs - set(template_kwargs.keys())
    if missing_inputs:
        typer.echo(f"❌ Missing required inputs: {', '.join(missing_inputs)}", err=True)
        typer.echo(
            f"💡 Usage: dakora run {template_id} --model {model} "
            + " ".join(f"--{inp} <value>" for inp in sorted(template_input_names)),
            err=True,
        )
        raise typer.Exit(1)

    try:
        result = template.execute(model=model, **template_kwargs, **llm_kwargs)
    except ValidationError as e:
        typer.echo(f"❌ Validation error: {e}", err=True)
        raise typer.Exit(1)
    except RenderError as e:
        typer.echo(f"❌ Render error: {e}", err=True)
        raise typer.Exit(1)
    except APIKeyError as e:
        typer.echo(f"❌ API key error: {e}", err=True)
        typer.echo(
            "💡 Set the required environment variable (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY)",
            err=True,
        )
        raise typer.Exit(1)
    except RateLimitError as e:
        typer.echo(f"❌ Rate limit exceeded: {e}", err=True)
        raise typer.Exit(1)
    except ModelNotFoundError as e:
        typer.echo(f"❌ Model not found: {e}", err=True)
        raise typer.Exit(1)
    except LLMError as e:
        typer.echo(f"❌ LLM error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        raise typer.Exit(1)

    if json_output:
        output = {
            "output": result.output,
            "provider": result.provider,
            "model": result.model,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
        }
        typer.echo(json.dumps(output, indent=2))
    elif quiet:
        typer.echo(result.output)
    else:
        cost_str = f"${result.cost_usd:.4f}" if result.cost_usd > 0 else "$0.0000"
        latency_str = (
            f"{result.latency_ms:,} ms"
            if result.latency_ms < 10000
            else f"{result.latency_ms / 1000:.1f}s"
        )

        typer.echo("╭─────────────────────────────────────╮")
        typer.echo(f"│ Model: {result.model} ({result.provider})".ljust(38) + "│")
        typer.echo(f"│ Cost: {cost_str} USD".ljust(38) + "│")
        typer.echo(f"│ Latency: {latency_str}".ljust(38) + "│")
        typer.echo(
            f"│ Tokens: {result.tokens_in} → {result.tokens_out}".ljust(38) + "│"
        )
        typer.echo("╰─────────────────────────────────────╯")
        typer.echo()
        typer.echo(result.output)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def compare(
    ctx: typer.Context,
    template_id: str = typer.Argument(..., help="Template ID to execute"),
    models: str = typer.Option(
        ...,
        "--models",
        "-m",
        help="Comma-separated list of models (e.g., 'gpt-4,claude-3-opus')",
    ),
    config: str = typer.Option("dakora.yaml", help="Config file path"),
    temperature: float = typer.Option(
        None, "--temperature", "-t", help="Sampling temperature (0.0-2.0)"
    ),
    max_tokens: int = typer.Option(
        None, "--max-tokens", help="Maximum tokens to generate"
    ),
    top_p: float = typer.Option(None, "--top-p", help="Nucleus sampling probability"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON result"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full responses (not truncated)"
    ),
):
    """Compare template execution across multiple LLM models.

    Template inputs should be provided as --<input-name> <value> flags.
    Any parameter not matching a template input will be passed to LiteLLM.

    Examples:
      dakora compare summarizer --models gpt-4,claude-3-opus --input-text "Article..."
      dakora compare summarizer --models gpt-4,claude-3-opus,gemini-pro --input-text "Text" --temperature 0.7
      dakora compare chatbot --models gpt-4,claude-3-opus --message "Hello" --verbose
    """
    try:
        vault = Vault(config)
    except FileNotFoundError:
        typer.echo(f"❌ Config file not found: {config}", err=True)
        typer.echo("💡 Run 'dakora init' to create a new project", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Failed to load config: {e}", err=True)
        raise typer.Exit(1)

    try:
        template = vault.get(template_id)
    except TemplateNotFound:
        typer.echo(f"❌ Template '{template_id}' not found", err=True)
        typer.echo("💡 Run 'dakora list' to see available templates", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Failed to load template: {e}", err=True)
        raise typer.Exit(1)

    model_list = [m.strip() for m in models.split(",") if m.strip()]
    if not model_list:
        typer.echo("❌ No models specified", err=True)
        typer.echo(
            "💡 Provide comma-separated models: --models gpt-4,claude-3-opus", err=True
        )
        raise typer.Exit(1)

    template_input_names = set(template.spec.inputs.keys())

    extra_args = ctx.args
    template_kwargs = {}
    llm_kwargs = {}

    if temperature is not None:
        llm_kwargs["temperature"] = temperature
    if max_tokens is not None:
        llm_kwargs["max_tokens"] = max_tokens
    if top_p is not None:
        llm_kwargs["top_p"] = top_p

    i = 0
    while i < len(extra_args):
        arg = extra_args[i]

        if arg.startswith("--") and i + 1 < len(extra_args):
            key = arg[2:].replace("-", "_")
            value = extra_args[i + 1]

            if key in template_input_names:
                template_kwargs[key] = value
            else:
                try:
                    parsed_value = json.loads(value)
                    llm_kwargs[key] = parsed_value
                except (json.JSONDecodeError, ValueError):
                    llm_kwargs[key] = value

            i += 2
        else:
            i += 1

    required_inputs = {
        name for name, spec in template.spec.inputs.items() if spec.required
    }
    missing_inputs = required_inputs - set(template_kwargs.keys())
    if missing_inputs:
        typer.echo(f"❌ Missing required inputs: {', '.join(missing_inputs)}", err=True)
        typer.echo(
            f"💡 Usage: dakora compare {template_id} --models {models} "
            + " ".join(f"--{inp} <value>" for inp in sorted(template_input_names)),
            err=True,
        )
        raise typer.Exit(1)

    try:
        comparison = asyncio.run(
            template.compare(models=model_list, **template_kwargs, **llm_kwargs)
        )
    except ValidationError as e:
        typer.echo(f"❌ Validation error: {e}", err=True)
        raise typer.Exit(1)
    except RenderError as e:
        typer.echo(f"❌ Render error: {e}", err=True)
        raise typer.Exit(1)
    except APIKeyError as e:
        typer.echo(f"❌ API key error: {e}", err=True)
        typer.echo(
            "💡 Set the required environment variable (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY)",
            err=True,
        )
        raise typer.Exit(1)
    except RateLimitError as e:
        typer.echo(f"❌ Rate limit exceeded: {e}", err=True)
        raise typer.Exit(1)
    except ModelNotFoundError as e:
        typer.echo(f"❌ Model not found: {e}", err=True)
        raise typer.Exit(1)
    except LLMError as e:
        typer.echo(f"❌ LLM error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        raise typer.Exit(1)

    if json_output:
        output = {
            "results": [
                {
                    "model": r.model,
                    "provider": r.provider,
                    "output": r.output,
                    "tokens_in": r.tokens_in,
                    "tokens_out": r.tokens_out,
                    "cost_usd": r.cost_usd,
                    "latency_ms": r.latency_ms,
                    "error": r.error,
                }
                for r in comparison.results
            ],
            "total_cost_usd": comparison.total_cost_usd,
            "total_tokens_in": comparison.total_tokens_in,
            "total_tokens_out": comparison.total_tokens_out,
            "successful_count": comparison.successful_count,
            "failed_count": comparison.failed_count,
        }
        typer.echo(json.dumps(output, indent=2))
    elif verbose:
        for i, result in enumerate(comparison.results):
            if i > 0:
                typer.echo("\n" + "─" * 80 + "\n")

            if result.error:
                typer.echo(f"❌ {result.model} ({result.provider}) - FAILED")
                typer.echo(f"Error: {result.error}")
            else:
                cost_str = (
                    f"${result.cost_usd:.4f}" if result.cost_usd > 0 else "$0.0000"
                )
                latency_str = (
                    f"{result.latency_ms:,} ms"
                    if result.latency_ms < 10000
                    else f"{result.latency_ms / 1000:.1f}s"
                )

                typer.echo(f"✅ {result.model} ({result.provider})")
                typer.echo(
                    f"Cost: {cost_str} | Latency: {latency_str} | Tokens: {result.tokens_in} → {result.tokens_out}"
                )
                typer.echo()
                typer.echo(result.output)

        typer.echo("\n" + "─" * 80)
        typer.echo(f"\nTotal Cost: ${comparison.total_cost_usd:.4f}")
        typer.echo(
            f"Total Tokens: {comparison.total_tokens_in} → {comparison.total_tokens_out}"
        )
        typer.echo(
            f"Success Rate: {comparison.successful_count}/{len(comparison.results)}"
        )
    else:
        max_model_len = max(len(r.model) for r in comparison.results)
        max_model_len = max(max_model_len, 15)

        header_model = "Model".ljust(max_model_len)
        header_response = "Response (preview)".ljust(80)
        header_cost = "Cost".ljust(10)
        header_latency = "Latency".ljust(10)
        header_tokens = "Tokens".ljust(12)

        separator = "─" * (max_model_len + 80 + 10 + 10 + 12 + 8)

        typer.echo(separator)
        typer.echo(
            f" {header_model} │ {header_response} │ {header_cost} │ {header_latency} │ {header_tokens}"
        )
        typer.echo(separator)

        for result in comparison.results:
            model_col = result.model.ljust(max_model_len)

            if result.error:
                status = "❌"
                response_col = f"ERROR: {result.error[:74]}"
                response_col = response_col.ljust(80)
                cost_col = "N/A".ljust(10)
                latency_col = "N/A".ljust(10)
                tokens_col = "N/A".ljust(12)
            else:
                status = "✅"
                response_preview = result.output.replace("\n", " ").strip()
                if len(response_preview) > 77:
                    response_preview = response_preview[:77] + "..."
                response_col = response_preview.ljust(80)

                cost_str = (
                    f"${result.cost_usd:.4f}" if result.cost_usd > 0 else "$0.0000"
                )
                cost_col = cost_str.ljust(10)

                if result.latency_ms < 10000:
                    latency_str = f"{result.latency_ms:,}ms"
                else:
                    latency_str = f"{result.latency_ms / 1000:.1f}s"
                latency_col = latency_str.ljust(10)

                tokens_col = f"{result.tokens_in}→{result.tokens_out}".ljust(12)

            typer.echo(
                f"{status}{model_col} │ {response_col} │ {cost_col} │ {latency_col} │ {tokens_col}"
            )

        typer.echo(separator)
        typer.echo(
            f"\nTotal Cost: ${comparison.total_cost_usd:.4f} | Total Tokens: {comparison.total_tokens_in} → {comparison.total_tokens_out} | Success: {comparison.successful_count}/{len(comparison.results)}"
        )

        if verbose:
            typer.echo("\n💡 Use --verbose to see full responses")
        elif not json_output and comparison.successful_count < len(comparison.results):
            typer.echo("💡 Some models failed - use --verbose to see error details")
