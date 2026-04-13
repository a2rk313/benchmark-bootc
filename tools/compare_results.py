#!/usr/bin/env python3
"""
Cross-Language Validation Tool
Compares results across Python, R, and Julia to verify correctness.

This tool:
1. Loads validation JSON files from all languages
2. Compares output hashes for each scenario
3. Flags any discrepancies
4. Generates comparison report
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

OUTPUT_DIR = Path("validation")


@dataclass
class ValidationResult:
    scenario: str
    language: str
    passed: bool
    hash: str
    details: Optional[Dict] = None


def load_validation_files(scenario: str) -> Dict[str, ValidationResult]:
    """Load validation files for all languages for a scenario."""
    results = {}

    for lang in ["python", "r", "julia"]:
        filepath = OUTPUT_DIR / f"{scenario}_{lang}_results.json"
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
                results[lang] = ValidationResult(
                    scenario=scenario,
                    language=lang,
                    passed=True,
                    hash=data.get("combined_hash", data.get("hash", "")),
                    details=data.get("results", {}),
                )
        else:
            results[lang] = ValidationResult(
                scenario=scenario,
                language=lang,
                passed=False,
                hash="MISSING",
                details={"error": "File not found"},
            )

    return results


def compare_hashes(results: Dict[str, ValidationResult]) -> Dict:
    """Compare hashes across languages."""
    comparison = {
        "scenario": None,
        "languages": {},
        "hashes_match": False,
        "all_present": False,
        "warnings": [],
    }

    if not results:
        return comparison

    comparison["scenario"] = next(iter(results.values())).scenario

    # Check which languages are present
    present = [lang for lang, res in results.items() if res.passed]
    comparison["all_present"] = len(present) == 3

    for lang, result in results.items():
        comparison["languages"][lang] = {
            "present": result.passed,
            "hash": result.hash,
            "timings": {},
        }

        if result.details:
            for op, data in result.details.items():
                if isinstance(data, dict):
                    comparison["languages"][lang]["timings"][op] = {
                        "min_time_s": data.get("min_time_s"),
                        "hash": data.get("hash", data.get("output_hash")),
                    }

    # Check if all hashes match
    if comparison["all_present"]:
        hashes = [results[lang].hash for lang in present]
        comparison["hashes_match"] = len(set(hashes)) == 1

        if not comparison["hashes_match"]:
            comparison["warnings"].append(
                f"Hash mismatch: {[results[lang].hash for lang in present]}"
            )
    else:
        missing = [lang for lang in ["python", "r", "julia"] if lang not in present]
        comparison["warnings"].append(f"Missing languages: {missing}")

    return comparison


def compare_performance(comparison: Dict) -> Dict:
    """Compare performance across languages."""
    perf = {"fastest_by_operation": {}, "speedup_matrix": {}}

    # Find fastest for each operation
    for lang, data in comparison["languages"].items():
        if not data["present"]:
            continue

        for op, timing in data["timings"].items():
            min_time = timing.get("min_time_s")
            if min_time is None:
                continue

            if op not in perf["fastest_by_operation"]:
                perf["fastest_by_operation"][op] = {
                    "language": lang,
                    "time_s": min_time,
                }
            elif min_time < perf["fastest_by_operation"][op]["time_s"]:
                perf["fastest_by_operation"][op] = {
                    "language": lang,
                    "time_s": min_time,
                }

    # Calculate speedups
    languages = [
        l for l in comparison["languages"] if comparison["languages"][l]["present"]
    ]
    if len(languages) >= 2:
        baseline = languages[0]

        for lang in languages[1:]:
            perf["speedup_matrix"][lang] = {}

            ops = set(comparison["languages"][baseline]["timings"].keys()) & set(
                comparison["languages"][lang]["timings"].keys()
            )

            for op in ops:
                baseline_time = comparison["languages"][baseline]["timings"][op].get(
                    "min_time_s"
                )
                lang_time = comparison["languages"][lang]["timings"][op].get(
                    "min_time_s"
                )

                if baseline_time and lang_time and baseline_time > 0:
                    speedup = baseline_time / lang_time
                    perf["speedup_matrix"][lang][op] = round(speedup, 2)

    return perf


def generate_report(scenarios: List[str]) -> str:
    """Generate a comprehensive comparison report."""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("CROSS-LANGUAGE BENCHMARK VALIDATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    all_comparisons = {}

    for scenario in scenarios:
        results = load_validation_files(scenario)
        comparison = compare_hashes(results)
        performance = compare_performance(comparison)

        all_comparisons[scenario] = {
            "hash_comparison": comparison,
            "performance": performance,
        }

        # Hash comparison section
        report_lines.append(f"\n{'─' * 80}")
        report_lines.append(f"SCENARIO: {scenario.upper()}")
        report_lines.append(f"{'─' * 80}")

        # Language presence
        report_lines.append("\n[Language Presence]")
        for lang in ["python", "r", "julia"]:
            present = comparison["languages"][lang]["present"]
            status = "✓" if present else "✗"
            report_lines.append(
                f"  {status} {lang.capitalize()}: {'Present' if present else 'Missing'}"
            )

        # Hash comparison
        report_lines.append("\n[Hash Comparison]")
        if comparison["hashes_match"]:
            report_lines.append("  ✓ All languages produce identical results")
        else:
            report_lines.append("  ✗ Hash mismatch detected!")
            for lang in ["python", "r", "julia"]:
                if comparison["languages"][lang]["present"]:
                    h = comparison["languages"][lang]["hash"]
                    report_lines.append(f"    {lang}: {h}")

        # Performance comparison
        report_lines.append("\n[Performance Summary]")
        for op, fastest in performance["fastest_by_operation"].items():
            report_lines.append(
                f"  {op}: {fastest['language']} ({fastest['time_s']:.4f}s)"
            )

        # Speedup matrix
        if performance["speedup_matrix"]:
            report_lines.append("\n[Speedup Matrix (vs Python)]")
            for lang, ops in performance["speedup_matrix"].items():
                if ops:
                    report_lines.append(f"  {lang.capitalize()}:")
                    for op, speedup in ops.items():
                        better = "faster" if speedup > 1 else "slower"
                        report_lines.append(f"    {op}: {speedup:.2f}x {better}")

        # Warnings
        if comparison["warnings"]:
            report_lines.append("\n[Warnings]")
            for warning in comparison["warnings"]:
                report_lines.append(f"  ⚠ {warning}")

    # Summary
    report_lines.append("\n" + "=" * 80)
    report_lines.append("SUMMARY")
    report_lines.append("=" * 80)

    scenarios_with_all = sum(
        1 for c in all_comparisons.values() if c["hash_comparison"]["all_present"]
    )
    scenarios_with_match = sum(
        1 for c in all_comparisons.values() if c["hash_comparison"]["hashes_match"]
    )

    report_lines.append(
        f"\nScenarios with all languages: {scenarios_with_all}/{len(scenarios)}"
    )
    report_lines.append(
        f"Scenarios with matching hashes: {scenarios_with_match}/{len(scenarios)}"
    )

    if scenarios_with_match == len(scenarios):
        report_lines.append(
            "\n✓ All scenarios produce consistent results across languages!"
        )
    else:
        report_lines.append("\n⚠ Some scenarios have hash mismatches - review needed")

    return "\n".join(report_lines)


def main():
    # Define available scenarios (matches actual file naming)
    scenarios = [
        "matrix_ops",
        "io_ops",
        "raster",  # hsi_stream scenario
        "vector",  # vector_pip scenario
        "interpolation",
        "timeseries",
        "raster_algebra",
        "zonal_stats",
        "reprojection",
    ]

    print("Cross-Language Validation Tool")
    print("-" * 40)

    # Generate report
    report = generate_report(scenarios)
    print(report)

    # Save report
    report_path = OUTPUT_DIR / "cross_language_validation_report.txt"
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n✓ Report saved to: {report_path}")

    # Save JSON comparison
    import json

    json_output = {}
    for scenario in scenarios:
        results = load_validation_files(scenario)
        json_output[scenario] = compare_hashes(results)

    json_path = OUTPUT_DIR / "cross_language_comparison.json"
    with open(json_path, "w") as f:
        json.dump(json_output, f, indent=2, default=str)

    print(f"✓ JSON comparison saved to: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
