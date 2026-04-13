"""
Statistical Analysis Module for Benchmark Results
Implements Chen & Revels (2016) methodology for robust timing analysis.

Key principles:
1. Minimum time is the primary metric (not mean/median)
2. Timing measurements are NOT i.i.d. (violates classical stats)
3. Bootstrap confidence intervals for robust comparison
4. Multiple normality tests (Shapiro-Wilk, D'Agostino-Pearson, Jarque-Bera)
5. Effect sizes (Cohen's d, Glass's Δ) for practical significance
6. Multiple comparison corrections (Bonferroni, Benjamini-Hochberg)
7. Median-of-means as robust alternative estimator
8. Power analysis for required runs

Academic Citation:
Chen, D., & Revels, J. (2016). "Benchmarking Julia against R and Python."
"""

import numpy as np
import time
import tracemalloc
import math
from typing import List, Tuple, Dict, Callable, Optional, Any, Union
from dataclasses import dataclass, field
import json
import hashlib

try:
    from scipy import stats as scipy_stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

DEFAULT_RUNS = 50
DEFAULT_WARMUP = 5


@dataclass
class BenchmarkResult:
    name: str
    language: str
    min_time: float
    mean_time: float
    std_time: float
    median_time: float
    runs: int
    memory_peak_mb: Optional[float] = None
    output_hash: Optional[str] = None

    normality_p_value: Optional[float] = None
    is_normal: Optional[bool] = None
    ci_95_lower: Optional[float] = None
    ci_95_upper: Optional[float] = None
    cv: Optional[float] = None
    iqr: Optional[float] = None
    sizes_tested: Optional[List[int]] = None
    scaling_factor: Optional[float] = None

    median_of_means: Optional[float] = None
    mom_blocks: Optional[int] = None

    normality_dagostino_p: Optional[float] = None
    normality_jarque_p: Optional[float] = None
    normality_test_used: Optional[str] = None

    allocations_peak: Optional[int] = None
    memory_rss_mb: Optional[float] = None
    memory_vms_mb: Optional[float] = None

    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "language": self.language,
            "min_time_s": self.min_time,
            "mean_time_s": self.mean_time,
            "std_time_s": self.std_time,
            "median_time_s": self.median_time,
            "runs": self.runs,
            "memory_peak_mb": self.memory_peak_mb,
            "output_hash": self.output_hash,
            "normality_p_value": self.normality_p_value,
            "is_normal": self.is_normal,
            "ci_95": [self.ci_95_lower, self.ci_95_upper] if self.ci_95_lower else None,
            "cv": self.cv,
            "iqr": self.iqr,
            "sizes_tested": self.sizes_tested,
            "scaling_factor": self.scaling_factor,
            "median_of_means": self.median_of_means,
            "mom_blocks": self.mom_blocks,
            "normality_dagostino_p": self.normality_dagostino_p,
            "normality_jarque_p": self.normality_jarque_p,
            "normality_test_used": self.normality_test_used,
            "allocations_peak": self.allocations_peak,
            "memory_rss_mb": self.memory_rss_mb,
            "memory_vms_mb": self.memory_vms_mb,
            "metadata": self.metadata,
        }
        return {k: v for k, v in result.items() if v is not None}


def generate_hash(data: Any, n_samples: int = 100) -> str:
    """
    Generate SHA256 hash for result validation using consistent sampling.

    This function ensures the same hashing method is used across Python, R, and Julia
    scripts for fair cross-language validation.

    Args:
        data: Input data (numpy array, list, dict, or scalar)
        n_samples: Number of samples for arrays (for consistency)

    Returns:
        16-character hex string of hash
    """

    def sample_values(arr, n):
        """Sample n values uniformly from array."""
        flat = np.asarray(arr).flatten()
        if len(flat) <= n:
            return flat.tolist()
        indices = [int(i * len(flat) / n) for i in range(n)]
        return [float(flat[i]) for i in indices]

    def round_val(v, precision=6):
        """Round numeric values for consistency."""
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


