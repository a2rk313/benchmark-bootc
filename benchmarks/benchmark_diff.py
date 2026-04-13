#!/usr/bin/env python3
"""
Benchmark Diff Tool - Compare Results Against Baseline

Compares current benchmark results against a baseline and generates
a detailed diff report showing:
- Performance regressions
- Performance improvements
- New benchmarks added
- Benchmarks removed
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np


@dataclass
class BenchmarkDiff:
    benchmark: str
    language: str
    baseline_time: float
    current_time: float
    change_pct: float
    is_regression: bool
    is_improvement: bool
    status: str


class BenchmarkDiffer:
    REGRESSION_THRESHOLD = 5.0
    IMPROVEMENT_THRESHOLD = -5.0
    
    def __init__(self, baseline_dir: str, current_dir: str):
        self.baseline_dir = Path(baseline_dir)
        self.current_dir = Path(current_dir)
        self.baseline_results: Dict[str, Dict] = {}
        self.current_results: Dict[str, Dict] = {}
        self.diffs: List[BenchmarkDiff] = []
    
    def load_results(self, results_dir: Path) -> Dict[str, Dict]:
        """Load all JSON results from a directory."""
        results = {}
        
        for json_file in results_dir.rglob("*.json"):
            if "validation" in str(json_file):
                continue
            
            try:
                with open(json_file) as f:
                    data = json.load(f)
                
                key = self._extract_key(json_file, data)
                results[key] = data
            except Exception as e:
                print(f"Warning: Could not load {json_file}: {e}")
        
        return results
    
    def _extract_key(self, file_path: Path, data: Any) -> str:
        """Extract a unique key for a result file."""
        name = data.get("name", data.get("benchmark", file_path.stem))
        language = data.get("language", "unknown")
        return f"{language}_{name}"
    
    def run(self) -> List[BenchmarkDiff]:
        """Run the diff analysis."""
        print("Loading baseline results...")
        self.baseline_results = self.load_results(self.baseline_dir)
        
        print("Loading current results...")
        self.current_results = self.load_results(self.current_dir)
        
        all_keys = set(self.baseline_results.keys()) | set(self.current_results.keys())
        
        for key in all_keys:
            baseline = self.baseline_results.get(key)
            current = self.current_results.get(key)
            
            if baseline is None:
                diff = self._create_new_benchmark(key, current)
            elif current is None:
                diff = self._create_removed_benchmark(key, baseline)
            else:
                diff = self._compare_benchmarks(key, baseline, current)
            
            self.diffs.append(diff)
        
        return self.diffs
    
    def _compare_benchmarks(
        self,
        key: str,
        baseline: Dict,
        current: Dict,
    ) -> BenchmarkDiff:
        """Compare two benchmark results."""
        baseline_time = baseline.get("min_time", baseline.get("min_time_s", 0))
        current_time = current.get("min_time", current.get("min_time_s", 0))
        
        if baseline_time == 0:
            change_pct = 0.0
        else:
            change_pct = ((current_time - baseline_time) / baseline_time) * 100
        
        is_regression = change_pct > self.REGRESSION_THRESHOLD
        is_improvement = change_pct < self.IMPROVEMENT_THRESHOLD
        
        if is_regression:
            status = "REGRESSION"
        elif is_improvement:
            status = "IMPROVEMENT"
        else:
            status = "STABLE"
        
        language = current.get("language", key.split("_")[0] if "_" in key else "unknown")
        name = current.get("name", current.get("benchmark", key))
        
        return BenchmarkDiff(
            benchmark=name,
            language=language,
            baseline_time=baseline_time,
            current_time=current_time,
            change_pct=change_pct,
            is_regression=is_regression,
            is_improvement=is_improvement,
            status=status,
        )
    
    def _create_new_benchmark(self, key: str, current: Dict) -> BenchmarkDiff:
        """Benchmark that appears in current but not in baseline."""
        return BenchmarkDiff(
            benchmark=key,
            language=current.get("language", "unknown"),
            baseline_time=0.0,
            current_time=current.get("min_time", 0),
            change_pct=0.0,
            is_regression=False,
            is_improvement=False,
            status="NEW",
        )
    
    def _create_removed_benchmark(self, key: str, baseline: Dict) -> BenchmarkDiff:
        """Benchmark that was in baseline but not in current."""
        return BenchmarkDiff(
            benchmark=key,
            language=baseline.get("language", "unknown"),
            baseline_time=baseline.get("min_time", 0),
            current_time=0.0,
            change_pct=-100.0,
            is_regression=True,
            is_improvement=False,
            status="REMOVED",
        )
    
    def generate_markdown_report(self) -> str:
        """Generate a markdown report of the diff."""
        lines = [
            "# Benchmark Diff Report",
            f"\nGenerated: {datetime.now().isoformat()}",
            f"\nBaseline: `{self.baseline_dir}`",
            f"Current: `{self.current_dir}`",
            "\n---",
        ]
        
        regressions = [d for d in self.diffs if d.is_regression]
        improvements = [d for d in self.diffs if d.is_improvement]
        new = [d for d in self.diffs if d.status == "NEW"]
        removed = [d for d in self.diffs if d.status == "REMOVED"]
        stable = [d for d in self.diffs if d.status == "STABLE"]
        
        lines.append(f"\n## Summary\n")
        lines.append(f"- Total benchmarks: {len(self.diffs)}")
        lines.append(f"- Regressions: {len(regressions)}")
        lines.append(f"- Improvements: {len(improvements)}")
        lines.append(f"- New: {len(new)}")
        lines.append(f"- Removed: {len(removed)}")
        lines.append(f"- Stable: {len(stable)}")
        
        if regressions:
            lines.append("\n## Regressions\n")
            lines.append("| Benchmark | Language | Baseline | Current | Change |")
            lines.append("|-----------|----------|----------|---------|--------|")
            for d in sorted(regressions, key=lambda x: -x.change_pct):
                lines.append(
                    f"| {d.benchmark} | {d.language} | "
                    f"{d.baseline_time:.4f}s | {d.current_time:.4f}s | "
                    f"+{d.change_pct:.1f}% |"
                )
        
        if improvements:
            lines.append("\n## Improvements\n")
            lines.append("| Benchmark | Language | Baseline | Current | Change |")
            lines.append("|-----------|----------|----------|---------|--------|")
            for d in sorted(improvements, key=lambda x: x.change_pct):
                lines.append(
                    f"| {d.benchmark} | {d.language} | "
                    f"{d.baseline_time:.4f}s | {d.current_time:.4f}s | "
                    f"{d.change_pct:.1f}% |"
                )
        
        if new:
            lines.append("\n## New Benchmarks\n")
            for d in new:
                lines.append(f"- {d.benchmark} ({d.language}): {d.current_time:.4f}s")
        
        if removed:
            lines.append("\n## Removed Benchmarks\n")
            for d in removed:
                lines.append(f"- {d.benchmark} ({d.language}): was {d.baseline_time:.4f}s")
        
        return "\n".join(lines)
    
    def export_json(self, output_path: str):
        """Export diff results as JSON."""
        data = {
            "baseline_dir": str(self.baseline_dir),
            "current_dir": str(self.current_dir),
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total": len(self.diffs),
                "regressions": sum(1 for d in self.diffs if d.is_regression),
                "improvements": sum(1 for d in self.diffs if d.is_improvement),
                "new": sum(1 for d in self.diffs if d.status == "NEW"),
                "removed": sum(1 for d in self.diffs if d.status == "REMOVED"),
            },
            "diffs": [asdict(d) for d in self.diffs],
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Diff exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Compare benchmarks against baseline")
    parser.add_argument("baseline", help="Baseline results directory")
    parser.add_argument("current", help="Current results directory")
    parser.add_argument("--output", "-o", help="Output file (markdown or JSON)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="Output format")
    
    args = parser.parse_args()
    
    differ = BenchmarkDiffer(args.baseline, args.current)
    differ.run()
    
    if args.format == "markdown":
        report = differ.generate_markdown_report()
        print(report)
        
        if args.output:
            with open(args.output, "w") as f:
                f.write(report)
            print(f"\nReport saved to {args.output}")
    else:
        differ.export_json(args.output or "benchmark_diff.json")
    
    regressions = sum(1 for d in differ.diffs if d.is_regression)
    return 0 if regressions == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
