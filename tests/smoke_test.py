#!/usr/bin/env python3
"""
Quick smoke test for Dakora functionality
"""
import tempfile
from pathlib import Path
import yaml
import sys
import os
import gc
import time

# Add parent directory to path to import dakora
sys.path.insert(0, str(Path(__file__).parent.parent))

from dakora.vault import Vault
from dakora.cli import app
import typer.testing

def test_vault_operations():
    """Test basic Vault operations"""
    print("🔍 Testing Vault operations...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        prompts_dir = tmpdir / "prompts"
        prompts_dir.mkdir()

        # Create test template
        # NOTE: Filename MUST match template ID for the new registry convention
        template_data = {
            "id": "test_template",
            "version": "1.0.0",
            "description": "A test template",
            "template": "Hello {{ name }}! You are {{ age }} years old.",
            "inputs": {
                "name": {"type": "string", "required": True},
                "age": {"type": "number", "required": True}
            }
        }

        (prompts_dir / "test_template.yaml").write_text(yaml.safe_dump(template_data))

        # Test Vault initialization
        vault = Vault(prompt_dir=str(prompts_dir))
        
        try:
            # Test listing templates
            template_ids = list(vault.list())
            assert "test_template" in template_ids, f"Template not found in list: {template_ids}"
            print("✅ Template listing works")

            # Test getting template
            template = vault.get("test_template")
            assert template.id == "test_template"
            assert template.version == "1.0.0"
            print("✅ Template retrieval works")

            # Test rendering
            result = template.render(name="Alice", age=30)
            expected = "Hello Alice! You are 30 years old."
            assert result == expected, f"Expected '{expected}', got '{result}'"
            print("✅ Template rendering works")

            # Test type coercion
            result2 = template.render(name="Bob", age="25")  # string age should be coerced
            expected2 = "Hello Bob! You are 25.0 years old."
            assert result2 == expected2, f"Type coercion failed: {result2}"
            print("✅ Type coercion works")
        finally:
            vault.close()

def test_cli_operations():
    """Test CLI commands"""
    print("\n🔍 Testing CLI operations...")

    runner = typer.testing.CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Test init command
            result = runner.invoke(app, ["init"])
            assert result.exit_code == 0, f"Init failed: {result.stdout}"
            assert Path("dakora.yaml").exists(), "Config file not created"
            assert Path("prompts/summarizer.yaml").exists(), "Example template not created"
            print("✅ CLI init works")

            # Test list command
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0, f"List failed: {result.stdout}"
            assert "summarizer" in result.stdout, f"Summarizer not in output: {result.stdout}"
            print("✅ CLI list works")

            # Test get command
            result = runner.invoke(app, ["get", "summarizer"])
            assert result.exit_code == 0, f"Get failed: {result.stdout}"
            assert "{{ input_text }}" in result.stdout, f"Template content not found: {result.stdout}"
            print("✅ CLI get works")

            # Test bump command
            result = runner.invoke(app, ["bump", "summarizer", "--patch"])
            assert result.exit_code == 0, f"Bump failed: {result.stdout}"
            assert "1.0.1" in result.stdout, f"Version not bumped: {result.stdout}"
            print("✅ CLI bump works")
            
            # Clean up database connections before directory cleanup
            if Path("dakora.db").exists():
                # Load and close vault to release database locks
                vault = Vault("dakora.yaml")
                vault.close()
                gc.collect()
                time.sleep(0.1)

        finally:
            os.chdir(original_cwd)

def test_error_handling():
    """Test error conditions"""
    print("\n🔍 Testing error handling...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        prompts_dir = tmpdir / "prompts"
        prompts_dir.mkdir()

        vault = Vault(prompt_dir=str(prompts_dir))
        
        try:
            # Test template not found
            try:
                vault.get("nonexistent")
                assert False, "Should have raised TemplateNotFound"
            except Exception as e:
                assert "TemplateNotFound" in str(type(e)), f"Wrong exception type: {type(e)}"
                print("✅ Template not found error works")

            # Test validation error
            template_data = {
                "id": "validation_test",
                "version": "1.0.0",
                "template": "Hello {{ name }}!",
                "inputs": {
                    "name": {"type": "string", "required": True}
                }
            }
            # Filename must match ID
            (prompts_dir / "validation_test.yaml").write_text(yaml.safe_dump(template_data))

            template = vault.get("validation_test")
            try:
                template.render()  # Missing required input
                assert False, "Should have raised ValidationError"
            except Exception as e:
                assert "missing input" in str(e), f"Wrong error message: {e}"
                print("✅ Validation error works")
        finally:
            vault.close()

def main():
    """Run all smoke tests"""
    print("🚀 Running Dakora smoke tests...\n")

    try:
        test_vault_operations()
        test_cli_operations()
        test_error_handling()

        print("\n🎉 All smoke tests passed! Dakora is working correctly.")
        return 0

    except Exception as e:
        print(f"\n❌ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())