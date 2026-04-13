#!/usr/bin/env python3
"""
Regression Testing Module for Thesis Benchmarks

Validates that benchmark results haven't regressed against known-good baselines.
Supports both output hash validation and statistical regression detection.
"""

import json
import hashlib
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class RegressionStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NEW_BENCHMARK = "new"


@dataclass
class RegressionResult:
    benchmark: str
    language: str
    status: RegressionStatus
    expected_hash: Optional[str]
    actual_hash: Optional[str]
    expected_min_time: Optional[float]
    actual_min_time: Optional[float]
    regression_pct: Optional[float]
    message: str


class RegressionTestSuite:
    def __init__(self, baseline_file: str = "containers/versions.json"):
        self.baseline_file = Path(baseline_file)
        self.baselines = self._load_baselines()
        self.results: List[RegressionResult] = []
    
    def _load_baselines(self) -> Dict:
        if self.baseline_file.exists():
            with open(self.baseline_file) as f:
                return json.load(f)
        return {"regression_hashes": {}, "expected_times": {}}
    
    def validate_hash(
        self,
        benchmark: str,
        language: str,
        output_hash: str,
    ) -> RegressionResult:
        """Validate output hash against baseline."""
        key = f"{language}_{benchmark}"
        expected = self.baselines.get("regression_hashes", {}).get(key)
        
        if expected is None:
            return RegressionResult(
                benchmark=benchmark,
                language=language,
                status=RegressionStatus.NEW_BENCHMARK,
                expected_hash=None,
                actual_hash=output_hash,
                expected_min_time=None,
                actual_min_time=None,
                regression_pct=None,
                message=f"New benchmark '{key}' - no baseline available",
            )
        
        if output_hash == expected:
            return RegressionResult(
                benchmark=benchmark,
                language=language,
                status=RegressionStatus.PASS,
                expected_hash=expected,
                actual_hash=output_hash,
                expected_min_time=None,
                actual_min_time=None,
                regression_pct=None,
                message="Output hash matches baseline",
            )
        
        return RegressionResult(
            benchmark=benchmark,
            language=language,
            status=RegressionStatus.FAIL,
            expected_hash=expected,
            actual_hash=output_hash,
            expected_min_time=None,
            actual_min_time=None,
            regression_pct=None,
            message="Output hash MISMATCH - results have changed",
        )
    
    def validate_timing(
        self,
        benchmark: str,
        language: str,
        min_time: float,
        tolerance_pct: float = 10.0,
    ) -> RegressionResult:
        """Validate timing against baseline with tolerance."""
        key = f"{language}_{benchmark}"
        expected = self.baselines.get("expected_times", {}).get(key, {}).get("min_time")
        
        if expected is None:
            return RegressionResult(
                benchmark=benchmark,
                language=language,
                status=RegressionStatus.NEW_BENCHMARK,
                expected_hash=None,
                actual_hash=None,
                expected_min_time=None,
                actual_min_time=min_time,
                regression_pct=None,
                message=f"New benchmark '{key}' - no baseline available",
            )
        
        regression_pct = ((min_time - expected) / expected) * 100
        
        if abs(regression_pct) <= tolerance_pct:
            status = RegressionStatus.PASS
            message = f"Time within {tolerance_pct}% of baseline"
        elif regression_pct > 0:
            status = RegressionStatus.FAIL
            message = f"SLOWDOWN: {regression_pct:.1f}% slower than baseline"
        else:
            status = RegressionStatus.WARNING
            message = f"SPEEDUP: {abs(regression_pct):.1f}% faster than baseline"
        
        return RegressionResult(
            benchmark=benchmark,
            language=language,
            status=status,
            expected_hash=None,
            actual_hash=None,
            expected_min_time=expected,
            actual_min_time=min_time,
            regression_pct=regression_pct,
            message=message,
        )
    
    def run_validation(
        self,
        results_file: str,
        mode: str = "hash",
        tolerance_pct: float = 10.0,
    ) -> Tuple[int, int, int]:
        """
        Run validation against a results file.
        
        Returns:
            Tuple of (passed, failed, warnings)
        """
        results_path = Path(results_file)
        if not results_path.exists():
            print(f"Warning: Results file not found: {results_file}")
            return 0, 0, 0
        
        with open(results_path) as f:
            results_data = json.load(f)
        
        if isinstance(results_data, list):
            for result in results_data:
                self._validate_single_result(result, mode, tolerance_pct)
        elif isinstance(results_data, dict):
            for lang, lang_results in results_data.items():
                if isinstance(lang_results, list):
                    for result in lang_results:
                        self._validate_single_result(result, mode, tolerance_pct)
        
        return self._count_results()
    
    def _validate_single_result(
        self,
        result: Dict,
        mode: str,
        tolerance_pct: float,
    ):
        benchmark = result.get("name", result.get("benchmark", "unknown"))
        language = result.get("language", "unknown")
        
        if mode == "hash":
            output_hash = result.get("output_hash")
            if output_hash:
                validation = self.validate_hash(benchmark, language, output_hash)
                self.results.append(validation)
        
        elif mode == "timing":
            min_time = result.get("min_time")
            if min_time:
                validation = self.validate_timing(benchmark, language, min_time, tolerance_pct)
                self.results.append(validation)
        
        elif mode == "both":
            output_hash = result.get("output_hash")
            min_time = result.get("min_time")
            
            if output_hash:
                self.results.append(self.validate_hash(benchmark, language, output_hash))
            if min_time:
                self.results.append(self.validate_timing(benchmark, language, min_time, tolerance_pct))
    
    def _count_results(self) -> Tuple[int, int, int]:
        passed = sum(1 for r in self.results if r.status == RegressionStatus.PASS)
        failed = sum(1 for r in self.results if r.status == RegressionStatus.FAIL)
        warnings = sum(1 for r in self.results if r.status == RegressionStatus.WARNING)
        return passed, failed, warnings
    
    def print_report(self):
        """Print a formatted regression report."""
        print("\n" + "=" * 70)
        print("REGRESSION TEST REPORT")
        print("=" * 70)
        
        passed, failed, warnings = self._count_results()
        new_benchmarks = sum(1 for r in self.results if r.status == RegressionStatus.NEW_BENCHMARK)
        
        print(f"\nSummary: {passed} passed, {failed} failed, {warnings} warnings, {new_benchmarks} new")
        
        print("\n--- Failed Tests ---")
        for r in self.results:
            if r.status == RegressionStatus.FAIL:
                print(f"  FAIL: {r.benchmark} ({r.language})")
                print(f"        {r.message}")
        
        print("\n--- Warning Tests ---")
        for r in self.results:
            if r.status == RegressionStatus.WARNING:
                print(f"  WARN: {r.benchmark} ({r.language})")
                print(f"        {r.message}")
        
        print("\n--- Passed Tests ---")
        for r in self.results:
            if r.status == RegressionStatus.PASS:
                print(f"  PASS: {r.benchmark} ({r.language})")
        
        print("\n" + "=" * 70)
        
        return failed == 0
    
    def export_baseline(
        self,
        results_file: str,
        output_file: str = "containers/versions.json",
    ):
        """Export current results as new baseline."""
        with open(results_file) as f:
            results_data = json.load(f)
        
        baselines = self.baselines.copy()
        if "regression_hashes" not in baselines:
            baselines["regression_hashes"] = {}
        if "expected_times" not in baselines:
            baselines["expected_times"] = {}
        
        for lang, lang_results in results_data.items():
            if isinstance(lang_results, list):
                for result in lang_results:
                    key = f"{lang}_{result.get('name', result.get('benchmark'))}"
                    if "output_hash" in result:
                        baselines["regression_hashes"][key] = result["output_hash"]
                    if "min_time" in result:
                        baselines["expected_times"][key] = {"min_time": result["min_time"]}
        
        with open(output_file, "w") as f:
            json.dump(baselines, f, indent=2)
        
        print(f"Updated baselines saved to {output_file}")


