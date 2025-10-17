"""
Unit tests for Dakora Playground Server
"""

from fastapi.testclient import TestClient
from dakora.playground import PlaygroundServer, create_playground
from dakora.vault import Vault
from fastapi.routing import APIRoute


class TestPlaygroundServer:
    """Test PlaygroundServer class functionality"""

    def test_create_playground_with_config(self, temp_project_dir):
        """Test creating playground server with config file"""
        tmpdir, config_path = temp_project_dir
        playground = create_playground(config_path=str(config_path))

        assert isinstance(playground, PlaygroundServer)
        assert playground.host == "localhost"
        assert playground.port == 3000
        assert isinstance(playground.vault, Vault)

    def test_create_playground_with_prompt_dir(self, temp_project_dir):
        """Test creating playground server with prompt directory"""
        tmpdir, config_path = temp_project_dir
        prompts_dir = f"{tmpdir}/prompts"

        playground = create_playground(
            prompt_dir=prompts_dir, host="0.0.0.0", port=8080
        )

        assert playground.host == "0.0.0.0"
        assert playground.port == 8080
        assert playground.vault.config["prompt_dir"] == prompts_dir

    def test_playground_app_creation(self, test_vault):
        """Test that playground creates FastAPI app correctly"""
        playground = PlaygroundServer(test_vault)
        app = playground.app

        # Check that app has expected routes
        routes = [route.path for route in app.routes if isinstance(route, APIRoute)]
        expected_routes = [
            "/api/templates",
            "/api/templates/{template_id}",
            "/api/templates/{template_id}/render",
            "/api/examples",
            "/api/health",
            "/",
        ]

        for expected_route in expected_routes:
            # Check if any route matches (considering path parameters)
            assert any(
                expected_route.replace("{template_id}", "{path}") in route
                or expected_route == route
                for route in routes
            ), f"Missing route: {expected_route}"

    def test_example_templates_structure(self, test_vault):
        """Test that example templates have proper structure"""
        playground = PlaygroundServer(test_vault)
        examples = playground._get_example_templates()

        assert len(examples) >= 3

        for example in examples:
            # Check required fields
            assert example.id
            assert example.version
            assert example.template
            assert example.description

            # Check inputs structure
            for input_name, input_spec in example.inputs.items():
                assert hasattr(input_spec, "type")
                assert hasattr(input_spec, "required")
                assert input_spec.type in [
                    "string",
                    "number",
                    "boolean",
                    "array<string>",
                    "object",
                ]

            # Check metadata exists
            assert hasattr(example, "metadata")
            assert isinstance(example.metadata, dict)


class TestPlaygroundServerWithTestClient:
    """Test playground server using FastAPI TestClient"""

    def test_health_endpoint(self, test_vault):
        """Test health endpoint returns correct information"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert "templates_loaded" in data
            assert "vault_config" in data

    def test_templates_list_endpoint(self, test_vault):
        """Test templates listing endpoint"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            response = client.get("/api/templates")
            assert response.status_code == 200

            templates = response.json()
            assert isinstance(templates, list)
            assert "simple-greeting" in templates
            assert "complex-template" in templates

    def test_template_detail_endpoint(self, test_vault):
        """Test individual template detail endpoint"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            response = client.get("/api/templates/simple-greeting")
            assert response.status_code == 200

            template_data = response.json()
            assert template_data["id"] == "simple-greeting"
            assert template_data["version"] == "1.0.0"
            assert "inputs" in template_data
            assert "name" in template_data["inputs"]

    def test_template_render_endpoint(self, test_vault):
        """Test template rendering endpoint"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            response = client.post(
                "/api/templates/simple-greeting/render",
                json={"inputs": {"name": "TestClient"}},
            )
            assert response.status_code == 200

            render_data = response.json()
            assert render_data["rendered"] == "Hello TestClient!"
            assert render_data["inputs_used"]["name"] == "TestClient"

    def test_examples_endpoint(self, test_vault):
        """Test examples endpoint returns built-in templates"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            response = client.get("/api/examples")
            assert response.status_code == 200

            examples = response.json()
            assert isinstance(examples, list)
            assert len(examples) >= 3

            # Check first example structure
            example = examples[0]
            assert "id" in example
            assert "version" in example
            assert "description" in example
            assert "template" in example
            assert "inputs" in example

    def test_root_endpoint_returns_html(self, test_vault):
        """Test root endpoint returns HTML playground UI"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "Dakora Playground" in response.text

    def test_404_for_nonexistent_template(self, test_vault):
        """Test 404 response for non-existent template"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            response = client.get("/api/templates/nonexistent")
            assert response.status_code == 404

            response = client.post(
                "/api/templates/nonexistent/render", json={"inputs": {"test": "value"}}
            )
            assert response.status_code == 404

    def test_validation_errors(self, test_vault):
        """Test proper validation error responses"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            # Missing required input
            response = client.post(
                "/api/templates/simple-greeting/render", json={"inputs": {}}
            )
            assert response.status_code == 400
            assert "validation error" in response.json()["detail"].lower()

    def test_render_errors(self, test_vault):
        """Test proper render error responses"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            # Template with undefined variable should cause render error
            response = client.post(
                "/api/templates/error-template/render",
                json={"inputs": {"name": "test"}},
            )
            assert response.status_code == 400
            assert "render error" in response.json()["detail"].lower()


class TestPlaygroundServerEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_vault(self):
        """Test playground server with vault containing no templates"""
        import tempfile
        import os
        from pathlib import Path
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config with empty prompts directory
            config = {
                "registry": "local",
                "prompt_dir": "./prompts",
                "logging": {"enabled": False},
            }

            config_path = Path(tmpdir) / "dakora.yaml"
            config_path.write_text(yaml.safe_dump(config))

            # Create empty prompts directory
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir()

            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                vault = Vault(str(config_path))
                playground = PlaygroundServer(vault)

                with TestClient(playground.app) as client:
                    # Health should still work
                    response = client.get("/api/health")
                    assert response.status_code == 200
                    assert response.json()["templates_loaded"] == 0

                    # Templates list should return empty list
                    response = client.get("/api/templates")
                    assert response.status_code == 200
                    assert response.json() == []

                    # Examples should still work
                    response = client.get("/api/examples")
                    assert response.status_code == 200
                    assert len(response.json()) >= 3

            finally:
                os.chdir(original_cwd)

    def test_malformed_request_data(self, test_vault):
        """Test handling of malformed request data"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            # Test with non-JSON content type
            response = client.post(
                "/api/templates/simple-greeting/render",
                content="not json",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 422

            # Test with wrong content type
            response = client.post(
                "/api/templates/simple-greeting/render",
                content='{"inputs": {"name": "test"}}',
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 422

    def test_cors_and_security_headers(self, test_vault):
        """Test that appropriate security headers are set"""
        playground = PlaygroundServer(test_vault)

        with TestClient(playground.app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            # FastAPI should set appropriate JSON content type
            assert "application/json" in response.headers.get("content-type", "")

    def test_concurrent_requests(self, test_vault):
        """Test that server handles concurrent requests properly"""
        import threading

        playground = PlaygroundServer(test_vault)
        results = []
        errors = []

        def make_request():
            try:
                with TestClient(playground.app) as client:
                    response = client.post(
                        "/api/templates/simple-greeting/render",
                        json={"inputs": {"name": "ConcurrentTest"}},
                    )
                    results.append(response.status_code == 200)
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads to test concurrent access
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(results), "Some requests failed"
        assert len(results) == 10
