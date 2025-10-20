"""
Manual integration test for OpenAI gpt-5-nano.

This test is NOT run in CI to avoid costs. Run manually with:

    export OPENAI_API_KEY=your_key_here
    uv run python tests/manual_test_openai.py

Or use a .env file in the project root:

    OPENAI_API_KEY=your_key_here

This test uses gpt-5-nano which is the most cost-efficient GPT-5 model.
"""

import tempfile
from pathlib import Path
import yaml
import sys
import os

from dotenv import load_dotenv
from dakora.vault import Vault
from dakora.exceptions import APIKeyError

load_dotenv()


def test_gpt5_nano_execution():
    print("=" * 60)
    print("OpenAI GPT-5 Nano Integration Test")
    print("=" * 60)
    print()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("💡 Set it with: export OPENAI_API_KEY=your_key_here")
        print("💡 Or create a .env file in the project root")
        sys.exit(1)

    print(f"✅ API key found: {api_key[:10]}...{api_key[-4:]}")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()

        test_template = {
            "id": "summarizer",
            "version": "1.0.0",
            "description": "Test template for GPT-5 Nano",
            "template": "Summarize the following text in one sentence:\n\n{{ input_text }}",
            "inputs": {
                "input_text": {
                    "type": "string",
                    "required": True
                }
            }
        }

        template_path = prompts_dir / "summarizer.yaml"
        template_path.write_text(yaml.safe_dump(test_template))

        config = {
            "registry": "local",
            "prompt_dir": str(prompts_dir),
            "logging": {
                "enabled": True,
                "backend": "sqlite",
                "db_path": str(Path(tmpdir) / "dakora.db")
            }
        }

        config_path = Path(tmpdir) / "dakora.yaml"
        config_path.write_text(yaml.safe_dump(config))

        vault = Vault(str(config_path))
        template = vault.get("summarizer")

        test_text = """
        Artificial intelligence has made remarkable progress in recent years.
        Large language models can now understand and generate human-like text,
        assist with coding, and solve complex reasoning tasks. However, they still
        face challenges with factual accuracy and reasoning capabilities.
        """

        print("📝 Test Input:")
        print(test_text.strip())
        print()

        print("🚀 Executing with gpt-5-nano...")
        print()

        try:
            result = template.execute(
                model="gpt-5-nano",
                input_text=test_text.strip(),
                temperature=0.7
            )

            print("✅ Execution successful!")
            print()
            print("=" * 60)
            print("RESULTS")
            print("=" * 60)
            print()
            print(f"Model:        {result.model}")
            print(f"Provider:     {result.provider}")
            print(f"Cost:         ${result.cost_usd:.6f} USD")
            print(f"Latency:      {result.latency_ms} ms ({result.latency_ms / 1000:.2f}s)")
            print(f"Tokens In:    {result.tokens_in}")
            print(f"Tokens Out:   {result.tokens_out}")
            print(f"Total Tokens: {result.tokens_in + result.tokens_out}")
            print()
            print("=" * 60)
            print("OUTPUT")
            print("=" * 60)
            print()
            print(result.output)
            print()

            assert result.provider == "openai"
            assert result.model == "gpt-5-nano"
            assert result.tokens_in > 0
            assert result.tokens_out > 0
            assert len(result.output) > 0

            print("=" * 60)
            print("✅ All assertions passed!")
            print("=" * 60)

        except APIKeyError as e:
            print(f"❌ API Key Error: {e}")
            print("💡 Check that your OPENAI_API_KEY is valid")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def test_gpt5_nano_with_custom_params():
    print()
    print("=" * 60)
    print("GPT-5 Nano with Custom LLM Parameters Test")
    print("=" * 60)
    print()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set, skipping test")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()

        test_template = {
            "id": "creative-writer",
            "version": "1.0.0",
            "description": "Write creatively",
            "template": "Write a one-sentence creative description of:\n\n{{ topic }}",
            "inputs": {
                "topic": {
                    "type": "string",
                    "required": True
                }
            }
        }

        (prompts_dir / "creative-writer.yaml").write_text(yaml.safe_dump(test_template))

        vault = Vault(prompt_dir=str(prompts_dir))
        template = vault.get("creative-writer")

        print("📝 Test Topic: A sunset over mountains")
        print()
        print("🚀 Executing with gpt-5-nano and custom parameters (temperature, max_tokens)...")
        print()

        try:
            result = template.execute(
                model="gpt-5-nano",
                topic="A sunset over mountains",
                temperature=0.9,
                max_tokens=50
            )

            print("✅ Execution successful!")
            print()
            print(f"Cost:      ${result.cost_usd:.6f} USD")
            print(f"Latency:   {result.latency_ms} ms")
            print(f"Tokens:    {result.tokens_in} → {result.tokens_out}")
            print()
            print("Output:")
            print(result.output)
            print()

            print("=" * 60)
            print("✅ Custom parameters test passed!")
            print("=" * 60)

        except Exception as e:
            print(f"⚠️  Custom params test failed: {e}")


if __name__ == "__main__":
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  OpenAI GPT-5 Nano Manual Integration Tests".ljust(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    print("⚠️  These tests make real API calls and incur costs")
    print("💰 GPT-5 Nano is the most cost-efficient model")
    print()

    test_gpt5_nano_execution()
    test_gpt5_nano_with_custom_params()

    print()
    print("🎉 All manual integration tests completed!")
    print()
