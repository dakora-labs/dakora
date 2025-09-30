import typer, sys, time, subprocess, webbrowser, threading
from pathlib import Path
import yaml
from .vault import Vault
from .watcher import Watcher
from .playground import create_playground

app = typer.Typer(add_completion=False)

@app.command()
def init():
    root = Path.cwd()
    (root / "prompts").mkdir(exist_ok=True, parents=True)
    cfg = {
        "registry": "local",
        "prompt_dir": "./prompts",
        "logging": {"enabled": True, "backend": "sqlite", "db_path": "./dakora.db"},
    }
    (root / "dakora.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    example = {
        "id": "summarizer",
        "version": "1.0.0",
        "description": "Summarize text into exactly 3 bullets.",
        "template": "Summarize the following into exactly 3 bullet points:\n\n{{ input_text }}\n",
        "inputs": {"input_text": {"type": "string", "required": True}},
    }
    (root / "prompts" / "summarizer.yaml").write_text(yaml.safe_dump(example, sort_keys=False, allow_unicode=True), encoding="utf-8")
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
            x,y,z = [int(n) for n in ver.split(".")]
            if major: x,y,z = x+1,0,0
            elif minor: y,z = y+1,0
            else: z += 1
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
        typer.echo("❌ Web UI source not found. This may be a development installation issue.", err=True)
        return False

    # Check if playground is already built and recent
    if (playground_dir / "index.html").exists():
        ui_build_time = (playground_dir / "index.html").stat().st_mtime

        # Check if any source files are newer than the build
        newest_source_time = 0
        for source_file in web_dir.rglob("*"):
            if source_file.is_file() and not source_file.name.startswith('.'):
                newest_source_time = max(newest_source_time, source_file.stat().st_mtime)

        if ui_build_time > newest_source_time:
            typer.echo("✅ UI is already built and up to date")
            return True

    typer.echo("🔨 Building React UI...")

    try:
        # Check if node_modules exists
        if not (web_dir / "node_modules").exists():
            typer.echo("📦 Installing npm dependencies...")
            result = subprocess.run(
                ["npm", "install"],
                cwd=web_dir,
                check=True,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                typer.echo(f"❌ Failed to install dependencies: {result.stderr}", err=True)
                return False

        # Build the React app
        typer.echo("🏗️  Building production bundle...")
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=web_dir,
            check=True,
            capture_output=True,
            text=True
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
        return False


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
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically")
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
                typer.echo("⚠️  UI build failed, starting with fallback interface", err=True)

        # Create the server
        if prompt_dir:
            playground_server = create_playground(prompt_dir=prompt_dir, host=host, port=port)
        else:
            playground_server = create_playground(config_path=config, host=host, port=port)

        # Prepare browser opening
        if not no_browser:
            url = f"http://{host}:{port}"
            _open_browser_delayed(url)

        # Start the server
        if dev:
            typer.echo("🚀 Starting playground in development mode...")
        else:
            typer.echo("🎯 Starting Dakora Playground...")

        typer.echo("📍 Press Ctrl+C to stop the server")
        typer.echo("")

        playground_server.run(debug=dev)

    except FileNotFoundError as e:
        typer.echo(f"❌ Config file not found: {e}", err=True)
        typer.echo("💡 Run 'dakora init' to create a new project", err=True)
        raise typer.Exit(1)
    except KeyboardInterrupt:
        typer.echo("\n👋 Stopping playground server...")
        raise typer.Exit(0)
    except Exception as e:
        typer.echo(f"❌ Failed to start playground: {e}", err=True)
        raise typer.Exit(1)