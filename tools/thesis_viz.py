#!/usr/bin/env python3
"""
================================================================================
Thesis Benchmark Visualization Suite
================================================================================

Unified visualization for publication-quality figures.

Usage:
    python tools/thesis_viz.py --all        # All visualizations
    python tools/thesis_viz.py --summary    # Summary chart
    python tools/thesis_viz.py --heatmap    # Performance heatmap
    python tools/thesis_viz.py --speedup    # Speedup comparison
    python tools/thesis_viz.py --stats      # Statistical plots
    python tools/thesis_viz.py --report      # Full HTML report

================================================================================
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import seaborn as sns

    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print(
        "⚠ matplotlib/seaborn not available. Install with: uv pip install matplotlib seaborn"
    )

try:
    from scipy import stats

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# =============================================================================
# Configuration
# =============================================================================

RESULTS_DIR = Path("results")
VALIDATION_DIR = Path("validation")
FIGURES_DIR = RESULTS_DIR / "figures"

COLORS = {
    "python": "#E69F00",  # Orange
    "julia": "#0072B2",  # Blue
    "r": "#009E73",  # Green
}

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
    }
)


# =============================================================================
# Data Loading
# =============================================================================


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

    for suffix in ["python", "julia", "r"]:
        for json_file in RESULTS_DIR.glob(f"*_{suffix}.json"):
            if any(
                x in json_file.name for x in ["tedesco", "hardware", "cross_language"]
            ):
                continue
            name = json_file.stem.replace(f"_{suffix}", "")
            if name not in results:
                results[name] = {}
            results[name][suffix] = load_json(json_file)

    for json_file in VALIDATION_DIR.glob("*_results.json"):
        name = json_file.stem.replace("_results", "")
        lang = None
        for suffix in ["_python", "_julia", "_r"]:
            if suffix in name:
                lang = suffix.replace("_", "")
                name = name.replace(suffix, "")
                break
        if lang:
            if name not in results:
                results[name] = {}
            results[name][lang] = load_json(json_file)

    return results


def extract_min_time(data: dict) -> Optional[float]:
    """Extract minimum time from result data."""
    if not data:
        return None

    if "results" in data and data["results"]:
        times = []
        for task_data in data["results"].values():
            if isinstance(task_data, dict):
                t = (
                    task_data.get("min")
                    or task_data.get("min_time")
                    or task_data.get("min_time_s")
                    or task_data.get("execution_time_s")
                )
                if t:
                    times.append(t)
        return min(times) if times else None

    return data.get("execution_time_s")


# =============================================================================
# Visualizations
# =============================================================================


def create_summary_chart(results: Dict):
    """Bar chart showing fastest language per scenario."""
    if not PLOTTING_AVAILABLE:
        return

    FIGURES_DIR.mkdir(exist_ok=True)

    scenarios = []
    fastest = []
    times = []

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        min_time = float("inf")
        min_lang = None

        for lang, data in lang_results.items():
            t = extract_min_time(data)
            if t and t < min_time:
                min_time = t
                min_lang = lang

        if min_lang:
            scenarios.append(scenario_name.replace("_", " ").title())
            fastest.append(min_lang)
            times.append(min_time)

    if not scenarios:
        print("⚠ No data for summary chart")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(scenarios))
    colors = [COLORS.get(l, "#888888") for l in fastest]

    bars = ax.bar(x, times, color=colors, alpha=0.8, edgecolor="black")

    for bar, lang, t in zip(bars, fastest, times):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{lang.upper()}\n({t:.3f}s)",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax.set_xlabel("Scenario")
    ax.set_ylabel("Fastest Time (seconds)")
    ax.set_title("Benchmark Results Summary: Fastest Language per Scenario")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    ax.grid(axis="y", alpha=0.3)

    legend_patches = [
        mpatches.Patch(color=COLORS[l], label=l.upper()) for l in set(fastest)
    ]
    ax.legend(handles=legend_patches, loc="upper right")

    plt.tight_layout()
    output = FIGURES_DIR / "summary_chart.png"
    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✓ Saved: {output}")


def create_speedup_chart(results: Dict):
    """Julia vs Python speedup comparison."""
    if not PLOTTING_AVAILABLE:
        return

    scenarios = []
    speedups = []

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        py_time = None
        jl_time = None

        for lang, data in lang_results.items():
            t = extract_min_time(data)
            if t:
                if lang == "python":
                    py_time = min(py_time or float("inf"), t)
                elif lang == "julia":
                    jl_time = min(jl_time or float("inf"), t)

        if py_time and jl_time and py_time > 0:
            scenarios.append(scenario_name.replace("_", " ").title())
            speedups.append(py_time / jl_time)

    if not scenarios:
        print("⚠ No data for speedup chart")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(scenarios))
    bar_colors = ["#0072B2" if s > 1 else "#E69F00" for s in speedups]

    ax.bar(x, speedups, color=bar_colors, alpha=0.8, edgecolor="black")
    ax.axhline(
        y=1.0, color="red", linestyle="--", linewidth=2, label="Equal Performance"
    )

    for i, speedup in enumerate(speedups):
        label = (
            f"{speedup:.2f}×\n({'Julia faster' if speedup > 1 else 'Python faster'})"
        )
        ax.text(i, speedup, label, ha="center", va="bottom", fontsize=8)

    ax.set_xlabel("Scenario")
    ax.set_ylabel("Speedup (× faster)")
    ax.set_title("Julia vs Python: Speedup Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    output = FIGURES_DIR / "speedup_chart.png"
    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✓ Saved: {output}")


def create_heatmap(results: Dict):
    """Performance heatmap across scenarios and languages."""
    if not PLOTTING_AVAILABLE:
        return

    scenarios = []
    langs = ["python", "julia", "r"]

    data_matrix = []
    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        row = []
        for lang in langs:
            t = extract_min_time(lang_results.get(lang))
            row.append(t if t else np.nan)

        if not all(np.isnan(r) for r in row):
            scenarios.append(scenario_name.replace("_", " ").title())
            data_matrix.append(row)

    if not data_matrix:
        print("⚠ No data for heatmap")
        return

    data_matrix = np.array(data_matrix, dtype=float)

    with np.errstate(all="ignore"):
        row_min = np.nanmin(data_matrix, axis=1, keepdims=True)
        row_min = np.where(row_min == 0, 1, row_min)
        normalized = data_matrix / row_min

    fig, ax = plt.subplots(figsize=(8, 10))
    im = ax.imshow(normalized, cmap="RdYlGn_r", aspect="auto", vmin=1, vmax=5)

    ax.set_xticks(np.arange(len(langs)))
    ax.set_xticklabels([l.upper() for l in langs])
    ax.set_yticks(np.arange(len(scenarios)))
    ax.set_yticklabels(scenarios)

    for i in range(len(scenarios)):
        for j in range(len(langs)):
            val = data_matrix[i, j]
            if not np.isnan(val):
                text = f"{val:.3f}\n({normalized[i, j]:.1f}×)"
                color = "white" if normalized[i, j] > 3 else "black"
                ax.text(j, i, text, ha="center", va="center", color=color, fontsize=8)

    ax.set_title(
        "Normalized Performance Heatmap\n(Values = minutes, × = relative to fastest)"
    )
    plt.colorbar(im, ax=ax, label="Relative Performance")

    plt.tight_layout()
    output = FIGURES_DIR / "performance_heatmap.png"
    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✓ Saved: {output}")


def create_violin_plots(results: Dict):
    """Violin plots showing timing distributions."""
    if not PLOTTING_AVAILABLE:
        return

    all_data = []
    labels = []

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        for lang, data in lang_results.items():
            times = []
            if "results" in data and data["results"]:
                for task_data in data["results"].values():
                    if isinstance(task_data, dict):
                        t = task_data.get("min") or task_data.get("min_time")
                        if t:
                            times.append(t)

            if times:
                all_data.append(times)
                labels.append(f"{scenario_name[:15]}\n{lang.upper()}")

    if not all_data:
        print("⚠ No data for violin plots")
        return

    fig, ax = plt.subplots(figsize=(14, 6))

    parts = ax.violinplot(
        all_data, positions=range(len(all_data)), showmeans=True, showmedians=True
    )

    for i, pc in enumerate(parts["bodies"]):
        lang = labels[i].split("\n")[1].lower()
        pc.set_facecolor(COLORS.get(lang, "#888888"))
        pc.set_alpha(0.7)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Performance Distribution by Scenario and Language")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    output = FIGURES_DIR / "violin_plots.png"
    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✓ Saved: {output}")


def create_comparison_table(results: Dict) -> str:
    """Generate LaTeX comparison table."""
    lines = []
    lines.append("\\begin{table}[h]")
    lines.append("\\centering")
    lines.append("\\caption{Benchmark Results Comparison}")
    lines.append("\\begin{tabular}{l" + "r" * 3 + "}")
    lines.append("\\hline")
    lines.append("Scenario & Python & Julia & R \\\\")
    lines.append("\\hline")

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        row = [scenario_name.replace("_", " ").title()]
        for lang in ["python", "julia", "r"]:
            t = extract_min_time(lang_results.get(lang))
            row.append(f"{t:.4f}" if t else "-")
        lines.append(" & ".join(row) + " \\\\")

    lines.append("\\hline")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def print_summary(results: Dict):
    """Print console summary."""
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS QUICK VIEW")
    print("=" * 70)

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue

        print(f"\n{scenario_name.upper().replace('_', ' ')}")
        print("-" * 40)

        for lang in ["python", "julia", "r"]:
            data = lang_results.get(lang)
            if data:
                t = extract_min_time(data)
                if t:
                    print(f"  {lang.upper():8}: {t:.4f}s")


def generate_html_report(results: Dict):
    """Generate HTML report with all visualizations."""
    if not PLOTTING_AVAILABLE:
        return

    html = (
        """<!DOCTYPE html>