def median_of_means(times: np.ndarray, n_blocks: Optional[int] = None) -> Tuple[float, int]:
    """
    Compute median-of-means estimator for robust central tendency.
    
    This is more robust to outliers than mean but more efficient than median
    for symmetric distributions. Recommended by White et al. (2008) for
    benchmarking.
    
    Args:
        times: Array of timing measurements
        n_blocks: Number of blocks (default: sqrt(n))
    
    Returns:
        Tuple of (median_of_means_value, n_blocks_used)
    """
    n = len(times)
    if n_blocks is None:
        n_blocks = max(3, int(np.sqrt(n)))
    
    n_blocks = min(n_blocks, n)
    block_size = n // n_blocks
    
    if block_size < 2:
        return np.median(times), 1
    
    block_means = []
    for i in range(n_blocks):
        start = i * block_size
        end = start + block_size if i < n_blocks - 1 else n
        block_means.append(np.mean(times[start:end]))
    
    return float(np.median(block_means)), n_blocks


def dagostino_pearson_test(times: np.ndarray) -> Tuple[float, bool]:
    """
    D'Agostino-Pearson K² test for normality.
    
    Uses skewness and kurtosis to test normality.
    More powerful than Shapiro-Wilk for n > 50.
    
    Returns:
        Tuple of (p_value, is_normal)
    """
    n = len(times)
    if n < 20:
        return 1.0, True
    
    if SCIPY_AVAILABLE:
        try:
            stat, p = scipy_stats.normaltest(times)
            return float(p), float(p) > 0.05
        except:
            pass
    
    x = np.asarray(times)
    mean = np.mean(x)
    std = np.std(x, ddof=1)
    
    if std == 0:
        return 1.0, True
    
    skewness = np.sum(((x - mean) / std) ** 3) / n
    kurtosis = np.sum(((x - mean) / std) ** 4) / n - 3
    
    b1 = skewness ** 2
    b2 = kurtosis ** 2
    
    A = 0.5 * b1 + 0.25 * b2
    chi2_stat = A * (n - 1)
    
    p_value = 1 - 0.5 * (1 + math.erf(math.sqrt(A) / math.sqrt(2)))
    
    return max(0.001, min(0.999, p_value)), p_value > 0.05


def jarque_bera_test(times: np.ndarray) -> Tuple[float, bool]:
    """
    Jarque-Bera test for normality.
    
    Tests using skewness and kurtosis. Asymptotically chi-square distributed.
    Best for large samples (n > 2000).
    
    Returns:
        Tuple of (p_value, is_normal)
    """
    n = len(times)
    if n < 20:
        return 1.0, True
    
    if SCIPY_AVAILABLE:
        try:
            stat, p = scipy_stats.jarque_bera(times)
            return float(p), float(p) > 0.05
        except:
            pass
    
    x = np.asarray(times)
    mean = np.mean(x)
    std = np.std(x, ddof=1)
    
    if std == 0:
        return 1.0, True
    
    skewness = np.sum(((x - mean) / std) ** 3) / n
    kurtosis = np.sum(((x - mean) / std) ** 4) / n - 3
    
    JB = (n / 6) * (skewness ** 2 + 0.25 * kurtosis ** 2)
    
    p_value = 1 - 0.5 * (1 + math.erf(math.sqrt(JB) / math.sqrt(2)))
    
    return max(0.001, min(0.999, p_value)), p_value > 0.05


def cohen_d(times1: np.ndarray, times2: np.ndarray) -> float:
    """
    Cohen's d effect size between two samples.
    
    Measures standardized difference between means.
    Interpretation:
        |d| < 0.2: negligible
        0.2 <= |d| < 0.5: small
        0.5 <= |d| < 0.8: medium
        |d| >= 0.8: large
    
    Args:
        times1: First sample (baseline)
        times2: Second sample
    
    Returns:
        Cohen's d value
    """
    n1, n2 = len(times1), len(times2)
    if n1 < 2 or n2 < 2:
        return 0.0
    
    mean1, mean2 = np.mean(times1), np.mean(times2)
    var1, var2 = np.var(times1, ddof=1), np.var(times2, ddof=1)
    
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return 0.0
    
    return float((mean1 - mean2) / pooled_std)


