#!/usr/bin/env python3
"""
================================================================================
Standardized JSON Output Formatter for Thesis Benchmarks
================================================================================

Provides consistent JSON output format across all benchmark scripts.
Ensures cross-language compatibility and unified analysis.

Output Format:
{
    "schema_version": "1.0",
    "language": "python|julia|r",
    "scenario": "scenario_name",
    "timestamp": "ISO8601",
    "environment": {...},
    "timing": {
        "methodology": "minimum (Chen & Revels 2016)",
        "runs": N,
        "warmup": N,
        "tasks": {
            "task_name": {
                "min_time_s": float,
                "mean_time_s": float,
                "std_time_s": float,
                "median_time_s": float,
                "ci_95": [lower, upper]
            }
        }
    },
    "validation": {
        "hash": "...",
        "output_verified": bool
    },
    "metadata": {...}
}

Usage:
    from thesis_formatter import ThesisFormatter
    formatter = ThesisFormatter("python", "matrix_ops")
    formatter.add_task("matrix_creation", times_array)
    formatter.add_validation_hash(hash_value)
    formatter.save("results/matrix_ops_python.json")

================================================================================
"""

import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager

import numpy as np


# =============================================================================
# Schema Definition
# =============================================================================

SCHEMA_VERSION = "1.0"

REQUIRED_FIELDS = [
    "schema_version",
    "language",
    "scenario",
    "timestamp",
]

TIMING_FIELDS = [
    "min_time_s",
    "mean_time_s",
    "std_time_s",
    "median_time_s",
    "ci_95_lower",
    "ci_95_upper",
    "runs",
]


# =============================================================================
# Utility Functions
# =============================================================================


def compute_hash(data: Any, n_samples: int = 100) -> str:
    """Compute SHA256 hash of result data."""

    def sample_values(arr, n):
        flat = np.asarray(arr).flatten()
        if len(flat) <= n:
            return flat.tolist()
        indices = [int(i * len(flat) / n) for i in range(n)]
        return [float(flat[i]) for i in indices]

    def round_val(v, precision=6):
        if isinstance(v, (int, float, np.integer, np.floating)):
            return round(float(v), precision)
        return v

    if data is None:
        return "0" * 16

    if isinstance(data, dict):
        items = []
        for k in sorted(data.keys()):
            v = data[k]
            if isinstance(v, (np.ndarray, list, tuple)):
                sampled = sample_values(v, n_samples)
                items.append((str(k), [round_val(x) for x in sampled]))
            else:
                items.append((str(k), round_val(v)))
        content = json.dumps(items, sort_keys=True)
    elif isinstance(data, (list, tuple)):
        if len(data) > 0 and isinstance(data[0], (np.ndarray, list, tuple, int, float)):
            sampled = sample_values(data, n_samples)
            content = json.dumps([round_val(x) for x in sampled], sort_keys=True)
        else:
            content = json.dumps([round_val(x) for x in data], sort_keys=True)
    elif hasattr(data, "flatten"):
        sampled = sample_values(data, n_samples)
        content = json.dumps([round_val(x) for x in sampled], sort_keys=True)
    else:
        content = json.dumps(round_val(data), sort_keys=True)

    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def compute_statistics(times: Union[List[float], np.ndarray]) -> Dict[str, float]:
    """Compute comprehensive statistics for timing data."""
    times = np.asarray(times)

    if len(times) == 0:
        return {f: None for f in TIMING_FIELDS}

    mean = float(np.mean(times))
    std = float(np.std(times, ddof=1)) if len(times) > 1 else 0.0
    median = float(np.median(times))
    min_t = float(np.min(times))
    max_t = float(np.max(times))

    # Bootstrap CI for mean
    if len(times) >= 3:
        n_bootstrap = 1000
        bootstrap_means = np.zeros(n_bootstrap)
        for i in range(n_bootstrap):
            sample = np.random.choice(times, size=len(times), replace=True)
            bootstrap_means[i] = np.mean(sample)
        ci_lower = float(np.percentile(bootstrap_means, 2.5))
        ci_upper = float(np.percentile(bootstrap_means, 97.5))
    else:
        ci_lower = ci_upper = mean

    return {
        "min_time_s": min_t,
        "mean_time_s": mean,
        "std_time_s": std,
        "median_time_s": median,
        "max_time_s": max_t,
        "ci_95_lower": ci_lower,
        "ci_95_upper": ci_upper,
        "runs": len(times),
    }


# =============================================================================
# Formatter Class
# =============================================================================


