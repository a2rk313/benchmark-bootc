#!/usr/bin/env python3
"""
================================================================================
BENCHMARK RESULTS VISUALIZER
================================================================================
Creates charts and graphs for easy understanding of results.

Usage:
    python tools/visualize_benchmarks.py              # All charts
    python tools/visualize_benchmarks.py --speedup   # Speedup comparison
    python tools/visualize_benchmarks.py --heatmap   # Language heatmap
    python tools/visualize_benchmarks.py --summary   # Quick summary chart
================================================================================
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("⚠ matplotlib not available. Install with: uv pip install matplotlib")

# Color palette (colorblind-friendly)
COLORS = {
    "python": "#E69F00",  # Orange
    "julia": "#0072B2",  # Blue
    "r": "#009E73",  # Green
    "python_julia": "#D55E00",  # Dark orange
}

RESULTS_DIR = Path("results")
VALIDATION_DIR = Path("validation")


def load_json(filepath: Path) -> Optional[dict]:
    """Load JSON file safely."""
    try:
        with open(filepath) as f:
            return json.load(f)
    except:
        return None


def get_all_results() -> Dict:
    """Load all benchmark results."""
    results = {}

    # Load from results/ directory
    for json_file in RESULTS_DIR.glob("*_python.json"):
        if "tedesco" in json_file.name:
            continue
        name = json_file.stem.replace("_python", "")
        if name not in results:
            results[name] = {}
        if "python" not in results[name]:
            results[name]["python"] = load_json(json_file)

    for json_file in RESULTS_DIR.glob("*_julia.json"):
        name = json_file.stem.replace("_julia", "")
        if name not in results:
            results[name] = {}
        if "julia" not in results[name]:
            results[name]["julia"] = load_json(json_file)

    for json_file in RESULTS_DIR.glob("*_r.json"):
        name = json_file.stem.replace("_r", "")
        if name not in results:
            results[name] = {}
        if "r" not in results[name]:
            results[name]["r"] = load_json(json_file)

    # Load validation results (these override if present)
    for json_file in VALIDATION_DIR.glob("*_results.json"):
        name = json_file.stem.replace("_results", "")
        lang = None
        for suffix in ["_python", "_julia", "_r"]:
            if suffix in name:
                lang = suffix.replace("_", "")
                name = name.replace(suffix, "")
                break

        if not lang:
            continue

        if name not in results:
            results[name] = {}
        if lang not in results[name]:
            results[name][lang] = load_json(json_file)

    return results


def create_summary_chart(results: Dict):
    """Create a quick summary bar chart showing fastest language per scenario."""
    if not PLOTLY_AVAILABLE:
        print("⚠ Cannot create chart - matplotlib not installed")
        return

    scenarios = []
    fastest = []
    times = []

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        min_time = float("inf")
        min_lang = None

        for lang, data in lang_results.items():
            if data and isinstance(data, dict):
                res = data.get("results", {})

                # Check if we have execution_time_s at top level (validation files)
                exec_time = data.get("execution_time_s")
                if exec_time and not res:
                    # No results dict, use execution_time_s directly
                    if exec_time < min_time:
                        min_time = exec_time
                        min_lang = lang
                elif res:
                    for task_name, task_data in res.items():
                        if isinstance(task_data, dict):
                            t = (
                                task_data.get("min_time_s")
                                or task_data.get("min_time")
                                or task_data.get("execution_time_s")
                                or task_data.get("min")
                            )
                            if t and t < min_time:
                                min_time = t
                                min_lang = lang

        if min_lang:
            scenarios.append(scenario_name.replace("_", " ").title())
            fastest.append(min_lang)
            times.append(min_time)

    if not scenarios:
        print("⚠ No data found for summary chart")
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(scenarios))
    colors = [COLORS.get(l, "#888888") for l in fastest]

    bars = ax.bar(x, times, color=colors, alpha=0.8, edgecolor="black")

    # Add language labels
    for i, (bar, lang) in enumerate(zip(bars, fastest)):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{lang.upper()}\n({height:.3f}s)",
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )

    ax.set_xlabel("Scenario", fontweight="bold")
    ax.set_ylabel("Fastest Time (seconds)", fontweight="bold")
    ax.set_title(
        "Benchmark Results Summary: Fastest Language per Scenario", fontweight="bold"
    )
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    ax.grid(axis="y", alpha=0.3)

    # Legend
    legend_patches = [
        mpatches.Patch(color=COLORS[l], label=l.upper()) for l in set(fastest)
    ]
    ax.legend(handles=legend_patches, loc="upper right")

    plt.tight_layout()
    output_file = RESULTS_DIR / "figures" / "summary_chart.png"
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"✓ Saved: {output_file}")
    plt.close()


def create_speedup_chart(results: Dict):
    """Create speedup comparison chart (Julia vs Python)."""
    if not PLOTLY_AVAILABLE:
        return

    scenarios = []
    speedups = []

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        py_time = None
        jl_time = None

        for lang, data in lang_results.items():
            if data and isinstance(data, dict):
                res = data.get("results", {})

                exec_time = data.get("execution_time_s")
                if exec_time and not res:
                    t = exec_time
                    if lang == "python":
                        py_time = min(py_time or float("inf"), t)
                    elif lang == "julia":
                        jl_time = min(jl_time or float("inf"), t)
                elif res:
                    for task_name, task_data in res.items():
                        if isinstance(task_data, dict):
                            t = (
                                task_data.get("min_time_s")
                                or task_data.get("min_time")
                                or task_data.get("execution_time_s")
                                or task_data.get("min")
                            )
                            if t:
                                if lang == "python":
                                    py_time = min(py_time or float("inf"), t)
                                elif lang == "julia":
                                    jl_time = min(jl_time or float("inf"), t)

        if py_time and jl_time and py_time > 0:
            scenarios.append(scenario_name.replace("_", " ").title())
            speedups.append(py_time / jl_time)

    if not scenarios:
        print("⚠ No data found for speedup chart")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(scenarios))
    bar_colors = ["#0072B2" if s > 1 else "#E69F00" for s in speedups]

    bars = ax.bar(x, speedups, color=bar_colors, alpha=0.8, edgecolor="black")

    ax.axhline(
        y=1.0, color="red", linestyle="--", linewidth=2, label="Equal Performance"
    )

    for i, (bar, speedup) in enumerate(zip(bars, speedups)):
        height = bar.get_height()
        label = f"{speedup:.2f}×"
        if speedup > 1:
            label += "\n(Julia faster)"
        else:
            label += "\n(Python faster)"
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            label,
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax.set_xlabel("Scenario", fontweight="bold")
    ax.set_ylabel("Speedup (× faster)", fontweight="bold")
    ax.set_title("Julia vs Python: Speedup Comparison", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    output_file = RESULTS_DIR / "figures" / "speedup_chart.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"✓ Saved: {output_file}")
    plt.close()


def create_language_heatmap(results: Dict):
    """Create heatmap showing performance across scenarios and languages."""
    if not PLOTLY_AVAILABLE:
        return

    scenarios = []
    langs = ["python", "julia", "r"]

    # Collect all min times
    data_matrix = []
    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        row = []
        for lang in langs:
            min_time = float("inf")
            if lang in lang_results:
                data = lang_results[lang]
                if data and isinstance(data, dict):
                    res = data.get("results", {})
                    exec_time = data.get("execution_time_s")
                    if exec_time and not res:
                        min_time = exec_time
                    elif res:
                        for task_data in res.values():
                            if isinstance(task_data, dict):
                                t = (
                                    task_data.get("min_time_s")
                                    or task_data.get("min_time")
                                    or task_data.get("execution_time_s")
                                    or task_data.get("min")
                                )
                                if t:
                                    min_time = min(min_time, t)
            row.append(min_time if min_time < float("inf") else None)

        if any(row):
            scenarios.append(scenario_name.replace("_", " ").title())
            data_matrix.append(row)

    if not data_matrix:
        print("⚠ No data found for heatmap")
        return

    data_matrix = np.array(data_matrix, dtype=float)

    # Replace None with nan for proper handling
    data_matrix = np.where(data_matrix == None, np.nan, data_matrix)

    # Normalize by row (scenario) to show relative performance
    with np.errstate(all="ignore"):
        row_min = np.nanmin(data_matrix, axis=1, keepdims=True)
        row_min = np.where(row_min == 0, 1, row_min)  # Avoid division by zero
        normalized = data_matrix / row_min

    fig, ax = plt.subplots(figsize=(8, 10))

    im = ax.imshow(normalized, cmap="RdYlGn_r", aspect="auto", vmin=1, vmax=5)

    ax.set_xticks(np.arange(len(langs)))
    ax.set_xticklabels([l.upper() for l in langs])
    ax.set_yticks(np.arange(len(scenarios)))
    ax.set_yticklabels(scenarios)

    # Add text annotations
    for i in range(len(scenarios)):
        for j in range(len(langs)):
            if not np.isnan(data_matrix[i, j]):
                text = f"{data_matrix[i, j]:.3f}s\n({normalized[i, j]:.1f}×)"
                color = "white" if normalized[i, j] > 2 else "black"
                ax.text(j, i, text, ha="center", va="center", fontsize=7, color=color)

    ax.set_title(
        "Relative Performance Heatmap\n(× slower than fastest)", fontweight="bold"
    )

    plt.colorbar(im, ax=ax, label="Relative slowdown factor")
    plt.tight_layout()

    output_file = RESULTS_DIR / "figures" / "performance_heatmap.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"✓ Saved: {output_file}")
    plt.close()


def create_quick_stats_table(results: Dict):
    """Print quick stats table to console."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS QUICK VIEW")
    print("=" * 80)

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        print(f"\n{scenario_name.upper().replace('_', ' ')}")
        print("-" * 40)

        for lang in ["python", "julia", "r"]:
            if lang in lang_results:
                data = lang_results[lang]
                if data and isinstance(data, dict):
                    res = data.get("results", {})

                    min_time = float("inf")

                    # Check for execution_time_s at top level (validation files)
                    exec_time = data.get("execution_time_s")
                    if exec_time and not res:
                        min_time = exec_time
                    elif res:
                        for task_data in res.values():
                            if isinstance(task_data, dict):
                                t = (
                                    task_data.get("min_time_s")
                                    or task_data.get("min_time")
                                    or task_data.get("execution_time_s")
                                    or task_data.get("min")
                                )
                                if t:
                                    min_time = min(min_time, t)

                    if min_time < float("inf"):
                        print(f"  {lang.upper():8}: {min_time:.4f}s")