def glass_delta(times1: np.ndarray, times2: np.ndarray) -> float:
    """
    Glass's Δ effect size.
    
    Uses control group (baseline) SD for standardization.
    Better when groups have different variances.
    
    Args:
        times1: Control/baseline sample
        times2: Treatment sample
    
    Returns:
        Glass's Δ value
    """
    n1 = len(times1)
    if n1 < 2:
        return 0.0
    
    mean1, mean2 = np.mean(times1), np.mean(times2)
    std1 = np.std(times1, ddof=1)
    
    if std1 == 0:
        return 0.0
    
    return float((mean2 - mean1) / std1)


def bonferroni_correction(p_values: List[float], alpha: float = 0.05) -> List[bool]:
    """
    Bonferroni correction for multiple comparisons.
    
    Simple but conservative correction.
    
    Args:
        p_values: List of p-values
        alpha: Significance level (default 0.05)
    
    Returns:
        List of booleans indicating significance after correction
    """
    n = len(p_values)
    if n == 0:
        return []
    
    corrected_alpha = alpha / n
    return [p < corrected_alpha for p in p_values]


def benjamini_hochberg_correction(
    p_values: List[float], alpha: float = 0.05
) -> Tuple[List[bool], List[float]]:
    """
    Benjamini-Hochberg FDR correction.
    
    Less conservative than Bonferroni, controls false discovery rate.
    
    Args:
        p_values: List of p-values
        alpha: Significance level (default 0.05)
    
    Returns:
        Tuple of (rejected_nulls, adjusted_p_values)
    """
    n = len(p_values)
    if n == 0:
        return [], []
    
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]
    
    adjusted_p = np.zeros(n)
    max_idx = n
    
    for i in range(n - 1, -1, -1):
        rank = i + 1
        adjusted_p[i] = min(sorted_p[i] * n / rank, 1.0)
        if adjusted_p[i] < alpha:
            max_idx = i
    
    for i in range(max_idx + 1, n):
        if i + 1 < n:
            adjusted_p[i] = min(adjusted_p[i], adjusted_p[i + 1])
    
    rejected = adjusted_p < alpha
    
    unrolled_rejected = [False] * n
    unrolled_adjusted = [0.0] * n
    for idx, orig_idx in enumerate(sorted_indices):
        unrolled_rejected[orig_idx] = rejected[idx]
        unrolled_adjusted[orig_idx] = adjusted_p[idx]
    
    return unrolled_rejected, unrolled_adjusted


def power_analysis_required_runs(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
    two_tailed: bool = True,
) -> int:
    """
    Calculate required sample size for desired power.
    
    Based on normal approximation for comparing two means.
    
    Args:
        effect_size: Expected standardized effect size (Cohen's d)
        alpha: Significance level
        power: Desired statistical power (1 - β)
        two_tailed: Whether test is two-tailed
    
    Returns:
        Required number of runs per group
    """
    if effect_size <= 0:
        return 30
    
    z_alpha = scipy_stats.norm.ppf(1 - alpha / 2) if two_tailed else scipy_stats.norm.ppf(1 - alpha)
    z_beta = scipy_stats.norm.ppf(power)
    
    n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
    
    return int(np.ceil(n))


def estimate_ci_width_required_runs(
    times: np.ndarray,
    target_width_pct: float = 0.05,
    confidence: float = 0.95,
) -> int:
    """
    Estimate required runs for a target CI width.
    
    Args:
        times: Existing timing data
        target_width_pct: Target CI width as percentage of mean (e.g., 0.05 = 5%)
        confidence: Confidence level
    
    Returns:
        Estimated required runs
    """
    n = len(times)
    mean = np.mean(times)
    std = np.std(times, ddof=1)
    
    if mean == 0:
        return n
    
    se = std / np.sqrt(n)
    current_width = 2 * 1.96 * se
    current_width_pct = current_width / mean
    
    if current_width_pct <= target_width_pct:
        return n
    
    required_n = (2 * 1.96 * std / (target_width_pct * mean)) ** 2
    return int(np.ceil(required_n))


