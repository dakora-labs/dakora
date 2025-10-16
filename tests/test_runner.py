#!/usr/bin/env python3
"""
Test runner for Dakora with different test categories
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=False, fast=False):
    """Run different categories of tests"""

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    # Add coverage if requested
    cmd.extend(["--tb=short"])

    # Determine which tests to run
    test_args = []

    if test_type == "all":
        # Run all unit, integration, and performance tests
        test_args = ["tests/"]
        if fast:
            cmd.extend(["-m", "not slow"])  # Skip slow tests in fast mode

    elif test_type == "unit":
        # Run unit tests
        test_args = ["tests/", "-m", "unit or not (integration or performance)"]

    elif test_type == "integration":
        # Run integration tests
        test_args = ["tests/", "-m", "integration"]

    elif test_type == "performance":
        # Run performance tests
        test_args = ["tests/", "-m", "performance"]
        if fast:
            cmd.extend(["-m", "not slow"])  # Skip slow tests in fast mode

    elif test_type == "smoke":
        # Run a quick smoke test with minimal tests
        test_args = [
            "tests/smoke_test.py",
            "-v"
        ]

    else:
        print(f"Unknown test type: {test_type}")
        return 1

    # Add test args to command
    cmd.extend(test_args)

    print(f"Running tests: {' '.join(cmd)}")
    print("-" * 60)

    # Run the tests
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run Dakora tests")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "performance", "smoke"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-f", "--fast",
        action="store_true",
        help="Skip slow tests"
    )

    args = parser.parse_args()

    print("🧪 Dakora Test Runner")
    print(f"Test type: {args.test_type}")
    if args.fast:
        print("Fast mode: skipping slow tests")
    print("")

    return run_tests(args.test_type, args.verbose, args.fast)


if __name__ == "__main__":
    sys.exit(main())