def add_expected_times_to_baseline():
    """Update baseline with expected timing values."""
    baseline_path = Path("containers/versions.json")
    if baseline_path.exists():
        with open(baseline_path) as f:
            data = json.load(f)
    else:
        data = {}
    
    data["expected_times"] = {
        "python_matrix_ops": {"min_time": 0.5, "std_pct": 5.0},
        "julia_matrix_ops": {"min_time": 0.3, "std_pct": 5.0},
        "r_matrix_ops": {"min_time": 0.8, "std_pct": 5.0},
        "python_hsi_stream": {"min_time": 1.2, "std_pct": 8.0},
        "julia_hsi_stream": {"min_time": 0.9, "std_pct": 8.0},
        "r_hsi_stream": {"min_time": 2.0, "std_pct": 10.0},
        "python_io_ops": {"min_time": 0.3, "std_pct": 10.0},
        "julia_io_ops": {"min_time": 0.2, "std_pct": 10.0},
        "r_io_ops": {"min_time": 0.4, "std_pct": 10.0},
    }
    
    with open(baseline_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print("Updated baseline with expected times")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python regression_tests.py <results_file> [--export]")
        sys.exit(1)
    
    results_file = sys.argv[1]
    suite = RegressionTestSuite()
    
    if "--export" in sys.argv:
        suite.export_baseline(results_file)
    else:
        passed, failed, warnings = suite.run_validation(results_file, mode="both")
        suite.print_report()
        sys.exit(0 if failed == 0 else 1)
