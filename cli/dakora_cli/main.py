"""Dakora Platform CLI"""

import os
import subprocess
from pathlib import Path
import typer

app = typer.Typer(
    name="dakora",
    help="Dakora Platform CLI - AI Control Plane for Prompt Management",
    no_args_is_help=True,
)


def get_docker_compose_path() -> Path:
    """Get the path to docker-compose.yml - check multiple locations"""
    # First check if we're in a user project (has local docker/)
    local_compose = Path.cwd() / "docker" / "docker-compose.yml"
    if local_compose.exists():
        return local_compose

    # Check if we're in the monorepo (for development)
    monorepo_compose = Path.cwd() / "docker" / "docker-compose.yml"
    if monorepo_compose.exists():
        return monorepo_compose

    # Try parent directory (in case we're in a subdirectory)
    parent_compose = Path.cwd().parent / "docker" / "docker-compose.yml"
    if parent_compose.exists():
        return parent_compose

    # Use embedded template from package
    try:
        from importlib.resources import files
        template_path = files("dakora_cli") / "templates" / "docker-compose.yml"
        if template_path.exists():
            # Copy to temporary location
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "dakora"
            temp_dir.mkdir(exist_ok=True)
            temp_compose = temp_dir / "docker-compose.yml"
            temp_compose.write_text(template_path.read_text())
            return temp_compose
    except:
        pass

    return None


@app.command()
def start(
    detach: bool = typer.Option(True, "--detach/--no-detach", "-d", help="Run in background"),
):
    """Start Dakora platform (docker compose up)"""
    compose_file = get_docker_compose_path()

    if not compose_file:
        typer.secho("Error: Could not find docker-compose.yml", fg=typer.colors.RED, bold=True)
        typer.echo("")
        typer.echo("Options:")
        typer.echo("  1. Run from the dakora monorepo root")
        typer.echo("  2. Run 'dakora init' to create a new project")
        raise typer.Exit(1)

    typer.echo(f"Starting Dakora platform using {compose_file}...")

    cmd = ["docker", "compose", "-f", str(compose_file), "up"]
    if detach:
        cmd.append("-d")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        typer.secho("Failed to start Dakora platform", fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)

    if detach:
        typer.echo("")
        typer.secho("✓ Dakora platform running", fg=typer.colors.GREEN, bold=True)
        typer.echo("  - API: http://localhost:54321")
        typer.echo("  - Studio: http://localhost:3000")
        typer.echo("")
        typer.echo("To stop: dakora stop")


@app.command()
def stop():
    """Stop Dakora platform (docker compose down)"""
    compose_file = get_docker_compose_path()

    if not compose_file.exists():
        typer.secho(f"Error: {compose_file} not found", fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)

    typer.echo("Stopping Dakora platform...")

    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down"],
            check=True
        )
        typer.secho("✓ Dakora platform stopped", fg=typer.colors.GREEN, bold=True)
    except subprocess.CalledProcessError:
        typer.secho("Failed to stop Dakora platform", fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)


@app.command()
def init():
    """Initialize new Dakora project with example templates"""
    cwd = Path.cwd()

    prompts_dir = cwd / "prompts"
    docker_dir = cwd / "docker"
    env_file = cwd / ".env"

    prompts_dir.mkdir(exist_ok=True)
    docker_dir.mkdir(exist_ok=True)

    # Create .env file
    if not env_file.exists():
        env_file.write_text(
            "MODE=local\n"
            "API_PORT=54321\n"
            "STUDIO_PORT=3000\n"
        )

    # Copy docker-compose.yml
    compose_file = docker_dir / "docker-compose.yml"
    if not compose_file.exists():
        from importlib.resources import files
        import shutil

        template_path = files("dakora_cli") / "templates" / "docker-compose.yml"
        if template_path.exists():
            shutil.copy(template_path, compose_file)
        else:
            typer.secho(
                "Warning: docker-compose.yml template not found.",
                fg=typer.colors.YELLOW
            )

    # Create example template
    example_template = prompts_dir / "greeting.yaml"
    if not example_template.exists():
        example_template.write_text("""id: greeting
version: 1.0.0
description: A simple greeting template
template: |
  Hello {{ name }}!
  {% if message %}{{ message }}{% endif %}
inputs:
  name:
    type: string
    required: true
  message:
    type: string
    required: false
    default: "Welcome to Dakora!"
metadata:
  tags: ["example", "greeting"]
""")

    typer.secho("✓ Initialized Dakora project", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  - Prompts: {prompts_dir}")
    typer.echo(f"  - Docker: {docker_dir}")
    typer.echo(f"  - Example template: greeting.yaml")
    typer.echo("")
    typer.echo("Next: dakora start")


@app.command()
def delete(
    template_id: str = typer.Argument(..., help="Template ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    api_url: str = typer.Option(
        os.getenv("DAKORA_URL", "http://localhost:54321"),
        "--api-url",
        help="Dakora API URL"
    ),
):
    """Delete a template from the registry
    
    This will permanently delete the template from the prompt registry.
    Use with caution as this action cannot be undone (unless versioning is enabled).
    """
    # Confirmation prompt
    if not yes:
        typer.echo(f"Template: {template_id}")
        typer.echo(f"API: {api_url}")
        typer.echo("")
        confirm = typer.confirm(
            f"Are you sure you want to delete '{template_id}'?",
            default=False
        )
        if not confirm:
            typer.echo("Deletion cancelled")
            raise typer.Exit(0)
    
    # Make DELETE request
    import httpx
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.delete(
                f"{api_url}/api/templates/{template_id}",
                headers={"Accept": "application/json"}
            )
            
            if response.status_code == 204:
                typer.secho(f"✓ Template '{template_id}' deleted successfully", fg=typer.colors.GREEN, bold=True)
            elif response.status_code == 404:
                typer.secho(f"Error: Template '{template_id}' not found", fg=typer.colors.RED, bold=True)
                raise typer.Exit(1)
            else:
                # Try to parse error message
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}"
                
                typer.secho(f"Error: Failed to delete template - {error_msg}", fg=typer.colors.RED, bold=True)
                raise typer.Exit(1)
                
    except httpx.ConnectError:
        typer.secho(f"Error: Cannot connect to Dakora API at {api_url}", fg=typer.colors.RED, bold=True)
        typer.echo("Make sure the Dakora server is running (try: dakora start)")
        raise typer.Exit(1)
    except httpx.TimeoutException:
        typer.secho("Error: Request timed out", fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: {str(e)}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)


@app.command()
def link(url: str = typer.Argument(..., help="Cloud Dakora instance URL")):
    """Link to cloud Dakora instance"""
    api_key = typer.prompt("Enter API key", hide_input=True)

    env_file = Path.cwd() / ".env"

    env_content = ""
    if env_file.exists():
        env_content = env_file.read_text()

    if "DAKORA_URL" not in env_content:
        env_content += f"\nDAKORA_URL={url}\n"
    if "DAKORA_API_KEY" not in env_content:
        env_content += f"DAKORA_API_KEY={api_key}\n"

    env_file.write_text(env_content)

    typer.secho(f"✓ Linked to {url}", fg=typer.colors.GREEN, bold=True)
    typer.echo("Credentials saved to .env")


@app.command()
def version():
    """Show Dakora CLI version"""
    from . import __version__
    typer.echo(f"Dakora CLI v{__version__}")


if __name__ == "__main__":
    app()