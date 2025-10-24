#!/usr/bin/env python3
"""
Quick test validation script to check that our test suite works
"""
import subprocess
import sys


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"🧪 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    """Run validation tests"""
    print("🎯 Dakora Test Validation")
    print("=" * 50)

    tests = [
        (
            "export PATH=\"$HOME/.local/bin:$PATH\" && uv run python -m pytest server/tests/smoke_test.py::test_vault_operations -v --tb=no -q",
            "Vault operations test"
        ),
        (
            "export PATH=\"$HOME/.local/bin:$PATH\" && uv run python -m pytest server/tests/smoke_test.py::test_error_handling -v --tb=no -q",
            "Error handling test"
        ),
    ]

    passed = 0
    total = len(tests)

    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1

    print()
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All validation tests passed!")
        return 0
    else:
        print(f"⚠️  {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())