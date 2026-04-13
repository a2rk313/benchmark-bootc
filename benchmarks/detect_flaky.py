#!/usr/bin/env python3
"""
Flaky Test Detection for Benchmark Results

Analyzes benchmark variance over time to detect:
1. Tests with high coefficient of variation (CV > threshold)
2. Tests that are systematically slowing down
3. Tests with bimodal distributions (hot/cold cache effects)
4. Outliers in timing distributions
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import argparse


@dataclass
class FlakyTestResult:
    benchmark: str
    language: str
    cv: float
    is_flaky: bool
    flaky_reason: str
    suggestion: str


class FlakyTestDetector:
    CV_THRESHOLD = 0.10
    OUTLIER_STD_THRESHOLD = 3.0
    
    def __init__(self, cv_threshold: float = 0.10):
        self.cv_threshold = cv_threshold
        self.results: List[FlakyTestResult] = []
    
    def analyze_single_benchmark(
        self,
        times: List[float],
        benchmark_name: str,
        language: str = "unknown",
    ) -> FlakyTestResult:
        """Analyze a single benchmark for flakiness."""
        times_arr = np.array(times)
        
        mean_t = np.mean(times_arr)
        std_t = np.std(times_arr)
        cv = std_t / mean_t if mean_t > 0 else 0
        
        mean, std = mean_t, std_t
        outlier_mask = np.abs(times_arr - mean) > self.OUTLIER_STD_THRESHOLD * std
        n_outliers = np.sum(outlier_mask)
        outlier_pct = n_outliers / len(times_arr) * 100 if len(times_arr) > 0 else 0
        
        bimodal_score = self._detect_bimodality(times_arr)
        
        is_flaky = False
        flaky_reason = "stable"
        suggestion = "No action needed"
        
        if cv > self.cv_threshold:
            is_flaky = True
            flaky_reason = f"High variance (CV={cv:.1%})"
            suggestion = "Increase warmup runs or check for resource contention"
        
        if outlier_pct > 10:
            flaky_reason += f", {outlier_pct:.0f}% outliers"
            suggestion = "Check for background processes or thermal throttling"
        
        if bimodal_score > 0.7:
            flaky_reason += ", bimodal distribution"
            suggestion = "Cache effects detected - increase warmup"
        
        return FlakyTestResult(
            benchmark=benchmark_name,
            language=language,
            cv=cv,
            is_flaky=is_flaky,
            flaky_reason=flaky_reason,
            suggestion=suggestion,
        )
    
    def _detect_bimodality(self, times: np.ndarray) -> float:
        """Detect bimodal distribution using Hartigan's dip test approximation."""
        if len(times) < 10:
            return 0.0
        
        sorted_times = np.sort(times)
        n = len(sorted_times)
        
        left = sorted_times[:n//2]
        right = sorted_times[n//2:]
        
        mean_diff = abs(np.mean(left) - np.mean(right))
        overall_std = np.std(sorted_times)
        
        if overall_std == 0:
            return 0.0
        
        bimodal_score = mean_diff / overall_std
        
        return min(bimodal_score / 2, 1.0)
    
    def analyze_results_directory(self, results_dir: str) -> List[FlakyTestResult]:
        """Analyze all benchmarks in a directory."""
        results_path = Path(results_dir)
        
        for json_file in results_path.rglob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                
                self._analyze_json_data(data)
            except Exception as e:
                print(f"Warning: Could not analyze {json_file}: {e}")
        
        return self.results
    
    def _analyze_json_data(self, data, parent_key: str = ""):
        """Recursively analyze JSON data for timing arrays."""
        if isinstance(data, dict):
            if "times" in data and isinstance(data["times"], list):
                times = data["times"]
                if len(times) > 3:
                    result = self.analyze_single_benchmark(
                        times,
                        data.get("name", parent_key),
                        data.get("language", "unknown"),
                    )
                    self.results.append(result)
            
            for key, value in data.items():
                if key not in ("languages", "results", "config"):
                    self._analyze_json_data(value, key)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._analyze_json_data(item, f"{parent_key}_{i}")
    
    def detect_trend(self, times: List[float]) -> Tuple[float, bool]:
        """
        Detect if performance is degrading over time.
        
        Returns:
            Tuple of (degradation_pct, is_degrading)
        """
        if len(times) < 5:
            return 0.0, False
        
        times_arr = np.array(times)
        n = len(times_arr)
        
        first_half = np.mean(times_arr[:n//2])
        second_half = np.mean(times_arr[n//2:])
        
        if first_half == 0:
            return 0.0, False
        
        degradation_pct = ((second_half - first_half) / first_half) * 100
        
        return degradation_pct, degradation_pct > 10
    
    def print_report(self):
        """Print flaky test report."""
        print("\n" + "=" * 70)
        print("FLAKY TEST DETECTION REPORT")
        print("=" * 70)
        
        flaky_tests = [r for r in self.results if r.is_flaky]
        stable_tests = [r for r in self.results if not r.is_flaky]
        
        print(f"\nTotal benchmarks analyzed: {len(self.results)}")
        print(f"Stable tests: {len(stable_tests)}")
        print(f"Flaky tests: {len(flaky_tests)}")
        
        if flaky_tests:
            print("\n--- FLaky Tests ---")
            for result in flaky_tests:
                print(f"\n{result.benchmark} ({result.language}):")
                print(f"  CV: {result.cv:.2%}")
                print(f"  Reason: {result.flaky_reason}")
                print(f"  Suggestion: {result.suggestion}")
        
        if stable_tests:
            print("\n--- Stable Tests ---")
            for result in stable_tests[:10]:
                print(f"  ✓ {result.benchmark} ({result.language}): CV={result.cv:.2%}")
            if len(stable_tests) > 10:
                print(f"  ... and {len(stable_tests) - 10} more")
        
        print("\n" + "=" * 70)
        
        return len(flaky_tests) == 0
    
    def export_report(self, output_path: str):
        """Export report to JSON."""
        report = {
            "summary": {
                "total": len(self.results),
                "flaky": sum(1 for r in self.results if r.is_flaky),
                "stable": sum(1 for r in self.results if not r.is_flaky),
                "cv_threshold": self.cv_threshold,
            },
            "flaky_tests": [asdict(r) for r in self.results if r.is_flaky],
            "stable_tests": [asdict(r) for r in self.results if not r.is_flaky],
        }
        
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"Report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Detect flaky benchmark tests")
    parser.add_argument("results_dir", help="Directory containing benchmark results")
    parser.add_argument("--cv-threshold", type=float, default=0.10, help="CV threshold for flakiness")
    parser.add_argument("--analyze", action="store_true", help="Run full analysis")
    parser.add_argument("--output", help="Output JSON file for report")
    
    args = parser.parse_args()
    
    detector = FlakyTestDetector(cv_threshold=args.cv_threshold)
    detector.analyze_results_directory(args.results_dir)
    
    all_passed = detector.print_report()
    
    if args.output:
        detector.export_report(args.output)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
