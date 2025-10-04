#!/usr/bin/env python3
"""
Simple environment variable loader for examples.

This utility helps load environment variables from a .env file
if you don't want to use python-dotenv as a dependency.

Usage:
    from load_env import load_env
    load_env()  # Loads from .env if it exists
"""

import os
from pathlib import Path


def load_env(env_file: str = ".env") -> None:
    """
    Load environment variables from a .env file.
    
    The .env file is searched in the following order:
    1. If env_file is an absolute path, use that
    2. Look in the same directory as this script
    3. Look in the current working directory
    
    Args:
        env_file: Path to .env file (default: .env in script directory)
    """
    # If absolute path provided, use it directly
    env_path = Path(env_file)
    if env_path.is_absolute():
        if not env_path.exists():
            print(f"ℹ️  No {env_file} file found. Using existing environment variables.")
            return
    else:
        # Try script directory first (most common case)
        script_dir = Path(__file__).parent
        env_path = script_dir / env_file
        
        # If not in script directory, try current working directory
        if not env_path.exists():
            env_path = Path(env_file)
            if not env_path.exists():
                print(f"ℹ️  No {env_file} file found in {script_dir} or current directory.")
                print("    Using existing environment variables.")
                return
    
    print(f"📁 Loading environment variables from {env_path}...")
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value
                    print(f"  ✓ Set {key}")
                else:
                    print(f"  ⊗ Skipped {key} (already set)")
    
    print("✅ Environment variables loaded!\n")


def check_required_vars(required: list[str]) -> bool:
    """
    Check if required environment variables are set.
    
    Args:
        required: List of required environment variable names
        
    Returns:
        True if all required vars are set, False otherwise
    """
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        return False
    
    print("✅ All required environment variables are set!")
    return True


def print_config_info() -> None:
    """Print current Azure configuration (without exposing secrets)."""
    print("\n📋 Current Configuration:")
    print("-" * 50)
    
    # Azure OpenAI
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if endpoint:
        print(f"Azure OpenAI Endpoint: {endpoint}")
    
    # Azure AI Foundry
    ai_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if ai_endpoint:
        print(f"Azure AI Project: {ai_endpoint}")
    
    # Model deployment
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") or \
                 os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if deployment:
        print(f"Model Deployment: {deployment}")
    
    # API version
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
    if api_version:
        print(f"API Version: {api_version}")
    
    # Auth method
    if os.environ.get("AZURE_OPENAI_API_KEY"):
        print("Authentication: API Key ✓")
    else:
        print("Authentication: Azure CLI (default)")
    
    print("-" * 50)
    print()


if __name__ == "__main__":
    # Demo usage
    load_env()
    check_required_vars(["AZURE_OPENAI_ENDPOINT"])
    print_config_info()
