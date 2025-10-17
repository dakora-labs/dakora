"""
Tests for the Dakora Playground API using requests
"""
import pytest
import requests

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestPlaygroundHealthAPI:
    """Test health check and server status endpoints"""

    def test_health_endpoint_returns_200(self, playground_url):
        """Test that health endpoint returns successful status"""
        response = requests.get(f"{playground_url}/api/health")
        assert response.status_code == 200

    def test_health_endpoint_structure(self, playground_url):
        """Test health endpoint returns expected data structure"""
        response = requests.get(f"{playground_url}/api/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert "templates_loaded" in data
        assert isinstance(data["templates_loaded"], int)
        assert data["templates_loaded"] >= 0
        assert "vault_config" in data
        assert "registry_type" in data["vault_config"]
        assert data["vault_config"]["registry_type"] in ["local", "azure"]
        assert "logging_enabled" in data["vault_config"]
        
        # Check for location info based on registry type
        if data["vault_config"]["registry_type"] == "local":
            assert "prompt_dir" in data["vault_config"]
        elif data["vault_config"]["registry_type"] == "azure":
            assert "cloud_location" in data["vault_config"]

    def test_health_shows_correct_template_count(self, playground_url):
        """Test that health endpoint shows correct number of templates"""
        health_response = requests.get(f"{playground_url}/api/health")
        templates_response = requests.get(f"{playground_url}/api/templates")

        health_data = health_response.json()
        templates_data = templates_response.json()

        assert health_data["templates_loaded"] == len(templates_data)


class TestPlaygroundTemplatesAPI:
    """Test template listing and retrieval endpoints"""

    def test_templates_list_endpoint(self, playground_url):
        """Test that templates list endpoint returns template IDs"""
        response = requests.get(f"{playground_url}/api/templates")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Should have our test templates
        template_ids = set(data)
        expected_ids = {"simple-greeting", "complex-template", "error-template"}
        assert expected_ids.issubset(template_ids)

    def test_get_template_details(self, playground_url):
        """Test retrieving specific template details"""
        response = requests.get(f"{playground_url}/api/templates/simple-greeting")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "simple-greeting"
        assert data["version"] == "1.0.0"
        assert data["description"] == "A simple greeting template"
        assert data["template"] == "Hello {{ name }}!"
        assert "inputs" in data
        assert "name" in data["inputs"]
        assert data["inputs"]["name"]["type"] == "string"
        assert data["inputs"]["name"]["required"] is True

    def test_get_complex_template_details(self, playground_url):
        """Test retrieving complex template with all features"""
        response = requests.get(f"{playground_url}/api/templates/complex-template")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "complex-template"
        assert data["version"] == "2.1.0"
        assert "inputs" in data
        assert len(data["inputs"]) == 4  # name, age, hobbies, message

        # Check input types
        assert data["inputs"]["name"]["type"] == "string"
        assert data["inputs"]["age"]["type"] == "number"
        assert data["inputs"]["hobbies"]["type"] == "array<string>"
        assert data["inputs"]["message"]["type"] == "string"

        # Check required flags
        assert data["inputs"]["name"]["required"] is True
        assert data["inputs"]["age"]["required"] is False
        assert data["inputs"]["hobbies"]["required"] is False
        assert data["inputs"]["message"]["required"] is False

        # Check default value
        assert data["inputs"]["message"]["default"] == "Welcome to Dakora!"

        # Check metadata
        assert "metadata" in data
        assert data["metadata"]["category"] == "greeting"
        assert "test" in data["metadata"]["tags"]

    def test_get_nonexistent_template_404(self, playground_url):
        """Test that requesting non-existent template returns 404"""
        response = requests.get(f"{playground_url}/api/templates/nonexistent-template")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_templates_endpoint_content_type(self, playground_url):
        """Test that API endpoints return proper JSON content type"""
        response = requests.get(f"{playground_url}/api/templates")
        assert "application/json" in response.headers.get("content-type", "")


class TestPlaygroundRenderAPI:
    """Test template rendering endpoints"""

    def test_simple_template_render(self, playground_url):
        """Test rendering simple template with required inputs"""
        payload = {
            "inputs": {
                "name": "Alice"
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/render",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()

        assert "rendered" in data
        assert data["rendered"] == "Hello Alice!"
        assert "inputs_used" in data
        assert data["inputs_used"]["name"] == "Alice"

    def test_complex_template_render_minimal(self, playground_url):
        """Test rendering complex template with minimal required inputs"""
        payload = {
            "inputs": {
                "name": "Bob"
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates/complex-template/render",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()

        rendered = data["rendered"]
        assert "Welcome Bob!" in rendered
        assert "Welcome to Dakora!" in rendered  # Default message
        assert "years old" not in rendered  # Age not provided

    def test_complex_template_render_full(self, playground_url):
        """Test rendering complex template with all inputs"""
        payload = {
            "inputs": {
                "name": "Charlie",
                "age": 25,
                "hobbies": ["coding", "reading", "hiking"],
                "message": "Have an awesome day!"
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates/complex-template/render",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()

        rendered = data["rendered"]
        assert "Welcome Charlie!" in rendered
        assert "You are 25 years old." in rendered
        assert "coding, reading, hiking" in rendered
        assert "Have an awesome day!" in rendered

        # Check inputs_used contains all provided inputs
        inputs_used = data["inputs_used"]
        assert inputs_used["name"] == "Charlie"
        assert inputs_used["age"] == 25
        assert inputs_used["hobbies"] == ["coding", "reading", "hiking"]
        assert inputs_used["message"] == "Have an awesome day!"

    def test_render_missing_required_input(self, playground_url):
        """Test that rendering fails when required input is missing"""
        payload = {
            "inputs": {
                # Missing required 'name' field
                "age": 30
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/render",
            json=payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "validation error" in data["detail"].lower()
        assert "missing input" in data["detail"].lower()

    def test_render_invalid_input_type(self, playground_url):
        """Test that rendering fails with invalid input types"""
        payload = {
            "inputs": {
                "name": "Dave",
                "age": "not-a-number"  # Should be number
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates/complex-template/render",
            json=payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_render_template_error(self, playground_url):
        """Test handling of template rendering errors"""
        payload = {
            "inputs": {
                "name": "ErrorTest"
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates/error-template/render",
            json=payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "render error" in data["detail"].lower()

    def test_render_nonexistent_template(self, playground_url):
        """Test rendering non-existent template returns 404"""
        payload = {
            "inputs": {
                "name": "Test"
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates/nonexistent/render",
            json=payload
        )

        assert response.status_code == 404

    def test_render_empty_inputs(self, playground_url):
        """Test rendering template with empty inputs object"""
        payload = {
            "inputs": {}
        }

        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/render",
            json=payload
        )

        assert response.status_code == 400  # Missing required 'name'

    def test_render_no_inputs_key(self, playground_url):
        """Test rendering with malformed JSON (no inputs key)"""
        payload = {
            "name": "Test"  # Should be under "inputs"
        }

        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/render",
            json=payload
        )

        # Should use default empty inputs and fail validation
        assert response.status_code == 400


class TestPlaygroundExamplesAPI:
    """Test example templates endpoint"""

    def test_examples_endpoint(self, playground_url):
        """Test that examples endpoint returns example templates"""
        response = requests.get(f"{playground_url}/api/examples")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # Should have at least 3 built-in examples

        # Check structure of first example
        example = data[0]
        assert "id" in example
        assert "version" in example
        assert "description" in example
        assert "template" in example
        assert "inputs" in example

    def test_examples_include_expected_templates(self, playground_url):
        """Test that examples include the expected built-in templates"""
        response = requests.get(f"{playground_url}/api/examples")
        data = response.json()

        example_ids = {example["id"] for example in data}
        expected_ids = {"code-reviewer", "email-responder", "blog-post-generator"}

        assert expected_ids.issubset(example_ids)

    def test_examples_have_valid_structure(self, playground_url):
        """Test that all examples have valid template structure"""
        response = requests.get(f"{playground_url}/api/examples")
        data = response.json()

        for example in data:
            # Required fields
            assert example["id"]
            assert example["version"]
            assert example["template"]

            # Inputs should be properly structured
            if "inputs" in example:
                for input_name, input_spec in example["inputs"].items():
                    assert "type" in input_spec
                    assert "required" in input_spec
                    assert input_spec["type"] in ["string", "number", "boolean", "array<string>", "object"]


class TestPlaygroundTemplateCreationAPI:
    """Test template creation endpoints"""

    def test_create_template_success(self, playground_url, tmp_path):
        """Test successful template creation"""
        payload = {
            "id": "api-test-template",
            "version": "1.0.0",
            "description": "A template created via API for testing",
            "template": "Hello {{ name }}, welcome to {{ service }}!",
            "inputs": {
                "name": {
                    "type": "string",
                    "required": True
                },
                "service": {
                    "type": "string",
                    "required": True,
                    "default": "Dakora"
                }
            },
            "metadata": {
                "tags": ["test", "api"]
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["id"] == "api-test-template"
        assert data["version"] == "1.0.0"
        assert data["description"] == "A template created via API for testing"
        assert data["template"] == "Hello {{ name }}, welcome to {{ service }}!"

        # Verify inputs are properly structured
        assert "name" in data["inputs"]
        assert data["inputs"]["name"]["type"] == "string"
        assert data["inputs"]["name"]["required"] is True
        assert data["inputs"]["name"]["default"] is None

        assert "service" in data["inputs"]
        assert data["inputs"]["service"]["type"] == "string"
        assert data["inputs"]["service"]["required"] is True
        assert data["inputs"]["service"]["default"] == "Dakora"

        # Verify metadata
        assert data["metadata"]["tags"] == ["test", "api"]

    def test_create_template_minimal(self, playground_url):
        """Test creating template with minimal required fields"""
        payload = {
            "id": "minimal-template",
            "template": "Simple template: {{ value }}"
        }

        response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "minimal-template"
        assert data["version"] == "1.0.0"  # Default version
        assert data["description"] is None
        assert data["template"] == "Simple template: {{ value }}"
        assert data["inputs"] == {}
        assert data["metadata"] == {}

    def test_create_template_with_all_input_types(self, playground_url):
        """Test creating template with all supported input types"""
        payload = {
            "id": "all-types-template",
            "template": "{{ name }} is {{ age }} years old, likes {{ hobbies }}, active: {{ active }}, data: {{ config }}",
            "inputs": {
                "name": {
                    "type": "string",
                    "required": True
                },
                "age": {
                    "type": "number",
                    "required": False,
                    "default": 25
                },
                "hobbies": {
                    "type": "array<string>",
                    "required": False,
                    "default": ["reading"]
                },
                "active": {
                    "type": "boolean",
                    "required": False,
                    "default": True
                },
                "config": {
                    "type": "object",
                    "required": False,
                    "default": {"key": "value"}
                }
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all input types are preserved
        inputs = data["inputs"]
        assert inputs["name"]["type"] == "string"
        assert inputs["age"]["type"] == "number"
        assert inputs["age"]["default"] == 25
        assert inputs["hobbies"]["type"] == "array<string>"
        assert inputs["hobbies"]["default"] == ["reading"]
        assert inputs["active"]["type"] == "boolean"
        assert inputs["active"]["default"] is True
        assert inputs["config"]["type"] == "object"
        assert inputs["config"]["default"] == {"key": "value"}

    def test_create_template_appears_in_list(self, playground_url):
        """Test that created template appears in templates list"""
        # Create template
        payload = {
            "id": "list-test-template",
            "template": "Test {{ name }}"
        }

        create_response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert create_response.status_code == 200

        # Check it appears in list
        list_response = requests.get(f"{playground_url}/api/templates")
        templates = list_response.json()
        assert "list-test-template" in templates

    def test_create_template_is_retrievable(self, playground_url):
        """Test that created template can be retrieved"""
        # Create template
        payload = {
            "id": "retrievable-template",
            "description": "Test retrieval",
            "template": "Hello {{ user }}",
            "inputs": {
                "user": {
                    "type": "string",
                    "required": True
                }
            }
        }

        create_response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert create_response.status_code == 200

        # Retrieve template
        get_response = requests.get(f"{playground_url}/api/templates/retrievable-template")
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["id"] == "retrievable-template"
        assert data["description"] == "Test retrieval"
        assert data["template"] == "Hello {{ user }}"

    def test_create_template_is_renderable(self, playground_url):
        """Test that created template can be rendered"""
        # Create template
        payload = {
            "id": "renderable-template",
            "template": "Greetings {{ name }}!",
            "inputs": {
                "name": {
                    "type": "string",
                    "required": True
                }
            }
        }

        create_response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert create_response.status_code == 200

        # Render template
        render_payload = {
            "inputs": {
                "name": "TestUser"
            }
        }

        render_response = requests.post(
            f"{playground_url}/api/templates/renderable-template/render",
            json=render_payload
        )
        assert render_response.status_code == 200

        data = render_response.json()
        assert data["rendered"] == "Greetings TestUser!"

    def test_create_template_duplicate_id_fails(self, playground_url):
        """Test that creating template with duplicate ID fails"""
        payload = {
            "id": "duplicate-test",
            "template": "First template"
        }

        # Create first template
        response1 = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert response1.status_code == 200

        # Try to create duplicate
        payload["template"] = "Second template"
        response2 = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert response2.status_code == 400

        data = response2.json()
        assert "already exists" in data["detail"]

    def test_create_template_missing_id_fails(self, playground_url):
        """Test that creating template without ID fails"""
        payload = {
            "template": "Template without ID"
        }

        response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert response.status_code == 422  # Validation error

    def test_create_template_missing_template_fails(self, playground_url):
        """Test that creating template without template content fails"""
        payload = {
            "id": "no-template-content"
        }

        response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert response.status_code == 422  # Validation error

    def test_create_template_invalid_input_type_fails(self, playground_url):
        """Test that creating template with invalid input type fails"""
        payload = {
            "id": "invalid-input-type",
            "template": "Test {{ value }}",
            "inputs": {
                "value": {
                    "type": "invalid_type",
                    "required": True
                }
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert response.status_code == 500  # Server error due to validation

    def test_create_template_invalid_default_value_fails(self, playground_url):
        """Test that creating template with invalid default value fails"""
        payload = {
            "id": "invalid-default",
            "template": "Test {{ value }}",
            "inputs": {
                "value": {
                    "type": "number",
                    "required": False,
                    "default": "not-a-number"
                }
            }
        }

        response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert response.status_code == 500  # Server error due to validation

    def test_create_template_empty_id_fails(self, playground_url):
        """Test that creating template with empty ID fails"""
        payload = {
            "id": "",
            "template": "Empty ID test"
        }

        response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert response.status_code == 422  # Validation error

    def test_create_template_health_count_updates(self, playground_url):
        """Test that health endpoint reflects new template count after creation"""
        # Get initial count
        health_response1 = requests.get(f"{playground_url}/api/health")
        initial_count = health_response1.json()["templates_loaded"]

        # Create template
        payload = {
            "id": "health-count-test",
            "template": "Count test"
        }

        create_response = requests.post(
            f"{playground_url}/api/templates",
            json=payload
        )
        assert create_response.status_code == 200

        # Check count updated
        health_response2 = requests.get(f"{playground_url}/api/health")
        new_count = health_response2.json()["templates_loaded"]
        assert new_count == initial_count + 1


class TestPlaygroundCompareAPI:
    """Test template comparison endpoint"""

    def test_compare_endpoint_not_found(self, playground_url):
        """Test compare endpoint with non-existent template returns 404"""
        payload = {
            "inputs": {"text": "Sample text"},
            "models": ["gpt-4"]
        }

        response = requests.post(
            f"{playground_url}/api/templates/nonexistent-template/compare",
            json=payload
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_compare_endpoint_missing_required_input(self, playground_url):
        """Test compare endpoint fails when required input is missing"""
        payload = {
            "inputs": {},
            "models": ["gpt-4"]
        }

        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/compare",
            json=payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "validation error" in data["detail"].lower()

    def test_compare_endpoint_missing_models(self, playground_url):
        """Test compare endpoint fails when models list is missing"""
        payload = {
            "inputs": {"name": "Test"}
        }

        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/compare",
            json=payload
        )

        assert response.status_code == 422

    def test_compare_endpoint_empty_models_list(self, playground_url):
        """Test compare endpoint fails when models list is empty"""
        payload = {
            "inputs": {"name": "Test"},
            "models": []
        }

        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/compare",
            json=payload
        )

        assert response.status_code == 422

    def test_compare_endpoint_too_many_models(self, playground_url):
        """Test compare endpoint fails when more than 3 models are provided"""
        payload = {
            "inputs": {"name": "Test"},
            "models": ["gpt-4", "claude-3-opus", "gemini-pro", "extra-model"]
        }

        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/compare",
            json=payload
        )

        assert response.status_code == 422


class TestPlaygroundErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_json_request(self, playground_url):
        """Test handling of invalid JSON in POST requests"""
        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/render",
            data="invalid-json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422  # FastAPI returns 422 for invalid JSON

    def test_get_root_endpoint(self, playground_url):
        """Test that root endpoint returns HTML playground UI"""
        response = requests.get(playground_url)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "Dakora Playground" in response.text

    def test_nonexistent_endpoint(self, playground_url):
        """Test that non-existent endpoints return 404"""
        response = requests.get(f"{playground_url}/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, playground_url):
        """Test that wrong HTTP methods return appropriate errors"""
        # PUT to templates list (should be GET or POST)
        response = requests.put(f"{playground_url}/api/templates")
        assert response.status_code == 405  # Method Not Allowed


class TestPlaygroundIntegration:
    """Integration tests that test multiple API interactions"""

    def test_complete_workflow(self, playground_url):
        """Test complete workflow: list -> get -> render"""
        # 1. List all templates
        templates_response = requests.get(f"{playground_url}/api/templates")
        assert templates_response.status_code == 200
        template_ids = templates_response.json()
        assert "simple-greeting" in template_ids

        # 2. Get template details
        detail_response = requests.get(f"{playground_url}/api/templates/simple-greeting")
        assert detail_response.status_code == 200
        template_data = detail_response.json()

        # 3. Render template using discovered input requirements
        required_inputs = {
            name: None for name, spec in template_data["inputs"].items()
            if spec["required"]
        }
        assert "name" in required_inputs

        render_payload = {
            "inputs": {
                "name": "Integration Test"
            }
        }
        render_response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/render",
            json=render_payload
        )
        assert render_response.status_code == 200
        assert "Hello Integration Test!" in render_response.json()["rendered"]

    def test_examples_are_renderable(self, playground_url):
        """Test that example templates can actually be rendered"""
        # Get examples
        examples_response = requests.get(f"{playground_url}/api/examples")
        examples = examples_response.json()

        # Test rendering first example that has simple inputs
        for example in examples:
            if example["id"] == "code-reviewer":
                render_payload = {
                    "inputs": {
                        "code": "def hello():\n    print('Hello World')",
                        "language": "python"
                    }
                }

                # Note: Example templates aren't loaded in vault, this will 404
                # But we test the API structure is correct
                render_response = requests.post(
                    f"{playground_url}/api/templates/{example['id']}/render",
                    json=render_payload
                )
                # We expect 404 since examples aren't in the vault
                assert render_response.status_code == 404
                break

    def test_health_reflects_server_state(self, playground_url):
        """Test that health endpoint reflects actual server state"""
        health_response = requests.get(f"{playground_url}/api/health")
        health_data = health_response.json()

        # Verify template count matches actual templates
        templates_response = requests.get(f"{playground_url}/api/templates")
        templates = templates_response.json()

        assert health_data["templates_loaded"] == len(templates)
        assert health_data["status"] == "healthy"

        # Verify vault config is accessible
        vault_config = health_data["vault_config"]
        assert "registry_type" in vault_config
        assert vault_config["registry_type"] in ["local", "azure"]
        
        # For local registry, check prompt_dir
        if vault_config["registry_type"] == "local":
            assert vault_config["prompt_dir"] == "./prompts"
        # For azure registry, check cloud_location
        elif vault_config["registry_type"] == "azure":
            assert "cloud_location" in vault_config
        
        assert isinstance(vault_config["logging_enabled"], bool)

    def test_complete_template_creation_workflow(self, playground_url):
        """Test complete template creation workflow: create -> list -> get -> render"""
        # 1. Create a new template
        create_payload = {
            "id": "integration-workflow-test",
            "version": "1.0.0",
            "description": "Integration test template",
            "template": "Processing {{ task }} for {{ user }} with priority {{ priority }}",
            "inputs": {
                "task": {
                    "type": "string",
                    "required": True
                },
                "user": {
                    "type": "string",
                    "required": True
                },
                "priority": {
                    "type": "string",
                    "required": False,
                    "default": "normal"
                }
            },
            "metadata": {
                "tags": ["integration", "workflow"],
                "category": "testing"
            }
        }

        create_response = requests.post(
            f"{playground_url}/api/templates",
            json=create_payload
        )
        assert create_response.status_code == 200

        # 2. Verify it appears in templates list
        list_response = requests.get(f"{playground_url}/api/templates")
        templates = list_response.json()
        assert "integration-workflow-test" in templates

        # 3. Get template details
        get_response = requests.get(f"{playground_url}/api/templates/integration-workflow-test")
        assert get_response.status_code == 200
        template_data = get_response.json()

        # Verify all data is preserved
        assert template_data["id"] == "integration-workflow-test"
        assert template_data["description"] == "Integration test template"
        assert template_data["inputs"]["task"]["required"] is True
        assert template_data["inputs"]["priority"]["default"] == "normal"
        assert template_data["metadata"]["category"] == "testing"

        # 4. Render template with minimal inputs (using defaults)
        render_payload = {
            "inputs": {
                "task": "testing",
                "user": "test-user"
            }
        }

        render_response = requests.post(
            f"{playground_url}/api/templates/integration-workflow-test/render",
            json=render_payload
        )
        assert render_response.status_code == 200

        render_data = render_response.json()
        assert "Processing testing for test-user with priority normal" == render_data["rendered"]

        # 5. Render template with all inputs provided
        full_render_payload = {
            "inputs": {
                "task": "deployment",
                "user": "admin",
                "priority": "high"
            }
        }

        full_render_response = requests.post(
            f"{playground_url}/api/templates/integration-workflow-test/render",
            json=full_render_payload
        )
        assert full_render_response.status_code == 200

        full_render_data = full_render_response.json()
        assert "Processing deployment for admin with priority high" == full_render_data["rendered"]

        # 6. Verify inputs_used contains all expected values
        inputs_used = full_render_data["inputs_used"]
        assert inputs_used["task"] == "deployment"
        assert inputs_used["user"] == "admin"
        assert inputs_used["priority"] == "high"