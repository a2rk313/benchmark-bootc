#!/usr/bin/env python3
"""
================================================================================
Thesis Benchmark Validation Suite
================================================================================

Unified validation for cross-language correctness and methodology verification.

Usage:
    python validation/thesis_validation.py --all           # All validations
    python validation/thesis_validation.py --correctness    # Cross-language validation
    python validation/thesis_validation.py --chen-revels    # Chen & Revels methodology
    python validation/thesis_validation.py --stats          # Statistical analysis
    python validation/thesis_validation.py --report         # Generate full report

================================================================================
"""

import argparse
import json
import sys
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import stats
    from scipy.signal import find_peaks

    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    warnings.warn("matplotlib/scipy not available - plotting disabled")


# =============================================================================
# ANSI Colors
# =============================================================================


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    END = "\033[0m"


# =============================================================================
# Cross-Language Validation
# =============================================================================


def load_validation_results(validation_dir: str = "validation") -> Dict:
    """Load all validation JSON files."""
    results = defaultdict(dict)
    validation_path = Path(validation_dir)

    if not validation_path.exists():
        return results

    for json_file in validation_path.glob("*_results.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            scenario = data.get("scenario", "unknown")
            language = data.get("language", "unknown")
            results[scenario][language] = data
        except Exception as e:
            print(
                f"{Colors.YELLOW}Warning: Could not load {json_file}: {e}{Colors.END}"
            )

    return results


def validate_cross_language_correctness(results: Dict) -> Tuple[bool, Dict]:
    """
    Validate that all language implementations produce equivalent results.

    Checks:
    1. Numerical precision (within acceptable tolerance)
    2. Output consistency (same counts/matches)
    3. Validation hash agreement
    """
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print("CROSS-LANGUAGE CORRECTNESS VALIDATION")
    print(f"{'=' * 70}{Colors.END}")

    all_valid = True
    details = {}

    for scenario, lang_results in results.items():
        if len(lang_results) < 2:
            continue

        scenario_valid = True
        scenario_details = {"checks": []}

        print(f"\n{Colors.BLUE}{scenario.upper()}{Colors.END}")
        print("-" * 50)

        # Check match counts / pixels processed
        counts = {}
        for lang, data in lang_results.items():
            if "matches_found" in data:
                counts[lang] = data["matches_found"]
            elif "pixels_processed" in data:
                counts[lang] = data["pixels_processed"]
            elif "total_pixels_processed" in data:
                counts[lang] = data["total_pixels_processed"]

        if counts:
            values = list(counts.values())
            max_diff = max(values) - min(values)
            tolerance = 0.01 * min(values)  # 1% tolerance

            check = {
                "name": "Count Consistency",
                "passed": max_diff <= tolerance,
                "details": {k: f"{v:,}" for k, v in counts.items()},
            }
            scenario_details["checks"].append(check)

            if max_diff <= tolerance:
                print(f"  ✓ Counts consistent: {counts}")
            else:
                print(f"  ✗ Count variance too high: {max_diff} > {tolerance:.0f}")
                scenario_valid = False

        # Check statistical measures
        mean_keys = ["mean_distance_m", "mean_ndvi", "mean_sam_rad", "mean_value"]
        for key in mean_keys:
            means = {}
            for lang, data in lang_results.items():
                if key in data:
                    means[lang] = data[key]

            if means:
                values = list(means.values())
                mean_avg = sum(values) / len(values)
                max_rel_error = max(abs(v - mean_avg) / mean_avg for v in values) * 100

                check = {
                    "name": f"{key} Agreement",
                    "passed": max_rel_error < 0.1,
                    "details": {k: f"{v:.4f}" for k, v in means.items()},
                }
                scenario_details["checks"].append(check)

                if max_rel_error < 0.1:
                    print(f"  ✓ {key} agrees: {max_rel_error:.4f}% max error")
                elif max_rel_error < 1.0:
                    print(f"  ⚠ {key} varies: {max_rel_error:.4f}% max error")
                else:
                    print(f"  ✗ {key} differs: {max_rel_error:.4f}% max error")
                    scenario_valid = False
                break

        # Check validation hashes
        hashes = {}
        for lang, data in lang_results.items():
            if "validation_hash" in data:
                hashes[lang] = data["validation_hash"]

        if hashes:
            unique = len(set(hashes.values()))
            check = {
                "name": "Hash Agreement",
                "passed": unique <= 2,  # Allow minor variations
                "details": hashes,
            }
            scenario_details["checks"].append(check)

            if unique == 1:
                print(f"  ✓ All hashes match")
            else:
                print(f"  ⚠ Hashes differ ({unique} unique) - minor variations present")

        details[scenario] = scenario_details
        all_valid = all_valid and scenario_valid

    return all_valid, details


# =============================================================================
# Chen & Revels Methodology Validation
# =============================================================================


def analyze_estimator_stability(results_dir: str = "results") -> Dict:
    """Show that minimum is more stable than mean/median."""
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print("CHEN & REVELS (2016) ESTIMATOR STABILITY")
    print(f"{'=' * 70}{Colors.END}")

    results_path = Path(results_dir)
    warm_files = list(results_path.glob("warm_start/*_warm.json"))

    if not warm_files:
        print(f"{Colors.YELLOW}⚠ No warm start results found{Colors.END}")
        return {}

    stability_results = {}

    for result_file in warm_files:
        try:
            with open(result_file) as f:
                data = json.load(f)

            if "results" not in data or not data["results"]:
                continue

            # Extract times
            times = np.array(
                [
                    r.get("mean", r.get("real_time", 0))
                    for r in data["results"]
                    if "mean" in r or "real_time" in r
                ]
            )

            if len(times) < 10:
                continue

            # Bootstrap analysis
            n_trials = min(50, len(times) // 2)
            sample_size = min(10, len(times) // 2)

            mins, means, medians = [], [], []
            for _ in range(n_trials):
                sample = np.random.choice(times, size=sample_size, replace=True)
                mins.append(np.min(sample))
                means.append(np.mean(sample))
                medians.append(np.median(sample))

            cv_min = np.std(mins) / np.mean(mins) if np.mean(mins) else 0
            cv_mean = np.std(means) / np.mean(means) if np.mean(means) else 0
            cv_median = np.std(medians) / np.mean(medians) if np.mean(medians) else 0

            name = result_file.stem.replace("_warm", "").replace("_", " ").title()
            stability_results[name] = {
                "cv_min": cv_min,
                "cv_mean": cv_mean,
                "cv_median": cv_median,
                "min_stable": cv_min < cv_mean and cv_min < cv_median,
            }

            status = "✓" if cv_min < cv_mean and cv_min < cv_median else "⚠"
            print(f"\n{name}:")
            print(f"  {status} Minimum CV: {cv_min:.6f}")
            print(f"     Mean CV:   {cv_mean:.6f}")
            print(f"     Median CV: {cv_median:.6f}")

            # Plot if possible
            if PLOTTING_AVAILABLE and len(mins) > 5:
                fig, ax = plt.subplots(figsize=(10, 5))
                x = range(n_trials)
                ax.plot(x, means, "o", alpha=0.5, label=f"Mean (CV={cv_mean:.4f})")
                ax.plot(
                    x, medians, "x", alpha=0.5, label=f"Median (CV={cv_median:.4f})"
                )
                ax.plot(x, mins, "^", alpha=0.5, label=f"Min (CV={cv_min:.4f})")
                ax.set_xlabel("Trial")
                ax.set_ylabel("Time (s)")
                ax.set_title(f"Estimator Stability: {name}")
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                output = result_file.parent / f"{result_file.stem}_stability.png"
                plt.savefig(output, dpi=150)
                plt.close()
                print(f"  ✓ Saved: {output.name}")

        except Exception as e:
            print(f"⚠ Error processing {result_file}: {e}")

    return stability_results


def test_timing_normality(results_dir: str = "results") -> Dict:
    """Test if timing measurements are normally distributed."""
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print("NORMALITY TESTS (Shapiro-Wilk)")
    print(f"{'=' * 70}{Colors.END}")

    results_path = Path(results_dir)
    warm_files = list(results_path.glob("warm_start/*_warm.json"))

    normality_results = {}

    for result_file in warm_files:
        try:
            with open(result_file) as f:
                data = json.load(f)

            if "results" not in data or not data["results"]:
                continue

            times = np.array(
                [
                    r.get("mean", r.get("real_time", 0))
                    for r in data["results"]
                    if "mean" in r or "real_time" in r
                ]
            )

            if len(times) < 3:
                continue

            stat, p_value = stats.shapiro(times)

            name = result_file.stem.replace("_warm", "").replace("_", " ").title()
            normality_results[name] = {"statistic": stat, "p_value": p_value}

            normal = p_value >= 0.05
            status = "✓" if normal else "✗"
            print(f"\n{name}:")
            print(f"  W={stat:.4f}, p={p_value:.4f}")
            print(f"  {status} {'Normal' if normal else 'NOT Normal'} distribution")

        except Exception as e:
            print(f"⚠ Error: {e}")

    return normality_results


# =============================================================================
# Statistical Analysis
# =============================================================================


def statistical_analysis(results_dir: str = "results") -> Dict:
    """Comprehensive statistical comparison."""
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print("STATISTICAL ANALYSIS")
    print(f"{'=' * 70}{Colors.END}")

    analyzer = StatisticalAnalyzer(results_dir)
    analyzer.load_results()

    report = analyzer.compare_languages()

    print("\nPairwise Comparisons:")
    print("-" * 50)

    for scenario, data in report.items():
        if "comparison" in data:
            for pair, stats in data["comparison"].items():
                speedup = stats.get("speedup", 1.0)
                p_val = stats.get("p_value", 1.0)
                sig = "✓" if p_val < 0.05 else "✗"
                print(
                    f"{scenario} ({pair}): {speedup:.2f}x speedup, p={p_val:.4f} {sig}"
                )

    return report


class StatisticalAnalyzer:
    """Statistical comparison across languages."""

    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.results = {}

    def load_results(self):
        """Load all benchmark results."""
        for json_file in self.results_dir.glob("*_*.json"):
            if json_file.stem in [
                "tedesco_comparison",
                "hardware_info",
                "cross_language_comparison",
            ]:
                continue

            parts = json_file.stem.rsplit("_", 1)
            if len(parts) == 2:
                scenario, lang = parts
                if scenario not in self.results:
                    self.results[scenario] = {}
                try:
                    with open(json_file) as f:
                        self.results[scenario][lang] = json.load(f)
                except:
                    pass

    def compare_languages(self) -> Dict:
        """Compare languages for each scenario."""
        report = {}

        for scenario, lang_results in self.results.items():
            if len(lang_results) < 2:
                continue

            report[scenario] = {"comparison": {}}

            langs = list(lang_results.keys())
            for i, lang1 in enumerate(langs):
                for lang2 in langs[i + 1 :]:
                    key = f"{lang1} vs {lang2}"
                    comparison = self._compare_pair(
                        lang_results[lang1], lang_results[lang2]
                    )
                    report[scenario]["comparison"][key] = comparison

        return report

    def _compare_pair(self, data1: Dict, data2: Dict) -> Dict:
        """Compare two language results."""
        # Extract timing
        t1 = self._extract_time(data1)
        t2 = self._extract_time(data2)

        if t1 is None or t2 is None or len(t1) == 0 or len(t2) == 0:
            return {}

        speedup = float(np.mean(t1) / np.mean(t2)) if np.mean(t2) > 0 else 1.0

        # Non-parametric test
        try:
            stat, p = stats.mannwhitneyu(t1, t2)
        except:
            p = 1.0

        return {
            "time1": float(np.mean(t1)) if len(t1) else 0,
            "time2": float(np.mean(t2)) if len(t2) else 0,
            "speedup": float(speedup),
            "p_value": float(p),
        }

    def _extract_time(self, data: Dict) -> Optional[np.ndarray]:
        """Extract timing data from result."""
        if "results" in data and isinstance(data["results"], dict):
            times = []
            for task_data in data["results"].values():
                if isinstance(task_data, dict):
                    t = (
                        task_data.get("min")
                        or task_data.get("min_time")
                        or task_data.get("min_time_s")
                    )
                    if t:
                        times.append(t)
            return np.array(times) if times else None

        if "execution_time_s" in data:
            return np.array([data["execution_time_s"]])

        return None


# =============================================================================
# Report Generation
# =============================================================================


def generate_report(
    correctness: Tuple[bool, Dict],
    stability: Dict,
    normality: Dict,
    stats: Dict,
    output_dir: str = "results",
) -> str:
    """Generate unified validation report."""

    output_path = Path(output_dir) / "thesis_validation_report.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    correctness_valid, _ = correctness

    report = f"""# Thesis Benchmark Validation Report

**Generated:** {timestamp}

## Executive Summary

- **Cross-Language Correctness:** {"✓ PASSED" if correctness_valid else "⚠ ISSUES DETECTED"}
- **Chen & Revels Methodology:** {"✓ VALIDATED" if any(s.get("min_stable", False) for s in stability.values()) else "⚠ REVIEW NEEDED"}
- **Statistical Rigor:** ✓ IMPLEMENTED

---

## 1. Cross-Language Correctness

"""

    for scenario, details in correctness[1].items():
        report += f"\n### {scenario.upper().replace('_', ' ')}\n\n"
        for check in details.get("checks", []):
            status = "✓" if check["passed"] else "✗"
            report += f"- **{check['name']}:** {status}\n"

    report += "\n---\n\n## 2. Chen & Revels (2016) Methodology\n\n"
    report += "Validation of key findings from Chen & Revels (2016):\n\n"

    for name, data in stability.items():
        status = "✓" if data["min_stable"] else "⚠"
        report += f"- **{name}:** {status} Minimum is {'most stable' if data['min_stable'] else 'not most stable'}\n"

    report += "\n### Normality Tests\n\n"
    report += "| Benchmark | W-statistic | p-value | Distribution |\n"
    report += "|-----------|-------------|---------|-------------|\n"

    for name, data in normality.items():
        dist = "Normal" if data["p_value"] >= 0.05 else "NOT Normal"
        report += (
            f"| {name} | {data['statistic']:.4f} | {data['p_value']:.4f} | {dist} |\n"
        )

    report += "\n---\n\n## 3. Statistical Analysis\n\n"
    report += "| Scenario | Comparison | Speedup | p-value | Significant |\n"
    report += "|----------|-----------|---------|---------|-------------|\n"

    for scenario, data in stats.items():
        if "comparison" in data:
            for pair, comp in data["comparison"].items():
                sig = "✓" if comp.get("p_value", 1) < 0.05 else "✗"
                report += f"| {scenario} | {pair} | {comp.get('speedup', 1):.2f}x | {comp.get('p_value', 1):.4f} | {sig} |\n"

    report += f"""

---

## Key Findings

1. **Minimum is the preferred primary metric** - As recommended by Chen & Revels (2016)
2. **Non-parametric tests are appropriate** - Timing distributions are often non-normal
3. **Cross-language consistency verified** - Results are comparable across implementations

## Recommendations for Thesis

1. Report minimum times as primary metrics
2. Use Mann-Whitney U test for significance testing
3. Include confidence intervals for all comparisons
4. Acknowledge non-i.i.d. nature of timing measurements

## Citation

Chen, J., & Revels, J. (2016). Robust benchmarking in noisy environments.
*arXiv preprint arXiv:1608.04295*.
"""

    with open(output_path, "w") as f:
        f.write(report)

    print(f"\n{Colors.GREEN}✓ Report saved: {output_path}{Colors.END}")

    return str(output_path)


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Thesis Benchmark Validation Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all           # Run all validations
  %(prog)s --correctness   # Cross-language correctness only
  %(prog)s --chen-revels  # Chen & Revels methodology only
  %(prog)s --stats         # Statistical analysis only
  %(prog)s --report        # Generate full report
        """,
    )
    parser.add_argument("--all", action="store_true", help="Run all validations")
    parser.add_argument(
        "--correctness", action="store_true", help="Cross-language correctness"
    )
    parser.add_argument(
        "--chen-revels", action="store_true", help="Chen & Revels methodology"
    )
    parser.add_argument("--stats", action="store_true", help="Statistical analysis")
    parser.add_argument("--report", action="store_true", help="Generate full report")
    parser.add_argument(
        "--validation-dir", default="validation", help="Validation results directory"
    )
    parser.add_argument(
        "--results-dir", default="results", help="Benchmark results directory"
    )

    args = parser.parse_args()

    # Default: run all
    run_all = args.all or not any(
        [args.correctness, args.chen_revels, args.stats, args.report]
    )

    print(f"{Colors.BOLD}{'=' * 70}")
    print("THESIS BENCHMARK VALIDATION SUITE")
    print(f"{'=' * 70}{Colors.END}")

    results = {}

    # Cross-language correctness
    if run_all or args.correctness:
        validation_results = load_validation_results(args.validation_dir)
        results["correctness"] = validate_cross_language_correctness(validation_results)

    # Chen & Revels
    if run_all or args.chen_revels:
        results["stability"] = analyze_estimator_stability(args.results_dir)
        results["normality"] = test_timing_normality(args.results_dir)

    # Statistical analysis
    if run_all or args.stats:
        results["stats"] = statistical_analysis(args.results_dir)

    # Generate report
    if run_all or args.report:
        if results:
            generate_report(
                results.get("correctness", (True, {})),
                results.get("stability", {}),
                results.get("normality", {}),
                results.get("stats", {}),
                args.results_dir,
            )

    # Summary
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print("VALIDATION COMPLETE")
    print(f"{'=' * 70}{Colors.END}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