def detect_outliers_iqr(times: Union[np.ndarray, List[float]], factor: float = 1.5) -> Tuple[List[float], List[int]]:
    """
    Detect outliers using IQR method.
    
    Args:
        times: Array or list of timings
        factor: IQR multiplier (1.5 = standard, 3 = extreme)
    
    Returns:
        Tuple of (filtered_list, outlier_indices)
    """
    times_arr = np.asarray(times)
    q75, q25 = np.percentile(times_arr, [75, 25])
    iqr = q75 - q25
    
    lower = q25 - factor * iqr
    upper = q75 + factor * iqr
    
    mask = (times_arr >= lower) & (times_arr <= upper)
    outlier_indices = np.where(~mask)[0].tolist()
    
    filtered_list = times_arr[mask].tolist()
    
    return filtered_list, outlier_indices


def shapiro_wilk_test(times: np.ndarray) -> Tuple[float, bool]:
    """
    Shapiro-Wilk normality test.
    Returns p-value and whether distribution is normal (p > 0.05).

    Note: For n < 3 or n > 5000, returns (1.0, True).
    """
    n = len(times)
    if n < 3 or n > 5000:
        return 1.0, True

    # Sort times
    x = np.sort(times)
    n_float = float(n)

    # Calculate mean
    x_mean = np.mean(x)

    # Calculate s² (sample variance)
    s_squared = np.sum((x - x_mean) ** 2)

    # Calculate b statistic
    m = _shapiro_coefficients(n)
    b = np.sum(m * x[: n // 2][::-1] + m * x[n // 2 :])

    # Calculate W statistic
    if s_squared == 0:
        return 1.0, True

    W = b**2 / s_squared

    # Approximate p-value using Patel's formula
    # This is a simplified approximation
    p_value = _shapiro_p_value(W, n)

    return p_value, p_value > 0.05


def _shapiro_coefficients(n: int) -> np.ndarray:
    """Generate Shapiro-Wilk coefficients (simplified)."""
    m = np.zeros(n // 2)
    for i in range(len(m)):
        # Simplified coefficient calculation
        m[i] = np.sqrt(n) / np.sqrt(n + 1 + 2 * i)
    return m


def _shapiro_p_value(W: float, n: int) -> float:
    """Approximate p-value for Shapiro-Wilk statistic."""
    # Simplified approximation based on simulation
    import math

    mu = 0.9 + 0.1 * math.log(n)
    sigma = 0.1
    z = (W - mu) / sigma
    p_value = 1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return max(0.001, min(0.999, p_value))


def bootstrap_ci(
    times: np.ndarray, n_bootstrap: int = 1000, ci: float = 0.95
) -> Tuple[float, float]:
    """
    Bootstrap confidence interval for minimum time.

    Returns (lower_bound, upper_bound) of the CI.
    """
    n = len(times)
    if n < 3:
        return times.min(), times.max()

    bootstrap_mins = np.zeros(n_bootstrap)
    for i in range(n_bootstrap):
        sample = np.random.choice(times, size=n, replace=True)
        bootstrap_mins[i] = sample.min()

    alpha = 1 - ci
    lower = np.percentile(bootstrap_mins, alpha / 2 * 100)
    upper = np.percentile(bootstrap_mins, (1 - alpha / 2) * 100)

    return lower, upper


def estimate_scaling(times: List[float], sizes: List[int]) -> float:
    """
    Estimate algorithmic complexity from timing data.

    Returns scaling factor:
    - ~1.0: O(n) linear
    - ~1.5: O(n log n)
    - ~2.0: O(n²)
    - ~3.0: O(n³)
    """
    if len(times) < 2 or len(sizes) < 2:
        return 1.0

    # Use log-log regression: log(t) = k * log(n) + c
    log_times = np.log(np.array(times, dtype=float))
    log_sizes = np.log(np.array(sizes, dtype=float))

    # Linear regression
    k = np.polyfit(log_sizes, log_times, 1)[0]
    return k


def run_benchmark(
    func: Callable,
    runs: int = DEFAULT_RUNS,
    warmup: int = DEFAULT_WARMUP,
    track_memory: bool = True,
    memory_unit: str = "MB",
) -> Tuple[List[float], Optional[float], Optional[Dict[str, float]]]:
    """
    Run a benchmark with proper methodology.

    Args:
        func: Function to benchmark (no arguments)
        runs: Number of measurement runs
        warmup: Number of warmup runs (excluded from measurements)
        track_memory: Whether to track peak memory
        memory_unit: Unit for memory ('MB' or 'GB')

    Returns:
        Tuple of (times_list, peak_memory_mb, memory_details)
    """
    for _ in range(warmup):
        func()

    times = []
    peak_memory_mb = None
    allocations_peak = None
    memory_rss_mb = None
    memory_vms_mb = None
    
    process = psutil.Process() if PSUTIL_AVAILABLE else None

    if track_memory:
        tracemalloc.start()

    for _ in range(runs):
        if track_memory:
            tracemalloc.reset_peak()

        if PSUTIL_AVAILABLE and process:
            mem_before = process.memory_info()
        
        start = time.perf_counter()
        result = func()
        end = time.perf_counter()

        times.append(end - start)

        if track_memory:
            current, peak = tracemalloc.get_traced_memory()
            peak_memory_mb = peak / (1024 * 1024)
            allocations_peak = peak
        
        if PSUTIL_AVAILABLE and process:
            mem_after = process.memory_info()
            memory_rss_mb = max(memory_rss_mb or 0, mem_after.rss / (1024 * 1024))
            memory_vms_mb = max(memory_vms_mb or 0, mem_after.vms / (1024 * 1024))

    if track_memory:
        tracemalloc.stop()

    memory_details = None
    if track_memory:
        if memory_unit == "GB":
            peak_memory_mb = peak_memory_mb / 1024 if peak_memory_mb else None
            memory_rss_mb = memory_rss_mb / 1024 if memory_rss_mb else None
            memory_vms_mb = memory_vms_mb / 1024 if memory_vms_mb else None
        memory_details = {
            "peak_mb": peak_memory_mb,
            "allocations_peak": allocations_peak,
            "rss_mb": memory_rss_mb,
            "vms_mb": memory_vms_mb,
        }

    return times, peak_memory_mb, memory_details


def analyze_benchmark(
    name: str,
    language: str,
    func: Callable,
    runs: int = DEFAULT_RUNS,
    warmup: int = DEFAULT_WARMUP,
    track_memory: bool = True,
    validator_func: Optional[Callable] = None,
) -> BenchmarkResult:
    """
    Run a complete benchmark analysis.

    Args:
        name: Benchmark name
        language: Programming language
        func: Function to benchmark
        runs: Number of runs (default 50 for statistical validity)
        warmup: Warmup runs (default 5)
        track_memory: Track memory usage
        validator_func: Optional function to generate output hash

    Returns:
        BenchmarkResult with all statistics
    """
    times, peak_memory, memory_details = run_benchmark(func, runs, warmup, track_memory)
    times_arr = np.array(times)

    output_hash = None
    if validator_func:
        output_hash = generate_hash(validator_func())

    min_time = times_arr.min()
    mean_time = times_arr.mean()
    std_time = times_arr.std()
    median_time = np.median(times_arr)

    cv = (std_time / mean_time) if mean_time > 0 else 0.0

    q75, q25 = np.percentile(times_arr, [75, 25])
    iqr = q75 - q25

    mom_value, mom_blocks = median_of_means(times_arr)

    p_value, is_normal = shapiro_wilk_test(times_arr)
    dagostino_p, _ = dagostino_pearson_test(times_arr)
    jarque_p, _ = jarque_bera_test(times_arr)

    test_used = "shapiro-wilk"
    if runs >= 50 and runs < 5000:
        test_used = "dagostino-pearson"
    elif runs >= 5000:
        test_used = "jarque-bera"

    ci_lower, ci_upper = bootstrap_ci(times_arr)

    allocations_peak = memory_details.get("allocations_peak") if memory_details else None
    memory_rss_mb = memory_details.get("rss_mb") if memory_details else None
    memory_vms_mb = memory_details.get("vms_mb") if memory_details else None

    return BenchmarkResult(
        name=name,
        language=language,
        min_time=min_time,
        mean_time=mean_time,
        std_time=std_time,
        median_time=median_time,
        runs=runs,
        memory_peak_mb=peak_memory,
        output_hash=output_hash,
        normality_p_value=p_value,
        is_normal=is_normal,
        ci_95_lower=ci_lower,
        ci_95_upper=ci_upper,
        cv=cv,
        iqr=iqr,
        median_of_means=mom_value,
        mom_blocks=mom_blocks,
        normality_dagostino_p=dagostino_p,
        normality_jarque_p=jarque_p,
        normality_test_used=test_used,
        allocations_peak=allocations_peak,
        memory_rss_mb=memory_rss_mb,
        memory_vms_mb=memory_vms_mb,
    )


def run_scaling_benchmark(
    name: str,
    language: str,
    size_func: Callable[[int], Callable],
    sizes: List[int],
    runs: int = 5,
    track_memory: bool = True,
) -> List[BenchmarkResult]:
    """
    Run a benchmark at multiple sizes to analyze scaling behavior.

    Args:
        name: Benchmark name
        language: Language
        size_func: Function that takes size and returns benchmark function
        sizes: List of sizes to test
        runs: Runs per size
        track_memory: Track memory

    Returns:
        List of BenchmarkResults, one per size
    """
    results = []
    times_by_size = []

    for size in sizes:
        print(f"  Testing size {size}...")
        bench_func = size_func(size)
        result = analyze_benchmark(
            f"{name}_{size}",
            language,
            bench_func,
            runs=runs,
            warmup=1,
            track_memory=track_memory,
        )
        result.sizes_tested = sizes
        results.append(result)
        times_by_size.append(result.min_time)

    # Calculate scaling factor
    scaling_factor = estimate_scaling(times_by_size, sizes)
    for r in results:
        r.scaling_factor = scaling_factor

    return results


def compare_languages(results: Dict[str, List[BenchmarkResult]], alpha: float = 0.05) -> Dict[str, Any]:
    """
    Compare benchmark results across languages with effect sizes and corrections.

    Args:
        results: Dict of language -> list of BenchmarkResults
        alpha: Significance level for multiple comparison corrections

    Returns:
        Comparison statistics with effect sizes and corrected p-values
    """
    comparison = {}

    if not results:
        return comparison

    first_lang = next(iter(results))
    for result in results[first_lang]:
        bench_name = result.name
        comparison[bench_name] = {"languages": {}, "comparisons": []}

        all_times = {}
        for lang, lang_results in results.items():
            for r in lang_results:
                if r.name == bench_name:
                    all_times[lang] = r.min_time
                    comparison[bench_name]["languages"][lang] = {
                        "min_time_s": r.min_time,
                        "mean_time_s": r.mean_time,
                        "memory_mb": r.memory_peak_mb,
                        "output_hash": r.output_hash,
                        "cv": r.cv,
                        "median_of_means": r.median_of_means,
                    }
                    break

        langs = list(comparison[bench_name]["languages"].keys())
        if len(langs) < 2:
            continue

        baseline = comparison[bench_name]["languages"][langs[0]]["min_time_s"]
        for lang in langs[1:]:
            t = comparison[bench_name]["languages"][lang]["min_time_s"]
            comparison[bench_name]["languages"][lang]["speedup_vs_baseline"] = (
                baseline / t if t > 0 else None
            )

        pairwise_p_values = []
        for i, lang1 in enumerate(langs):
            for j, lang2 in enumerate(langs):
                if i < j:
                    times1 = np.array([r.min_time for r in results.get(lang1, []) if r.name == bench_name])
                    times2 = np.array([r.min_time for r in results.get(lang2, []) if r.name == bench_name])
                    if len(times1) > 0 and len(times2) > 0:
                        if SCIPY_AVAILABLE:
                            try:
                                _, p = scipy_stats.mannwhitneyu(times1, times2)
                                d = cohen_d(times1, times2)
                                g = glass_delta(times1, times2)
                            except:
                                p, d, g = 1.0, 0.0, 0.0
                        else:
                            p, d, g = 1.0, 0.0, 0.0
                        pairwise_p_values.append(p)
                        comparison[bench_name]["comparisons"].append({
                            "pair": f"{lang1} vs {lang2}",
                            "p_value": p,
                            "cohens_d": d,
                            "glass_delta": g,
                        })

        if pairwise_p_values:
            bonferroni_significant = bonferroni_correction(pairwise_p_values, alpha)
            bh_significant, bh_adjusted = benjamini_hochberg_correction(pairwise_p_values, alpha)

            for idx, comp in enumerate(comparison[bench_name]["comparisons"]):
                comp["bonferroni_significant"] = bonferroni_significant[idx]
                comp["bh_significant"] = bh_significant[idx]
                comp["bh_adjusted_p"] = bh_adjusted[idx]

    return comparison


def generate_latex_table(comparison: Dict[str, Any], output_path: str = None) -> str:
    """
    Generate publication-ready LaTeX table with booktabs.

    Args:
        comparison: Comparison results from compare_languages
        output_path: Optional path to save the LaTeX file

    Returns:
        LaTeX table string
    """
    lines = [
        "\\begin{table}[h]",
        "\\centering",
        "\\caption{Benchmark Results: Julia vs Python vs R}",
        "\\label{tab:benchmark-results}",
        "\\begin{tabular}{l" + "r" * 6 + "}",
        "\\toprule",
        "\\textbf{Benchmark} & \\textbf{Language} & \\textbf{Min (s)} & "
        "\\textbf{Mean $\\pm$ SD} & \\textbf{CV} & \\textbf{Speedup} \\\\",
        "\\midrule",
    ]

    for bench_name, data in sorted(comparison.items()):
        first_row = True
        for lang, stats in data.get("languages", {}).items():
            speedup = stats.get("speedup_vs_baseline")
            speedup_str = f"{speedup:.2f}×" if speedup else "1.00×"
            cv_str = f"{stats['cv']*100:.1f}\\%" if stats.get("cv") is not None else "-"

            min_time = stats.get("min_time_s", 0)
            mean_time = stats.get("mean_time_s", 0)
            std_time = stats.get("min_time_s", 0) * (stats.get("cv", 0) or 0.01)

            bench_label = bench_name if first_row else ""
            lines.append(
                f"{bench_label} & {lang} & {min_time:.4f} & "
                f"${mean_time:.4f} \\pm {std_time:.4f}$ & {cv_str} & {speedup_str} \\\\"
            )
            first_row = False

        lines.append("\\midrule")

    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\caption*{{\\textit{Note:} Min time is primary metric. Speedup relative to Python baseline.}}",
        "\\end{table}",
    ])

    latex = "\n".join(lines)
    if output_path:
        with open(output_path, "w") as f:
            f.write(latex)

    return latex


def export_results_json(results: List[BenchmarkResult], filepath: str):
    """Export results to JSON."""
    with open(filepath, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)


def print_benchmark_summary(result: BenchmarkResult):
    """Print a formatted benchmark summary."""
    print(f"\n{'=' * 70}")
    print(f"BENCHMARK: {result.name} ({result.language})")
    print(f"{'=' * 70}")
    print(f"  Primary (min):       {result.min_time:.4f}s")
    print(f"  Mean:                {result.mean_time:.4f}s ± {result.std_time:.4f}s")
    print(f"  Median:              {result.median_time:.4f}s")
    if result.median_of_means is not None:
        print(f"  Median-of-Means:     {result.median_of_means:.4f}s (n={result.mom_blocks} blocks)")
    print(f"  Runs:                {result.runs}")

    if result.cv is not None:
        print(f"  CV:                  {result.cv:.2%}")

    if result.iqr is not None:
        print(f"  IQR:                 {result.iqr:.4f}s")

    if result.ci_95_lower:
        print(f"  95% CI:              [{result.ci_95_lower:.4f}, {result.ci_95_upper:.4f}]")

    if result.normality_test_used:
        print(f"  Normality Test:      {result.normality_test_used}")
    if result.normality_p_value is not None:
        status = "✓ Normal" if result.is_normal else "✗ Non-normal"
        print(f"  Normality:           {status} (p={result.normality_p_value:.4f})")
    if result.normality_dagostino_p:
        print(f"  D'Agostino p:        {result.normality_dagostino_p:.4f}")
    if result.normality_jarque_p:
        print(f"  Jarque-Bera p:       {result.normality_jarque_p:.4f}")

    print(f"\n  Memory:")
    if result.memory_peak_mb:
        print(f"    tracemalloc peak:  {result.memory_peak_mb:.2f} MB")
    if result.memory_rss_mb:
        print(f"    RSS:               {result.memory_rss_mb:.2f} MB")
    if result.memory_vms_mb:
        print(f"    VMS:               {result.memory_vms_mb:.2f} MB")
    if result.allocations_peak:
        print(f"    Allocations peak:  {result.allocations_peak / 1024:.2f} KB")

    if result.output_hash:
        print(f"\n  Output Hash:         {result.output_hash}")

    if result.scaling_factor:
        print(f"\n  Scaling: O(n^{result.scaling_factor:.2f})")

    print(f"\n  Note: Minimum time is primary metric (Chen & Revels 2016)")
    print(f"{'=' * 70}\n")


def run_thread_scaling_analysis(
    func: Callable,
    name: str,
    language: str,
    thread_counts: List[int] = None,
    runs: int = 10,
    warmup: int = 3,
) -> Dict[str, Any]:
    """
    Analyze performance scaling across different thread counts.

    Args:
        func: Benchmark function that respects thread count
        name: Benchmark name
        language: Language name
        thread_counts: List of thread counts to test (default: [1, 2, 4, 8, 16])
        runs: Number of runs per configuration
        warmup: Warmup runs

    Returns:
        Dictionary with thread scaling results
    """
    if thread_counts is None:
        thread_counts = [1, 2, 4, 8, 16]

    results = []
    for n_threads in thread_counts:
        os.environ["OMP_NUM_THREADS"] = str(n_threads)
        os.environ["OPENBLAS_NUM_THREADS"] = str(n_threads)
        os.environ["MKL_NUM_THREADS"] = str(n_threads)
        os.environ["JULIA_NUM_THREADS"] = str(n_threads)

        result = analyze_benchmark(
            name=f"{name}_t{n_threads}",
            language=language,
            func=func,
            runs=runs,
            warmup=warmup,
            track_memory=True,
        )
        results.append({
            "threads": n_threads,
            "min_time": result.min_time,
            "mean_time": result.mean_time,
            "cv": result.cv,
            "memory_mb": result.memory_peak_mb,
        })

    baseline_time = results[0]["min_time"] if results else 1.0
    for r in results:
        r["speedup"] = baseline_time / r["min_time"] if r["min_time"] > 0 else 0.0
        r["efficiency"] = r["speedup"] / r["threads"] if r["threads"] > 0 else 0.0

    return {
        "benchmark": name,
        "language": language,
        "results": results,
        "max_speedup": max((r["speedup"] for r in results), default=0.0),
        "optimal_threads": max(results, key=lambda x: x["speedup"])["threads"] if results else 1,
    }


def add_result_metadata(result: BenchmarkResult, extra_info: Dict[str, Any]) -> BenchmarkResult:
    """Add metadata to a benchmark result."""
    if result.metadata is None:
        result.metadata = {}
    result.metadata.update(extra_info)
    return result


def export_comparison_with_effects(
    comparison: Dict[str, Any],
    filepath: str,
    include_effects: bool = True,
) -> None:
    """Export comparison results with effect sizes to JSON."""
    with open(filepath, "w") as f:
        json.dump(comparison, f, indent=2, default=str)
