#!/usr/bin/env python3
"""
Main Benchmark Runner
Runs all benchmarks across Python, Julia, and R languages.

Usage:
    python main.py                    # Run all benchmarks
    python main.py --scenario matrix  # Run specific scenario
    python main.py --lang python     # Run specific language
    python main.py --validate        # Validate cross-language results
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent
PROJECT_DIR = BENCHMARK_DIR.parent

# Benchmark scenarios
SCENARIOS = {
    "matrix_ops": {
        "name": "Matrix Operations",
        "files": {
            "python": "matrix_ops.py",
            "julia": "matrix_ops.jl",
            "r": "matrix_ops.R",
        },
    },
    "io_ops": {
        "name": "I/O Operations",
        "files": {"python": "io_ops.py", "julia": "io_ops.jl", "r": "io_ops.R"},
    },
    "hsi_stream": {
        "name": "Hyperspectral SAM",
        "files": {
            "python": "hsi_stream.py",
            "julia": "hsi_stream.jl",
            "r": "hsi_stream.R",
        },
    },
    "vector_pip": {
        "name": "Vector Point-in-Polygon",
        "files": {
            "python": "vector_pip.py",
            "julia": "vector_pip.jl",
            "r": "vector_pip.R",
        },
    },
    "interpolation": {
        "name": "IDW Interpolation",
        "files": {
            "python": "interpolation_idw.py",
            "julia": "interpolation_idw.jl",
            "r": "interpolation_idw.R",
        },
    },
    "timeseries": {
        "name": "Time-Series NDVI",
        "files": {
            "python": "timeseries_ndvi.py",
            "julia": "timeseries_ndvi.jl",
            "r": "timeseries_ndvi.R",
        },
    },
    "raster_algebra": {
        "name": "Raster Algebra & Band Math",
        "files": {
            "python": "raster_algebra.py",
            "julia": "raster_algebra.jl",
            "r": "raster_algebra.R",
        },
    },
    "zonal_stats": {
        "name": "Zonal Statistics",
        "files": {
            "python": "zonal_stats.py",
            "julia": "zonal_stats.jl",
            "r": "zonal_stats.R",
        },
    },
    "reprojection": {
        "name": "Coordinate Reprojection",
        "files": {
            "python": "reprojection.py",
            "julia": "reprojection.jl",
            "r": "reprojection.R",
        },
    },
}


def run_command(cmd, cwd=None, description=None):
    """Run a shell command and handle errors."""
    if description:
        print(f"\n{'=' * 60}")
        print(f"{description}")
        print("=" * 60)

    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or BENCHMARK_DIR, capture_output=False, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def run_python_benchmark(script):
    """Run a Python benchmark."""
    # Check if venv exists
    venv_python = PROJECT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        cmd = f"source {PROJECT_DIR}/.venv/bin/activate && python {script}"
    else:
        cmd = f"python3 {script}"
    return run_command(cmd, description=f"Python: {script}")


def run_julia_benchmark(script):
    """Run a Julia benchmark."""
    # Use julialauncher for proper Julia environment
    julia_cmd = os.path.expanduser("~/.juliaup/bin/julialauncher")
    if not os.path.exists(julia_cmd):
        julia_cmd = "julia"  # Fallback
    cmd = f"{julia_cmd} {script}"
    return run_command(cmd, description=f"Julia: {script}")


def run_r_benchmark(script):
    """Run an R benchmark."""
    cmd = f"Rscript {script}"
    return run_command(cmd, description=f"R: {script}")


def run_scenario(scenario_name, languages=None):
    """Run a specific benchmark scenario."""
    if scenario_name not in SCENARIOS:
        print(f"Unknown scenario: {scenario_name}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        return False

    scenario = SCENARIOS[scenario_name]
    print(f"\n{'#' * 60}")
    print(f"# {scenario['name']}")
    print(f"{'#' * 60}")

    all_passed = True

    for lang, script in scenario["files"].items():
        if languages and lang not in languages:
            continue

        script_path = BENCHMARK_DIR / script
        if not script_path.exists():
            print(f"⚠ {script} not found, skipping...")
            continue

        if lang == "python":
            success = run_python_benchmark(script)
        elif lang == "julia":
            success = run_julia_benchmark(script)
        elif lang == "r":
            success = run_r_benchmark(script)
        else:
            continue

        if not success:
            all_passed = False
            print(f"✗ {lang.capitalize()} benchmark failed")

    return all_passed


def run_all(languages=None):
    """Run all benchmarks."""
    print("\n" + "=" * 60)
    print("RUNNING ALL BENCHMARKS")
    print("=" * 60)

    results = {}

    for scenario_name in SCENARIOS:
        results[scenario_name] = run_scenario(scenario_name, languages)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for scenario_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {SCENARIOS[scenario_name]['name']}")

    print(f"\nPassed: {passed}/{total}")

    return passed == total


def run_validation():
    """Run cross-language validation."""
    print("\n" + "=" * 60)
    print("CROSS-LANGUAGE VALIDATION")
    print("=" * 60)

    # Run validation script
    validate_script = PROJECT_DIR / "tools" / "compare_results.py"
    if validate_script.exists():
        cmd = f"python {validate_script}"
        run_command(cmd, description="Cross-language validation")
    else:
        print("Validation script not found")

    # Run literature comparison
    tedesco_script = PROJECT_DIR / "tools" / "compare_with_tedesco.py"
    if tedesco_script.exists():
        cmd = f"python {tedesco_script}"
        run_command(cmd, description="Literature comparison (Tedesco et al.)")
    else:
        print("Literature comparison script not found")


def main():
    parser = argparse.ArgumentParser(description="Thesis Benchmark Runner")
    parser.add_argument("--scenario", "-s", help="Run specific scenario")
    parser.add_argument(
        "--lang",
        "-l",
        nargs="+",
        choices=["python", "julia", "r"],
        help="Run specific languages",
    )
    parser.add_argument(
        "--validate", "-v", action="store_true", help="Run cross-language validation"
    )
    parser.add_argument("--all", "-a", action="store_true", help="Run all benchmarks")

    args = parser.parse_args()

    if args.validate:
        run_validation()
    elif args.scenario:
        run_scenario(args.scenario, args.lang)
    elif args.all or not any([args.scenario, args.validate]):
        run_all(args.lang)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
