#!/usr/bin/env python3
"""
Version bumping script for Dakora monorepo.

Usage:
    python scripts/bump_version.py platform 2.0.0  # Bump CLI + Server
    python scripts/bump_version.py sdk 1.5.0       # Bump Python SDK only
"""

import sys
import tomllib
import tomli_w
from pathlib import Path

def bump_version(component: str, new_version: str):
    """Bump version in pyproject.toml files."""
    root = Path(__file__).parent.parent

    files_to_update = []

    if component == "platform":
        files_to_update = [
            root / "cli" / "pyproject.toml",
            root / "server" / "pyproject.toml",
        ]
        print(f"Bumping platform (CLI + Server) to version {new_version}")
    elif component == "sdk":
        files_to_update = [
            root / "packages" / "client-python" / "pyproject.toml",
        ]
        print(f"Bumping Python SDK to version {new_version}")
    else:
        print(f"Unknown component: {component}")
        print("Use 'platform' or 'sdk'")
        sys.exit(1)

    for file_path in files_to_update:
        if not file_path.exists():
            print(f"Warning: {file_path} does not exist, skipping")
            continue

        with open(file_path, "rb") as f:
            data = tomllib.load(f)

        old_version = data["project"]["version"]
        data["project"]["version"] = new_version

        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)

        print(f"  ✓ {file_path.relative_to(root)}: {old_version} → {new_version}")

    print(f"\n✅ Version bump complete!")
    print("\nNext steps:")
    print("  1. Review changes: git diff")
    print("  2. Run tests: uv run pytest")
    print("  3. Test builds:")
    if component == "platform":
        print("     cd cli && uv build")
        print("     cd server && uv build")
    else:
        print("     cd packages/client-python && uv build")
    print("  4. Commit: git add . && git commit -m 'chore: bump version to {}'".format(new_version))
    print("  5. Push: git push origin main")
    print("  6. Release via GitHub Actions")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/bump_version.py <component> <version>")
        print("  component: 'platform' (CLI + Server) or 'sdk' (Python SDK)")
        print("  version: e.g., '2.0.0'")
        sys.exit(1)

    component = sys.argv[1]
    version = sys.argv[2]

    bump_version(component, version)