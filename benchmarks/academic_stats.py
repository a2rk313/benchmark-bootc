"""
Academic Benchmarking Utilities for GIS/Remote Sensing Performance Analysis

Provides tools for rigorous, reproducible computational benchmarking:
- CPU pinning for consistent timing
- Statistical significance testing (Wilcoxon)
- CPU frequency monitoring
- Multi-run benchmarking with variance estimation
- Academic-quality reporting (mean ± std, CI, p-values)

Author: Thesis Benchmark Suite
Version: 1.0.0
"""

import os
import sys
import json
import time
import subprocess
import warnings
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
import threading
import statistics

import numpy as np

try:
    from scipy import stats

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    warnings.warn("scipy not available - some statistical tests will be limited")


# =============================================================================
# Configuration
# =============================================================================

BENCHMARK_CONFIG = {
    "runs": 50,
    "warmup": 5,
    "cache_warmup_iterations": 3,
    "cpu_pin_enabled": True,
    "cpu_cores": None,  # Auto-detect
    "confidence_level": 0.95,
}


@dataclass
class BenchmarkResult:
    """Comprehensive benchmark result with statistical analysis."""

    name: str = ""
    language: str = ""

    min_time: float = 0.0
    mean_time: float = 0.0
    std_time: float = 0.0
    median_time: float = 0.0
    max_time: float = 0.0

    runs: int = 0
    cv: float = 0.0
    iqr: float = 0.0

    ci_95_lower: float = 0.0
    ci_95_upper: float = 0.0
    ci_99_lower: float = 0.0
    ci_99_upper: float = 0.0

    normality_test: str = "shapiro-wilk"
    normality_p_value: float = 1.0
    is_normal: bool = True

    compared_to: Optional[str] = None
    speedup: Optional[float] = None
    p_value: Optional[float] = None
    is_significant: Optional[bool] = None
    significance_level: Optional[float] = None

    cpu_freq_mhz: Optional[float] = None
    cpu_freq_min: Optional[float] = None
    cpu_freq_max: Optional[float] = None
    memory_mb: Optional[float] = None

    output_hash: Optional[str] = None

    median_of_means: Optional[float] = None
    mom_blocks: Optional[int] = None

    normality_dagostino_p: Optional[float] = None
    normality_jarque_p: Optional[float] = None

    allocations_peak: Optional[int] = None
    memory_rss_mb: Optional[float] = None
    memory_vms_mb: Optional[float] = None

    scaling_factor: Optional[float] = None
    sizes_tested: Optional[List[int]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        # Convert numpy types to Python types
        for k, v in d.items():
            if isinstance(v, (np.integer, np.floating)):
                d[k] = float(v)
            elif isinstance(v, np.bool_):
                d[k] = bool(v)
        return d

    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [
            f"  Min:    {self.min_time:.6f}s (primary)",
            f"  Mean:   {self.mean_time:.6f}s ± {self.std_time:.6f}s",
            f"  Median: {self.median_time:.6f}s",
            f"  95% CI: [{self.ci_95_lower:.6f}, {self.ci_95_upper:.6f}]",
            f"  CV:     {self.cv:.2%}",
        ]
        if self.is_normal is not None:
            status = "Normal" if self.is_normal else "Non-normal"
            lines.append(f"  Normality: {status} (p={self.normality_p_value:.4f})")
        if self.speedup is not None:
            lines.append(f"  Speedup vs {self.compared_to}: {self.speedup:.2f}×")
        if self.is_significant is not None:
            sig = "Yes" if self.is_significant else "No"
            lines.append(f"  Significant: {sig} (p={self.p_value:.4f})")
        if self.cpu_freq_mhz is not None:
            lines.append(f"  CPU freq: {self.cpu_freq_mhz:.0f} MHz")
        return "\n".join(lines)


@dataclass
class CPUMonitor:
    """Monitor CPU frequency during benchmarking."""

    samples: List[float] = field(default_factory=list)
    min_freq: float = float("inf")
    max_freq: float = 0.0
    _running: bool = False
    _thread: Optional[threading.Thread] = None

    def start(self):
        """Start monitoring CPU frequency."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> Tuple[float, float, float]:
        """Stop monitoring and return stats."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

        if not self.samples:
            return 0.0, 0.0, 0.0

        return (
            statistics.mean(self.samples),
            self.min_freq if self.min_freq != float("inf") else 0.0,
            self.max_freq,
        )

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            freq = get_current_cpu_freq()
            if freq > 0:
                self.samples.append(freq)
                self.min_freq = min(self.min_freq, freq)
                self.max_freq = max(self.max_freq, freq)
            time.sleep(0.1)  # Sample every 100ms


# =============================================================================
# CPU Pinning Utilities
# =============================================================================


def get_available_cores() -> List[int]:
    """Get list of available CPU cores."""
    try:
        nproc = os.cpu_count()
        return list(range(nproc)) if nproc else [0]
    except:
        return [0]


def pin_to_core(core: int) -> bool:
    """Pin current process to a specific CPU core."""
    try:
        # Try taskset first (more portable)
        result = subprocess.run(
            ["taskset", "-c", "-p", str(core), str(os.getpid())],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        pass

    try:
        # Try affinity on Linux
        import os

        os.sched_setaffinity(os.getpid(), {core})
        return True
    except (AttributeError, OSError):
        return False


def pin_to_cores(cores: List[int]) -> bool:
    """Pin to multiple cores (for multi-threaded workloads)."""
    try:
        cores_str = ",".join(str(c) for c in cores)
        result = subprocess.run(
            ["taskset", "-c", "-p", cores_str, str(os.getpid())],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        pass

    try:
        import os

        os.sched_setaffinity(os.getpid(), set(cores))
        return True
    except (AttributeError, OSError):
        return False


@contextmanager
def cpu_pinned(core: Optional[int] = None):
    """Context manager to pin CPU during benchmark."""
    original_affinity = None

    try:
        import os

        original_affinity = os.sched_getaffinity(os.getpid())
    except (AttributeError, OSError):
        pass

    if core is not None:
        pin_to_core(core)
    elif BENCHMARK_CONFIG["cpu_pin_enabled"]:
        cores = BENCHMARK_CONFIG["cpu_cores"] or get_available_cores()
        if cores:
            pin_to_cores(cores[:4])  # Use first 4 cores

    try:
        yield
    finally:
        if original_affinity is not None:
            try:
                import os

                os.sched_setaffinity(os.getpid(), original_affinity)
            except:
                pass


# =============================================================================
# CPU Frequency Monitoring
# =============================================================================


def get_current_cpu_freq() -> float:
    """Get current CPU frequency in MHz."""
    try:
        # Try /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq (Linux)
        freq_file = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
        if freq_file.exists():
            return float(freq_file.read_text().strip()) / 1000  # kHz to MHz
    except:
        pass

    try:
        # Try cpufreq-info
        result = subprocess.run(
            ["cpufreq-info", "-c", "0", "-l"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass

    return 0.0


def disable_turbo_boost() -> bool:
    """Attempt to disable CPU turbo boost for consistent timings."""
    try:
        # Try MSR on Intel
        if Path("/dev/cpu/0/msr").exists():
            subprocess.run(
                ["wrmsr", "-a", "0x1a0", "0x400085", "0xffffffff"],
                capture_output=True,
                check=False,
            )
            return True
    except:
        pass

    try:
        # Try setting CPU governor to performance
        for cpu in range(os.cpu_count() or 4):
            subprocess.run(
                ["cpupower", "-c", str(cpu), "frequency-set", "-g", "performance"],
                capture_output=True,
                check=False,
            )
        return True
    except:
        pass

    return False


# =============================================================================
# Statistical Analysis
# =============================================================================


def compute_statistics(times: np.ndarray, confidence: float = 0.95) -> Dict[str, float]:
    """
    Compute comprehensive statistics for timing data.

    Args:
        times: Array of timing measurements
        confidence: Confidence level for CIs

    Returns:
        Dictionary of statistics
    """
    n = len(times)
    mean = np.mean(times)
    std = np.std(times, ddof=1)
    median = np.median(times)
    min_t = np.min(times)
    max_t = np.max(times)

    # Coefficient of variation
    cv = std / mean if mean > 0 else 0.0

    # IQR
    q75, q25 = np.percentile(times, [75, 25])
    iqr = q75 - q25

    # Bootstrap CI for mean
    ci_level = confidence
    alpha = 1 - ci_level

    n_bootstrap = 1000
    bootstrap_means = np.zeros(n_bootstrap)
    for i in range(n_bootstrap):
        sample = np.random.choice(times, size=n, replace=True)
        bootstrap_means[i] = np.mean(sample)

    ci_lower = np.percentile(bootstrap_means, alpha / 2 * 100)
    ci_upper = np.percentile(bootstrap_means, (1 - alpha / 2) * 100)

    # 99% CI
    bootstrap_means_99 = np.zeros(1000)
    for i in range(1000):
        sample = np.random.choice(times, size=n, replace=True)
        bootstrap_means_99[i] = np.mean(sample)

    ci_99_lower = np.percentile(bootstrap_means_99, 0.5)
    ci_99_upper = np.percentile(bootstrap_means_99, 99.5)

    return {
        "min_time": min_t,
        "max_time": max_t,
        "mean_time": mean,
        "std_time": std,
        "median_time": median,
        "cv": cv,
        "iqr": iqr,
        "ci_95_lower": ci_lower,
        "ci_95_upper": ci_upper,
        "ci_99_lower": ci_99_lower,
        "ci_99_upper": ci_99_upper,
    }


def test_normality(times: np.ndarray) -> Tuple[str, float, bool]:
    """
    Test for normality using appropriate test.

    Returns:
        Tuple of (test_name, p_value, is_normal)
    """
    n = len(times)

    if n < 3:
        return ("insufficient_data", 1.0, True)

    if n < 5000 and SCIPY_AVAILABLE:
        # Shapiro-Wilk (best for n < 5000)
        stat, p = stats.shapiro(times)
        return ("shapiro-wilk", p, p > 0.05)
    elif SCIPY_AVAILABLE:
        # D'Agostino-Pearson (good for larger samples)
        stat, p = stats.normaltest(times)
        return ("dagostino-pearson", p, p > 0.05)
    else:
        # Simple skewness/kurtosis test
        from scipy.stats import skew, kurtosis

        skewness = abs(skew(times))
        k = abs(kurtosis(times))
        # Heuristic: data is normal if skewness < 2 and kurtosis < 7
        is_normal = skewness < 2 and k < 7
        return ("skewness-kurtosis", 0.05 if is_normal else 0.01, is_normal)


def wilcoxon_signed_rank_test(
    times1: np.ndarray, times2: np.ndarray, significance_level: float = 0.05
) -> Tuple[float, float, bool]:
    """
    Wilcoxon signed-rank test for paired samples.

    Tests if the median difference between pairs is zero.
    Non-parametric alternative to paired t-test.

    Args:
        times1: First sample (baseline)
        times2: Second sample
        significance_level: Alpha for significance test

    Returns:
        Tuple of (test_statistic, p_value, is_significant)
    """
    if len(times1) != len(times2):
        raise ValueError("Samples must be paired (same length)")

    if len(times1) < 5:
        return (0.0, 1.0, False)

    if SCIPY_AVAILABLE:
        try:
            stat, p = stats.wilcoxon(times1, times2)
            return (float(stat), float(p), float(p) < significance_level)
        except ValueError:
            # All differences are zero
            return (0.0, 1.0, False)
    else:
        # Manual implementation
        diffs = times1 - times2
        diffs = diffs[diffs != 0]  # Remove zeros

        if len(diffs) == 0:
            return (0.0, 1.0, False)

        ranks = np.abs(diffs)
        signed_ranks = np.sign(diffs) * ranks

        W_plus = np.sum(signed_ranks[signed_ranks > 0])
        W_minus = np.abs(np.sum(signed_ranks[signed_ranks < 0]))
        W = min(W_plus, W_minus)

        # Approximate p-value using normal approximation
        n = len(diffs)
        expected = n * (n + 1) / 4
        variance = n * (n + 1) * (2 * n + 1) / 24

        if variance > 0:
            z = (W - expected) / np.sqrt(variance)
            p = 2 * (1 - stats.norm.cdf(abs(z))) if SCIPY_AVAILABLE else 0.05
        else:
            p = 1.0

        return (float(W), float(p), float(p) < significance_level)


def mann_whitney_u_test(
    times1: np.ndarray, times2: np.ndarray, significance_level: float = 0.05
) -> Tuple[float, float, bool]:
    """
    Mann-Whitney U test for independent samples.

    Non-parametric test to compare two independent samples.
    """
    if len(times1) < 3 or len(times2) < 3:
        return (0.0, 1.0, False)

    if SCIPY_AVAILABLE:
        try:
            stat, p = stats.mannwhitneyu(times1, times2, alternative="two-sided")
            return (float(stat), float(p), float(p) < significance_level)
        except ValueError:
            return (0.0, 1.0, False)
    else:
        return (0.0, 1.0, False)


def friedman_test(*samples) -> Tuple[float, float, bool]:
    """
    Friedman test for comparing multiple related samples.

    Non-parametric alternative to repeated measures ANOVA.
    """
    if not SCIPY_AVAILABLE:
        return (0.0, 1.0, False)

    try:
        stat, p = stats.friedmanchisquare(*samples)
        return (float(stat), float(p), float(p) < 0.05)
    except:
        return (0.0, 1.0, False)


# =============================================================================
# Academic Reporting
# =============================================================================


def format_academic_result(result: BenchmarkResult, benchmark_name: str = "") -> str:
    """Format result in academic paper style."""
    lines = []

    if benchmark_name:
        lines.append(f"\n{benchmark_name}")
        lines.append("-" * len(benchmark_name))

    lines.append(f"Primary metric (min): {result.min_time:.6f}s")
    lines.append(f"Mean ± SD: {result.mean_time:.6f} ± {result.std_time:.6f}s")
    lines.append(f"Median: {result.median_time:.6f}s")
    lines.append(f"95% CI: [{result.ci_95_lower:.6f}, {result.ci_95_upper:.6f}]")
    lines.append(f"Coefficient of variation: {result.cv:.2%}")
    lines.append(
        f"Normality: {result.normality_test} (p={result.normality_p_value:.4f})"
    )

    if result.speedup is not None:
        lines.append(f"Speedup vs {result.compared_to}: {result.speedup:.2f}×")

    if result.p_value is not None:
        lines.append(f"Statistical significance: p={'{:.4f}'.format(result.p_value)}")

    return "\n".join(lines)


def generate_comparison_table(results: Dict[str, BenchmarkResult]) -> str:
    """Generate LaTeX-style comparison table."""
    headers = ["Benchmark", "Language", "Min (s)", "Mean ± SD (s)", "95% CI", "CV"]

    lines = []
    lines.append("\\begin{table}[h]")
    lines.append("\\centering")
    lines.append("\\begin{tabular}{l" + "r" * (len(headers) - 1) + "}")
    lines.append("\\hline")
    lines.append(" & ".join(headers) + " \\\\")
    lines.append("\\hline")

    for name, result in results.items():
        row = [
            name,
            result.language,
            f"{result.min_time:.4f}",
            f"{result.mean_time:.4f} ± {result.std_time:.4f}",
            f"[{result.ci_95_lower:.4f}, {result.ci_95_upper:.4f}]",
            f"{result.cv:.2%}",
        ]
        lines.append(" & ".join(row) + " \\\\")

    lines.append("\\hline")
    lines.append("\\end{tabular}")
    lines.append("\\caption{Benchmark Results}")
    lines.append("\\end{table}")

    return "\n".join(lines)


# =============================================================================
# Benchmark Runner
# =============================================================================


def run_benchmark_with_stats(
    func: Callable,
    name: str = "",
    runs: int = 50,
    warmup: int = 5,
    language: str = "python",
    validator: Optional[Callable] = None,
    track_cpu: bool = True,
) -> BenchmarkResult:
    """
    Run a benchmark with comprehensive statistical analysis.

    Args:
        func: Function to benchmark
        name: Benchmark name
        runs: Number of measurement runs
        warmup: Number of warmup runs
        language: Programming language name
        validator: Optional function returning output to hash
        track_cpu: Whether to track CPU frequency

    Returns:
        BenchmarkResult with all statistics
    """
    # CPU pinning
    with cpu_pinned():
        # Warmup runs
        for _ in range(warmup):
            func()

        # Cache warmup (extra iterations for cache effects)
        for _ in range(BENCHMARK_CONFIG["cache_warmup_iterations"]):
            func()

        # CPU monitoring
        monitor = CPUMonitor() if track_cpu else None
        if monitor:
            monitor.start()

        # Timing runs
        times = []
        for _ in range(runs):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)

        if monitor:
            monitor.stop()

    times = np.array(times)

    # Compute statistics
    stats_dict = compute_statistics(times)
    test_name, p_norm, is_normal = test_normality(times)

    # Get CPU frequency
    cpu_mean, cpu_min, cpu_max = (
        (monitor.samples, monitor.min_freq, monitor.max_freq) if monitor else (0, 0, 0)
    )

    # Generate output hash
    output_hash = None
    if validator:
        try:
            output_hash = hash_output(validator())
        except:
            pass

    result = BenchmarkResult(
        min_time=stats_dict["min_time"],
        mean_time=stats_dict["mean_time"],
        std_time=stats_dict["std_time"],
        median_time=stats_dict["median_time"],
        max_time=stats_dict["max_time"],
        runs=runs,
        cv=stats_dict["cv"],
        iqr=stats_dict["iqr"],
        ci_95_lower=stats_dict["ci_95_lower"],
        ci_95_upper=stats_dict["ci_95_upper"],
        ci_99_lower=stats_dict["ci_99_lower"],
        ci_99_upper=stats_dict["ci_99_upper"],
        normality_test=test_name,
        normality_p_value=p_norm,
        is_normal=is_normal,
        cpu_freq_mhz=cpu_mean,
        cpu_freq_min=cpu_min,
        cpu_freq_max=cpu_max,
        output_hash=output_hash,
    )

    return result


def hash_output(data: Any, n_samples: int = 100) -> str:
    """Generate hash of output for validation."""
    import hashlib

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


# =============================================================================
# Multi-run Suite
# =============================================================================


def run_benchmark_suite(
    benchmarks: Dict[str, Tuple[Callable, Optional[Callable]]],
    runs: int = 50,
    warmup: int = 5,
    language: str = "python",
    n_full_repeats: int = 3,
) -> List[Dict[str, BenchmarkResult]]:
    """
    Run complete benchmark suite with multiple full repeats.

    Args:
        benchmarks: Dict of name -> (func, validator_func)
        runs: Runs per benchmark
        warmup: Warmup runs
        language: Language name
        n_full_repeats: Number of full suite repeats

    Returns:
        List of results dicts (one per repeat)
    """
    all_results = []

    for repeat in range(n_full_repeats):
        print(f"\n{'=' * 60}")
        print(f"FULL SUITE REPEAT {repeat + 1}/{n_full_repeats}")
        print(f"{'=' * 60}")

        repeat_results = {}

        for name, (func, validator) in benchmarks.items():
            print(f"\n{name}...", end=" ", flush=True)
            result = run_benchmark_with_stats(
                func=func,
                name=name,
                runs=runs,
                warmup=warmup,
                language=language,
                validator=validator,
            )
            repeat_results[name] = result
            print(f"done ({result.min_time:.4f}s)")

        all_results.append(repeat_results)

        if repeat < n_full_repeats - 1:
            print(f"\nResting between repeats...")
            time.sleep(2)  # Allow system to cool down

    return all_results


def aggregate_suite_results(
    suite_results: List[Dict[str, BenchmarkResult]],
) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate results across multiple suite repeats.

    Computes mean and variance of the min times across repeats.
    """
    if not suite_results:
        return {}

    aggregated = {}
    benchmark_names = suite_results[0].keys()

    for name in benchmark_names:
        min_times = [r[name].min_time for r in suite_results]
        mean_times = [r[name].mean_time for r in suite_results]

        aggregated[name] = {
            "min_time_mean": np.mean(min_times),
            "min_time_std": np.std(min_times),
            "min_time_min": np.min(min_times),
            "min_time_max": np.max(min_times),
            "mean_time_mean": np.mean(mean_times),
            "mean_time_std": np.std(mean_times),
            "n_repeats": len(suite_results),
            "individual_results": [r[name].to_dict() for r in suite_results],
        }

    return aggregated


if __name__ == "__main__":
    # Quick test
    print("Academic Benchmarking Utilities v1.0")
    print(f"scipy available: {SCIPY_AVAILABLE}")
    print(f"Available CPU cores: {get_available_cores()}")

    # Test CPU freq
    freq = get_current_cpu_freq()
    print(f"Current CPU freq: {freq:.0f} MHz")

    # Test benchmark
    def test_func():
        _ = sum(range(10000))

    result = run_benchmark_with_stats(test_func, name="test", runs=10, warmup=2)
    print(f"\nTest result: {result.min_time:.6f}s")