class ThesisFormatter:
    """
    Standardized output formatter for thesis benchmarks.

    Usage:
        formatter = ThesisFormatter("python", "matrix_ops")
        formatter.add_task("matrix_creation", times_array)
        formatter.add_validation_hash("abc123...")
        formatter.save("results/matrix_ops_python.json")
    """

    def __init__(
        self,
        language: str,
        scenario: str,
        methodology: str = "minimum (Chen & Revels 2016)",
        warmup: int = 5,
        runs: int = 50,
    ):
        self.language = language.lower()
        self.scenario = scenario.lower()
        self.methodology = methodology
        self.warmup = warmup
        self.runs = runs

        self.tasks: Dict[str, Dict] = {}
        self.validation_hash: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.environment: Dict[str, Any] = {}

        self.timestamp = datetime.now().isoformat()

    def add_task(self, name: str, times: Union[List[float], np.ndarray], **kwargs):
        """Add timing results for a task."""
        stats = compute_statistics(times)
        stats.update(kwargs)
        self.tasks[name] = stats

    def add_validation_hash(self, data: Any):
        """Set validation hash from result data."""
        self.validation_hash = compute_hash(data)

    def set_validation_hash(self, hash_value: str):
        """Set validation hash directly."""
        self.validation_hash = hash_value

    def add_metadata(self, key: str, value: Any):
        """Add arbitrary metadata."""
        self.metadata[key] = value

    def add_environment_info(self, **kwargs):
        """Add environment information."""
        self.environment.update(kwargs)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "schema_version": SCHEMA_VERSION,
            "language": self.language,
            "scenario": self.scenario,
            "timestamp": self.timestamp,
            "methodology": {
                "name": self.methodology,
                "primary_metric": "minimum time",
                "citation": "Chen, J., & Revels, J. (2016). Robust benchmarking in noisy environments.",
            },
            "timing": {
                "runs": self.runs,
                "warmup": self.warmup,
                "tasks": self.tasks,
            },
        }

        if self.validation_hash:
            result["validation"] = {
                "hash": self.validation_hash,
                "hash_method": "SHA256 (16 chars, 100 samples)",
            }

        if self.environment:
            result["environment"] = self.environment

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def save(self, filepath: Union[str, Path]):
        """Save to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return str(filepath)

    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Thesis Benchmark Result: {self.scenario} ({self.language})",
            f"  Schema: v{SCHEMA_VERSION}",
            f"  Tasks: {len(self.tasks)}",
            f"  Timestamp: {self.timestamp}",
        ]

        for name, stats in self.tasks.items():
            lines.append(f"\n  {name}:")
            lines.append(f"    Min:    {stats.get('min_time_s', 0):.6f}s")
            lines.append(
                f"    Mean:   {stats.get('mean_time_s', 0):.6f}s ± {stats.get('std_time_s', 0):.6f}s"
            )
            lines.append(f"    Median: {stats.get('median_time_s', 0):.6f}s")
            if "ci_95_lower" in stats:
                lines.append(
                    f"    95% CI: [{stats['ci_95_lower']:.6f}, {stats['ci_95_upper']:.6f}]"
                )

        return "\n".join(lines)


# =============================================================================
# Backward Compatibility
# =============================================================================


def convert_old_format(old_data: Dict) -> Dict:
    """Convert old format to new standardized format."""
    new = ThesisFormatter(
        language=old_data.get("language", "unknown"),
        scenario=old_data.get("scenario", old_data.get("name", "unknown")),
    )

    if "results" in old_data:
        for task_name, task_data in old_data["results"].items():
            if isinstance(task_data, dict):
                times = []
                for key in [
                    "min",
                    "min_time",
                    "min_time_s",
                    "mean",
                    "execution_time_s",
                ]:
                    if key in task_data:
                        times.append(task_data[key])
                        break
                if times:
                    new.add_task(task_name, times)

    if "validation_hash" in old_data:
        new.set_validation_hash(old_data["validation_hash"])

    return new.to_dict()


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Standardize benchmark JSON output")
    parser.add_argument("input_file", help="Input JSON file to convert")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--validate", action="store_true", help="Validate schema compliance"
    )

    args = parser.parse_args()

    with open(args.input_file) as f:
        data = json.load(f)

    # Check required fields
    if args.validate:
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            print(f"⚠ Missing required fields: {missing}")
        else:
            print("✓ All required fields present")

    # Convert if needed
    if data.get("schema_version") != SCHEMA_VERSION:
        data = convert_old_format(data)

    output = json.dumps(data, indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(f"✓ Saved to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
