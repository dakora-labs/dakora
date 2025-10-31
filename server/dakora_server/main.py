"""Dakora Platform Server"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from .api import (
    health,
    webhooks,
    projects, project_prompts,
    project_parts,
    me,
    api_keys,
    project_executions,
    execution_traces,
    project_optimizations,
    otlp_traces,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dakora Platform",
        description="AI Control Plane for Prompt Management",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # User context routes
    app.include_router(me.router)

    # Project-scoped routes
    app.include_router(projects.router)
    app.include_router(project_prompts.router)
    app.include_router(project_parts.router)
    app.include_router(api_keys.router)
    app.include_router(project_executions.router)
    app.include_router(execution_traces.router)
    app.include_router(project_optimizations.router)

    # OTLP ingestion
    app.include_router(otlp_traces.router)

    # System routes
    app.include_router(health.router)
    app.include_router(webhooks.router)

    studio_dir = Path(__file__).parent.parent.parent / "studio" / "dist"

    if studio_dir.exists() and (studio_dir / "index.html").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(studio_dir / "assets")),
            name="assets",
        )

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve index.html for all routes (SPA fallback)."""
            if full_path.startswith("api/"):
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="API endpoint not found")
            index_file = studio_dir / "index.html"
            return HTMLResponse(content=index_file.read_text(), status_code=200)
    else:
        @app.get("/", response_class=HTMLResponse)
        async def root():
            """Fallback when Studio UI not built."""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Dakora Platform</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        margin: 0; padding: 20px; background: #f5f5f5;
                    }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                    .content { background: white; padding: 20px; border-radius: 8px; }
                    .api-info { background: #e3f2fd; padding: 15px; border-radius: 4px; margin-top: 20px; }
                    code { background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Dakora Platform</h1>
                        <p>AI Control Plane for Prompt Management</p>
                    </div>
                    <div class="content">
                        <h2>API Endpoints</h2>
                        <ul>
                            <li><code>GET /api/templates</code> - List all templates</li>
                            <li><code>GET /api/templates/{id}</code> - Get template details</li>
                            <li><code>POST /api/templates</code> - Create template</li>
                            <li><code>PUT /api/templates/{id}</code> - Update template</li>
                            <li><code>POST /api/templates/{id}/render</code> - Render template</li>
                            <li><code>POST /api/templates/{id}/compare</code> - Compare LLM outputs</li>
                            <li><code>GET /api/health</code> - Health check</li>
                        </ul>

                        <div class="api-info">
                            <strong>API Testing</strong><br>
                            Try: <a href="/api/health">/api/health</a> |
                            <a href="/api/templates">/api/templates</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

    return app


app = create_app()