<html>
<head>
    <title>Thesis Benchmark Results</title>
    <style>
        body { font-family: sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        img { max-width: 100%; margin: 20px 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .card { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f5f5f5; }
    </style>
</head>
<body>
    <h1>Thesis Benchmark Results</h1>
    <p>Generated: """
        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        + """</p>
    
    <div class="grid">
"""
    )

    for fig in [
        "summary_chart.png",
        "speedup_chart.png",
        "performance_heatmap.png",
        "violin_plots.png",
    ]:
        path = FIGURES_DIR / fig
        if path.exists():
            html += f'        <div class="card"><h2>{fig.replace("_", " ").title()}</h2><img src="{fig}" alt="{fig}"></div>\n'

    html += """    </div>
    
    <h2>Data Summary</h2>
    <pre>"""

    for scenario_name, lang_results in sorted(results.items()):
        if not lang_results:
            continue
        html += f"\n{scenario_name.upper()}\n"
        for lang in ["python", "julia", "r"]:
            data = lang_results.get(lang)
            if data:
                t = extract_min_time(data)
                if t:
                    html += f"  {lang.upper()}: {t:.4f}s\n"

    html += """    </pre>
</body>
</html>"""

    output = RESULTS_DIR / "benchmark_report.html"
    output.write_text(html)
    print(f"✓ Saved: {output}")


def generate_latex_table(results: Dict):
    """Generate LaTeX table."""
    output = RESULTS_DIR / "benchmark_results.tex"
    output.write_text(create_comparison_table(results))
    print(f"✓ Saved: {output}")


# =============================================================================
# Main
# =============================================================================

from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Thesis Benchmark Visualization")
    parser.add_argument(
        "--all", action="store_true", help="Generate all visualizations"
    )
    parser.add_argument("--summary", action="store_true", help="Summary chart")
    parser.add_argument("--heatmap", action="store_true", help="Performance heatmap")
    parser.add_argument("--speedup", action="store_true", help="Speedup comparison")
    parser.add_argument("--stats", action="store_true", help="Statistical plots")
    parser.add_argument("--report", action="store_true", help="HTML report")
    parser.add_argument("--latex", action="store_true", help="LaTeX table")
    parser.add_argument("--results-dir", default="results", help="Results directory")

    args = parser.parse_args()

    if not PLOTTING_AVAILABLE:
        print(
            "⚠ matplotlib not available. Install with: uv pip install matplotlib seaborn"
        )
        return 1

    run_all = args.all or not any(
        [args.summary, args.heatmap, args.speedup, args.stats, args.report, args.latex]
    )

    global RESULTS_DIR, VALIDATION_DIR, FIGURES_DIR
    RESULTS_DIR = Path(args.results_dir)
    VALIDATION_DIR = Path("validation")
    FIGURES_DIR = RESULTS_DIR / "figures"
    FIGURES_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("THESIS BENCHMARK VISUALIZATION")
    print("=" * 70)

    results = get_all_results()
    print(f"✓ Loaded {len(results)} scenarios")

    print("\n📊 Generating visualizations...")

    if run_all or args.summary:
        create_summary_chart(results)
    if run_all or args.speedup:
        create_speedup_chart(results)
    if run_all or args.heatmap:
        create_heatmap(results)
    if run_all or args.stats:
        create_violin_plots(results)
    if run_all or args.report:
        generate_html_report(results)
    if run_all or args.latex:
        generate_latex_table(results)

    if run_all or not any(
        [args.summary, args.heatmap, args.speedup, args.stats, args.report, args.latex]
    ):
        print_summary(results)

    print("\n" + "=" * 70)
    print(f"✓ Visualizations saved to: {FIGURES_DIR}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
