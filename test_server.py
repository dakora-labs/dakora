#!/usr/bin/env python3
"""
Quick test script to verify the server structure is correct
Run this from the project root: python test_server.py
"""

import sys
from pathlib import Path

# Add server to path
server_path = Path(__file__).parent / "server"
sys.path.insert(0, str(server_path))

print("Testing server imports...")

try:
    from dakora_server.core.vault import Vault
    print("✓ Vault import successful")
except ImportError as e:
    print(f"✗ Vault import failed: {e}")
    sys.exit(1)

try:
    from dakora_server.core.renderer import Renderer
    print("✓ Renderer import successful")
except ImportError as e:
    print(f"✗ Renderer import failed: {e}")
    sys.exit(1)

try:
    from dakora_server.core.model import TemplateSpec
    print("✓ TemplateSpec import successful")
except ImportError as e:
    print(f"✗ TemplateSpec import failed: {e}")
    sys.exit(1)

try:
    from dakora_server.api import prompts, render, models, health
    print("✓ API routes import successful")
except ImportError as e:
    print(f"✗ API routes import failed: {e}")
    sys.exit(1)

try:
    from dakora_server.main import app
    print("✓ FastAPI app import successful")
except ImportError as e:
    print(f"✗ FastAPI app import failed: {e}")
    sys.exit(1)

try:
    from dakora_server.config import settings, get_vault
    print("✓ Config import successful")
except ImportError as e:
    print(f"✗ Config import failed: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")
print("\nNext steps:")
print("1. Install server dependencies:")
print("   cd server && pip install -e .")
print("\n2. Start the server:")
print("   cd server && uvicorn dakora_server.main:app --reload --port 8000")
print("\n3. Test health endpoint:")
print("   curl http://localhost:8000/api/health")