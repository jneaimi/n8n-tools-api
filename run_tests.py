#!/usr/bin/env python3
"""
Test runner script for N8N Tools API.

Provides convenient commands to run different types of tests with proper
configuration and reporting.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: list, description: str = None) -> bool:
    """Run a command and return success status."""
    if description:
        print(f"\n{'='*50}")
        print(f"🔄 {description}")
        print(f"{'='*50}")
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description or 'Command'} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description or 'Command'} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ["pytest", "pytest-cov", "pytest-asyncio", "httpx"]
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    return True


def run_unit_tests(verbose: bool = False, coverage: bool = True):
    """Run unit tests."""
    cmd = ["pytest", "tests/unit/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    
    cmd.extend(["--tb=short", "-x"])  # Stop on first failure
    
    return run_command(cmd, "Running Unit Tests")


def run_integration_tests(verbose: bool = False):
    """Run integration tests."""
    cmd = ["pytest", "tests/integration/", "-m", "integration"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["--tb=short"])
    
    return run_command(cmd, "Running Integration Tests")


def run_docker_tests(verbose: bool = False):
    """Run Docker container tests."""
    # Check if Docker is available
    if not run_command(["docker", "--version"], "Checking Docker availability"):
        print("⚠️  Docker tests skipped - Docker not available")
        return True
    
    cmd = ["pytest", "tests/docker/", "-m", "docker"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["--tb=short"])
    
    return run_command(cmd, "Running Docker Tests")


def run_performance_tests(verbose: bool = False):
    """Run performance tests."""
    cmd = ["pytest", "tests/", "-m", "slow"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["--tb=short"])
    
    return run_command(cmd, "Running Performance Tests")


def run_all_tests(verbose: bool = False, include_docker: bool = False, include_performance: bool = False):
    """Run all tests in sequence."""
    success = True
    
    # Unit tests (most important)
    success &= run_unit_tests(verbose, coverage=True)
    
    # Integration tests
    if success:
        success &= run_integration_tests(verbose)
    
    # Docker tests (optional)
    if success and include_docker:
        success &= run_docker_tests(verbose)
    
    # Performance tests (optional)
    if success and include_performance:
        success &= run_performance_tests(verbose)
    
    return success


def run_quick_tests():
    """Run a quick subset of tests for development."""
    cmd = [
        "pytest", 
        "tests/unit/test_pdf_service_enhanced.py",
        "tests/integration/test_pdf_endpoints_comprehensive.py::TestPDFEndpoints::test_health_check_endpoint",
        "tests/integration/test_pdf_endpoints_comprehensive.py::TestPDFEndpoints::test_pdf_info_endpoint_valid_file",
        "-v", "--tb=short"
    ]
    
    return run_command(cmd, "Running Quick Tests")


def lint_code():
    """Run code linting."""
    success = True
    
    # Black formatting check
    success &= run_command(["black", "--check", "--diff", "."], "Black Format Check")
    
    # Flake8 linting
    success &= run_command(["flake8", "app", "tests"], "Flake8 Linting")
    
    # MyPy type checking
    success &= run_command(["mypy", "app", "--ignore-missing-imports"], "MyPy Type Check")
    
    return success


def format_code():
    """Format code with Black and isort."""
    success = True
    
    # Black formatting
    success &= run_command(["black", "."], "Black Code Formatting")
    
    # Import sorting
    success &= run_command(["isort", "."], "Import Sorting")
    
    return success


def generate_coverage_report():
    """Generate detailed coverage report."""
    cmd = [
        "pytest", 
        "tests/unit/", 
        "--cov=app", 
        "--cov-report=html:tests/coverage",
        "--cov-report=term-missing",
        "--cov-report=xml:tests/coverage.xml"
    ]
    
    success = run_command(cmd, "Generating Coverage Report")
    
    if success:
        print("\n📊 Coverage report generated:")
        print("  - HTML: tests/coverage/index.html")
        print("  - XML: tests/coverage.xml")
    
    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="N8N Tools API Test Runner")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Unit tests
    unit_parser = subparsers.add_parser("unit", help="Run unit tests")
    unit_parser.add_argument("--no-coverage", action="store_true", help="Skip coverage report")
    
    # Integration tests
    subparsers.add_parser("integration", help="Run integration tests")
    
    # Docker tests
    subparsers.add_parser("docker", help="Run Docker tests")
    
    # Performance tests
    subparsers.add_parser("performance", help="Run performance tests")
    
    # All tests
    all_parser = subparsers.add_parser("all", help="Run all tests")
    all_parser.add_argument("--include-docker", action="store_true", help="Include Docker tests")
    all_parser.add_argument("--include-performance", action="store_true", help="Include performance tests")
    
    # Quick tests
    subparsers.add_parser("quick", help="Run quick subset of tests")
    
    # Code quality
    subparsers.add_parser("lint", help="Run code linting")
    subparsers.add_parser("format", help="Format code")
    subparsers.add_parser("coverage", help="Generate coverage report")
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    success = True
    
    if args.command == "unit":
        success = run_unit_tests(args.verbose, coverage=not args.no_coverage)
    elif args.command == "integration":
        success = run_integration_tests(args.verbose)
    elif args.command == "docker":
        success = run_docker_tests(args.verbose)
    elif args.command == "performance":
        success = run_performance_tests(args.verbose)
    elif args.command == "all":
        success = run_all_tests(args.verbose, args.include_docker, args.include_performance)
    elif args.command == "quick":
        success = run_quick_tests()
    elif args.command == "lint":
        success = lint_code()
    elif args.command == "format":
        success = format_code()
    elif args.command == "coverage":
        success = generate_coverage_report()
    else:
        parser.print_help()
        return 0
    
    if success:
        print(f"\n🎉 {args.command.title()} completed successfully!")
        return 0
    else:
        print(f"\n💥 {args.command.title()} failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