def generate_all_charts():
    """Generate all visualization charts."""
    print("=" * 70)
    print("GENERATING BENCHMARK VISUALIZATIONS")
    print("=" * 70)

    results = get_all_results()

    if not results:
        print("⚠ No results found. Run benchmarks first!")
        return

    print(f"✓ Loaded {len(results)} scenarios")

    # Create output directory
    (RESULTS_DIR / "figures").mkdir(exist_ok=True)

    print("\n📊 Creating charts...")

    create_quick_stats_table(results)
    create_summary_chart(results)
    create_speedup_chart(results)
    create_language_heatmap(results)

    print("\n" + "=" * 70)
    print("✓ VISUALIZATIONS COMPLETE")
    print("=" * 70)
    print(f"\nCharts saved to: {RESULTS_DIR / 'figures'}")
    print("  - summary_chart.png      (Quick overview)")
    print("  - speedup_chart.png      (Julia vs Python)")
    print("  - performance_heatmap.png (All scenarios)")


def main():
    parser = argparse.ArgumentParser(description="Visualize benchmark results")
    parser.add_argument("--all", action="store_true", help="Generate all charts")
    parser.add_argument("--summary", action="store_true", help="Summary chart only")
    parser.add_argument("--speedup", action="store_true", help="Speedup chart only")
    parser.add_argument("--heatmap", action="store_true", help="Heatmap only")
    parser.add_argument("--stats", action="store_true", help="Console stats only")

    args = parser.parse_args()

    results = get_all_results()

    if not results:
        print("⚠ No results found. Run benchmarks first!")
        sys.exit(1)

    print(f"✓ Loaded {len(results)} scenarios\n")

    if args.stats:
        create_quick_stats_table(results)
    elif args.summary:
        create_summary_chart(results)
    elif args.speedup:
        create_speedup_chart(results)
    elif args.heatmap:
        create_language_heatmap(results)
    else:
        generate_all_charts()


if __name__ == "__main__":
    main()
