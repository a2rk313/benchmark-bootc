#!/usr/bin/env python3
"""
Trend Analysis Module - Track Performance Over Commits

Analyzes benchmark performance trends across git commits to identify:
- Long-term performance degradation
- Sudden performance changes
- Regression patterns
"""

import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import numpy as np


@dataclass
class TrendPoint:
    commit: str
    date: str
    benchmark: str
    language: str
    min_time: float
    mean_time: float
    cv: float


@dataclass
class TrendAnalysis:
    benchmark: str
    language: str
    points: List[TrendPoint]
    slope: float
    intercept: float
    r_squared: float
    is_degrading: bool
    trend_pct_per_commit: float
    total_change_pct: float


class TrendAnalyzer:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.trends: Dict[str, TrendAnalysis] = {}
    
    def get_commit_history(self, n: int = 50) -> List[Dict]:
        """Get recent commit history."""
        try:
            result = subprocess.run(
                ["git", "log", f"--oneline", f"-{n}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        commits.append({
                            "hash": parts[0],
                            "message": parts[1],
                        })
            return commits
        except Exception as e:
            print(f"Warning: Could not get git history: {e}")
            return []
    
    def analyze_results(self, results_file: Path) -> List[TrendPoint]:
        """Analyze a single results file."""
        points = []
        
        try:
            with open(results_file) as f:
                data = json.load(f)
            
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            
            for item in items:
                name = item.get("name", item.get("benchmark", "unknown"))
                language = item.get("language", "unknown")
                
                points.append(TrendPoint(
                    commit="current",
                    date="now",
                    benchmark=name,
                    language=language,
                    min_time=item.get("min_time", item.get("min_time_s", 0)),
                    mean_time=item.get("mean_time", item.get("mean_time_s", 0)),
                    cv=item.get("cv", 0),
                ))
        except Exception as e:
            print(f"Warning: Could not analyze {results_file}: {e}")
        
        return points
    
    def compute_linear_trend(self, times: List[float]) -> Tuple[float, float, float]:
        """
        Compute linear regression for trend.
        
        Returns: (slope, intercept, r_squared)
        """
        if len(times) < 2:
            return 0.0, times[0] if times else 0.0, 0.0
        
        n = len(times)
        x = np.arange(n)
        y = np.array(times)
        
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        if denominator == 0:
            return 0.0, y_mean, 0.0
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        return slope, intercept, r_squared
    
    def analyze_trends(self, all_points: List[TrendPoint]) -> List[TrendAnalysis]:
        """Analyze trends across all benchmark points."""
        by_benchmark = defaultdict(list)
        
        for point in all_points:
            key = f"{point.language}_{point.benchmark}"
            by_benchmark[key].append(point)
        
        trends = []
        for key, points in by_benchmark.items():
            if len(points) < 3:
                continue
            
            times = [p.min_time for p in points]
            slope, intercept, r_squared = self.compute_linear_trend(times)
            
            first_time = times[0]
            last_time = times[-1]
            total_change = ((last_time - first_time) / first_time * 100) if first_time > 0 else 0
            
            avg_time = np.mean(times)
            trend_per_commit = (slope / avg_time * 100) if avg_time > 0 else 0
            
            is_degrading = slope > 0 and total_change > 10
            
            language = points[0].language
            benchmark = points[0].benchmark
            
            analysis = TrendAnalysis(
                benchmark=benchmark,
                language=language,
                points=points,
                slope=slope,
                intercept=intercept,
                r_squared=r_squared,
                is_degrading=is_degrading,
                trend_pct_per_commit=trend_per_commit,
                total_change_pct=total_change,
            )
            
            trends.append(analysis)
        
        return trends
    
    def print_trend_report(self, trends: List[TrendAnalysis]):
        """Print trend analysis report."""
        print("\n" + "=" * 70)
        print("BENCHMARK TREND ANALYSIS")
        print("=" * 70)
        
        degrading = [t for t in trends if t.is_degrading]
        improving = [t for t in trends if t.slope < 0 and t.total_change_pct < -10]
        stable = [t for t in trends if not t.is_degrading and not (t.slope < 0 and t.total_change_pct < -10)]
        
        print(f"\nTotal trends analyzed: {len(trends)}")
        print(f"Degrading: {len(degrading)}")
        print(f"Improving: {len(improving)}")
        print(f"Stable: {len(stable)}")
        
        if degrading:
            print("\n--- Degrading Performance ---")
            for trend in sorted(degrading, key=lambda t: -t.total_change_pct):
                print(f"\n{trend.benchmark} ({trend.language}):")
                print(f"  Total change: +{trend.total_change_pct:.1f}%")
                print(f"  Change per commit: +{trend.trend_pct_per_commit:.2f}%")
                print(f"  R²: {trend.r_squared:.3f}")
        
        if improving:
            print("\n--- Improving Performance ---")
            for trend in sorted(improving, key=lambda t: t.total_change_pct):
                print(f"\n{trend.benchmark} ({trend.language}):")
                print(f"  Total change: {trend.total_change_pct:.1f}%")
                print(f"  Change per commit: {trend.trend_pct_per_commit:.2f}%")
        
        print("\n" + "=" * 70)
        
        return len(degrading) == 0


def main():
    parser = argparse.ArgumentParser(description="Analyze benchmark performance trends")
    parser.add_argument("results_dir", help="Directory containing benchmark results")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--repo", default=".", help="Repository path")
    
    args = parser.parse_args()
    
    analyzer = TrendAnalyzer(repo_path=args.repo)
    
    results_path = Path(args.results_dir)
    all_points = []
    
    for json_file in results_path.rglob("*.json"):
        if "validation" in str(json_file):
            continue
        points = analyzer.analyze_results(json_file)
        all_points.extend(points)
    
    trends = analyzer.analyze_trends(all_points)
    all_passed = analyzer.print_trend_report(trends)
    
    if args.output:
        output_data = {
            "trends": [asdict(t) for t in trends],
            "summary": {
                "total": len(trends),
                "degrading": sum(1 for t in trends if t.is_degrading),
                "improving": sum(1 for t in trends if t.slope < 0 and t.total_change_pct < -10),
                "stable": sum(1 for t in trends if not t.is_degrading),
            },
        }
        
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nReport saved to {args.output}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
