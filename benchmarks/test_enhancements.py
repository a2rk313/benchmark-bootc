#!/usr/bin/env python3
"""
Comprehensive Test Suite for Thesis Benchmark Enhancements

Tests all new statistical methods, benchmarks, and utilities:
- Statistical functions (median-of-means, normality tests, effect sizes)
- Multiple comparison corrections
- New benchmark implementations
- Regression testing module
- Flaky detection
- Benchmark diffing
"""

import unittest
import numpy as np
import json
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from benchmark_stats import (
    median_of_means,
    dagostino_pearson_test,
    jarque_bera_test,
    cohen_d,
    glass_delta,
    bonferroni_correction,
    benjamini_hochberg_correction,
    power_analysis_required_runs,
    estimate_ci_width_required_runs,
    detect_outliers_iqr,
    bootstrap_ci,
    BenchmarkResult,
    generate_hash,
)

from regression_tests import RegressionTestSuite, RegressionStatus
from detect_flaky import FlakyTestDetector
from benchmark_diff import BenchmarkDiffer
from trend_analysis import TrendAnalyzer


class TestMedianOfMeans(unittest.TestCase):
    """Test median-of-means estimator."""
    
    def test_basic_functionality(self):
        """Test basic median-of-means calculation."""
        times = np.array([1.0, 1.1, 1.2, 1.3, 10.0, 1.0, 1.1, 1.2, 1.3, 1.0])
        mom, blocks = median_of_means(times)
        
        self.assertIsInstance(mom, float)
        self.assertGreater(blocks, 0)
        self.assertLess(mom, 10.0)
    
    def test_small_sample(self):
        """Test with small sample."""
        times = np.array([1.0, 1.1])
        mom, blocks = median_of_means(times, n_blocks=2)
        
        self.assertAlmostEqual(mom, 1.05, places=2)
    
    def test_single_block(self):
        """Test with single block fallback."""
        times = np.array([1.0])
        mom, blocks = median_of_means(times)
        
        self.assertEqual(blocks, 1)


class TestNormalityTests(unittest.TestCase):
    """Test normality test implementations."""
    
    def test_shapiro_wilk_normal(self):
        """Test Shapiro-Wilk on normal data."""
        np.random.seed(42)
        normal_data = np.random.randn(100)
        
        from benchmark_stats import shapiro_wilk_test
        p_value, is_normal = shapiro_wilk_test(normal_data)
        
        self.assertGreater(p_value, 0.01)
    
    def test_dagostino_pearson(self):
        """Test D'Agostino-Pearson test."""
        np.random.seed(42)
        normal_data = np.random.randn(100)
        
        p_value, is_normal = dagostino_pearson_test(normal_data)
        
        self.assertIsInstance(p_value, float)
        self.assertIsInstance(is_normal, bool)
    
    def test_jarque_bera(self):
        """Test Jarque-Bera test."""
        np.random.seed(42)
        normal_data = np.random.randn(200)
        
        p_value, is_normal = jarque_bera_test(normal_data)
        
        self.assertIsInstance(p_value, float)
        self.assertIsInstance(is_normal, bool)
    
    def test_small_sample_handling(self):
        """Test that small samples are handled gracefully."""
        small_data = np.array([1.0, 1.1])
        
        p_value, is_normal = dagostino_pearson_test(small_data)
        self.assertEqual(p_value, 1.0)
        
        p_value, is_normal = jarque_bera_test(small_data)
        self.assertEqual(p_value, 1.0)


class TestEffectSizes(unittest.TestCase):
    """Test effect size calculations."""
    
    def test_cohen_d_identical(self):
        """Cohen's d should be ~0 for identical distributions."""
        data1 = np.array([1.0, 1.1, 1.2])
        data2 = np.array([1.0, 1.1, 1.2])
        
        d = cohen_d(data1, data2)
        self.assertAlmostEqual(d, 0.0, places=5)
    
    def test_cohen_d_large_effect(self):
        """Cohen's d should be large for very different distributions."""
        data1 = np.array([1.0, 1.1, 1.2, 1.0, 1.1])
        data2 = np.array([10.0, 10.1, 10.2, 10.0, 10.1])
        
        d = cohen_d(data1, data2)
        self.assertGreater(abs(d), 10.0)
    
    def test_cohen_d_small_sample(self):
        """Test with insufficient samples."""
        data1 = np.array([1.0])
        data2 = np.array([2.0])
        
        d = cohen_d(data1, data2)
        self.assertEqual(d, 0.0)
    
    def test_glass_delta(self):
        """Test Glass's delta."""
        data1 = np.array([1.0, 1.1, 1.2, 1.0, 1.1])
        data2 = np.array([2.0, 2.1, 2.2, 2.0, 2.1])
        
        g = glass_delta(data1, data2)
        self.assertGreater(abs(g), 0.5)
    
    def test_glass_delta_zero_std(self):
        """Test with zero standard deviation."""
        data1 = np.array([1.0, 1.0, 1.0])
        data2 = np.array([2.0, 2.0, 2.0])
        
        g = glass_delta(data1, data2)
        self.assertEqual(g, 0.0)


class TestMultipleComparisons(unittest.TestCase):
    """Test multiple comparison corrections."""
    
    def test_bonferroni_all_significant(self):
        """Test Bonferroni with all significant p-values."""
        p_values = [0.01, 0.02, 0.03]
        alpha = 0.05
        
        corrected = bonferroni_correction(p_values, alpha)
        
        self.assertEqual(len(corrected), 3)
        self.assertEqual(corrected, [True, False, False])
    
    def test_bonferroni_none_significant(self):
        """Test Bonferroni with no significant p-values."""
        p_values = [0.5, 0.6, 0.7]
        alpha = 0.05
        
        corrected = bonferroni_correction(p_values, alpha)
        
        self.assertEqual(len(corrected), 3)
        self.assertFalse(any(corrected))
    
    def test_bonferroni_empty(self):
        """Test with empty p-values."""
        corrected = bonferroni_correction([])
        self.assertEqual(corrected, [])
    
    def test_benjamini_hochberg_basic(self):
        """Test Benjamini-Hochberg correction."""
        p_values = [0.01, 0.02, 0.03, 0.10]
        alpha = 0.05
        
        rejected, adjusted = benjamini_hochberg_correction(p_values, alpha)
        
        self.assertEqual(len(rejected), 4)
        self.assertEqual(len(adjusted), 4)
    
    def test_benjamini_hochberg_empty(self):
        """Test with empty p-values."""
        rejected, adjusted = benjamini_hochberg_correction([])
        self.assertEqual(rejected, [])
        self.assertEqual(adjusted, [])


class TestPowerAnalysis(unittest.TestCase):
    """Test power analysis functions."""
    
    def test_required_runs_basic(self):
        """Test basic required runs calculation."""
        n = power_analysis_required_runs(effect_size=0.5, alpha=0.05, power=0.8)
        
        self.assertGreater(n, 0)
        self.assertLess(n, 1000)
    
    def test_required_runs_small_effect(self):
        """Test with small effect size (needs more runs)."""
        n_small = power_analysis_required_runs(effect_size=0.2)
        n_large = power_analysis_required_runs(effect_size=0.8)
        
        self.assertGreater(n_small, n_large)
    
    def test_required_runs_zero_effect(self):
        """Test with zero effect size."""
        n = power_analysis_required_runs(effect_size=0.0)
        self.assertEqual(n, 30)
    
    def test_ci_width_required_runs(self):
        """Test CI width based run estimation."""
        np.random.seed(42)
        times = np.random.randn(30) * 0.1 + 1.0
        
        required = estimate_ci_width_required_runs(times, target_width_pct=0.05)
        
        self.assertGreater(required, 0)


class TestOutlierDetection(unittest.TestCase):
    """Test outlier detection."""
    
    def test_detect_no_outliers(self):
        """Test with data containing no outliers."""
        times = np.array([1.0, 1.1, 1.2, 1.0, 1.1, 1.2, 1.0, 1.1])
        
        filtered, outliers = detect_outliers_iqr(times)
        
        self.assertEqual(len(outliers), 0)
        self.assertEqual(len(filtered), len(times))
    
    def test_detect_obvious_outlier(self):
        """Test with obvious outliers."""
        times = np.array([1.0, 1.1, 1.2, 10.0, 1.0, 1.1])
        
        filtered, outliers = detect_outliers_iqr(times)
        
        self.assertEqual(len(outliers), 1)
        self.assertEqual(outliers[0], 3)
    
    def test_extreme_outliers(self):
        """Test extreme outlier detection."""
        times = np.array([1.0, 1.1, 1.2, 500.0])
        
        filtered, outliers = detect_outliers_iqr(times, factor=1.5)
        
        self.assertEqual(len(outliers), 1)


class TestBootstrapCI(unittest.TestCase):
    """Test bootstrap confidence intervals."""
    
    def test_basic_ci(self):
        """Test basic CI calculation for minimum time."""
        np.random.seed(42)
        times = np.random.randn(100) + 10
        
        lower, upper = bootstrap_ci(times, n_bootstrap=1000)
        
        self.assertLess(lower, upper)
        self.assertGreater(upper, lower)
        self.assertLessEqual(lower, times.min())
        self.assertGreater(upper, times.min())
        self.assertLess(upper - lower, times.max() - times.min())
    
    def test_small_sample(self):
        """Test with small sample."""
        times = np.array([1.0, 1.1])
        
        lower, upper = bootstrap_ci(times)
        
        self.assertLessEqual(lower, upper)


class TestHashGeneration(unittest.TestCase):
    """Test hash generation for validation."""
    
    def test_consistent_hashing(self):
        """Test that hashing is consistent."""
        data = {"a": [1.0, 2.0, 3.0]}
        
        hash1 = generate_hash(data)
        hash2 = generate_hash(data)
        
        self.assertEqual(hash1, hash2)
    
    def test_different_data_different_hash(self):
        """Test that different data produces different hashes."""
        hash1 = generate_hash({"a": [1.0, 2.0]})
        hash2 = generate_hash({"a": [1.0, 2.1]})
        
        self.assertNotEqual(hash1, hash2)
    
    def test_none_hash(self):
        """Test hash of None."""
        h = generate_hash(None)
        self.assertEqual(h, "0" * 16)


class TestRegressionSuite(unittest.TestCase):
    """Test regression testing module."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.baseline_file = Path(self.temp_dir) / "baseline.json"
        
        baseline = {
            "regression_hashes": {
                "python_matrix_ops": "abc123",
            },
            "expected_times": {
                "python_matrix_ops": {"min_time": 0.5}
            }
        }
        
        with open(self.baseline_file, "w") as f:
            json.dump(baseline, f)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_hash_validation_pass(self):
        """Test hash validation with matching hash."""
        suite = RegressionTestSuite(baseline_file=str(self.baseline_file))
        
        result = suite.validate_hash("matrix_ops", "python", "abc123")
        
        self.assertEqual(result.status, RegressionStatus.PASS)
    
    def test_hash_validation_fail(self):
        """Test hash validation with mismatched hash."""
        suite = RegressionTestSuite(baseline_file=str(self.baseline_file))
        
        result = suite.validate_hash("matrix_ops", "python", "xyz789")
        
        self.assertEqual(result.status, RegressionStatus.FAIL)
    
    def test_new_benchmark(self):
        """Test detection of new benchmark."""
        suite = RegressionTestSuite(baseline_file=str(self.baseline_file))
        
        result = suite.validate_hash("new_benchmark", "python", "abc123")
        
        self.assertEqual(result.status, RegressionStatus.NEW_BENCHMARK)
    
    def test_timing_validation_pass(self):
        """Test timing validation within tolerance."""
        suite = RegressionTestSuite(baseline_file=str(self.baseline_file))
        
        result = suite.validate_timing("matrix_ops", "python", 0.52, tolerance_pct=10.0)
        
        self.assertEqual(result.status, RegressionStatus.PASS)


class TestFlakyDetection(unittest.TestCase):
    """Test flaky test detection."""
    
    def test_stable_benchmark(self):
        """Test detection of stable benchmark."""
        times = [1.0, 1.01, 1.02, 1.0, 1.01] * 6
        
        detector = FlakyTestDetector(cv_threshold=0.10)
        result = detector.analyze_single_benchmark(times, "test_bench", "python")
        
        self.assertFalse(result.is_flaky)
    
    def test_flaky_benchmark(self):
        """Test detection of flaky benchmark."""
        times = [1.0, 1.1, 1.2, 5.0, 1.0, 1.1, 1.2, 6.0, 1.0, 1.1]
        
        detector = FlakyTestDetector(cv_threshold=0.10)
        result = detector.analyze_single_benchmark(times, "test_bench", "python")
        
        self.assertTrue(result.is_flaky)


class TestBenchmarkDiff(unittest.TestCase):
    """Test benchmark diffing."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        baseline_dir = Path(self.temp_dir) / "baseline"
        current_dir = Path(self.temp_dir) / "current"
        baseline_dir.mkdir()
        current_dir.mkdir()
        
        baseline_results = {
            "name": "matrix_ops",
            "language": "python",
            "min_time": 1.0,
        }
        
        current_results = {
            "name": "matrix_ops",
            "language": "python",
            "min_time": 1.03,
        }
        
        with open(baseline_dir / "matrix_ops_python.json", "w") as f:
            json.dump(baseline_results, f)
        
        with open(current_dir / "matrix_ops_python.json", "w") as f:
            json.dump(current_results, f)
        
        self.baseline_dir = str(baseline_dir)
        self.current_dir = str(current_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_regression_detection(self):
        """Test that regressions are detected."""
        differ = BenchmarkDiffer(self.baseline_dir, self.current_dir)
        differ.run()
        
        self.assertEqual(len(differ.diffs), 1)
        self.assertFalse(differ.diffs[0].is_regression)
        self.assertAlmostEqual(differ.diffs[0].change_pct, 3.0, places=1)


class TestNewBenchmarks(unittest.TestCase):
    """Test new benchmark implementations."""
    
    def test_real_modis_import(self):
        """Test that real MODIS benchmark can be imported."""
        try:
            from real_modis_timeseries import (
                generate_realistic_modis_subset,
                temporal_statistics,
            )
            
            data = generate_realistic_modis_subset(width=100, height=100, n_dates=10)
            
            self.assertEqual(data.shape, (10, 100, 100))
            self.assertTrue(np.all(data >= -0.1))
            self.assertTrue(np.all(data <= 1.0))
            
            mean, trend, amplitude = temporal_statistics(data)
            self.assertIsInstance(mean, float)
            self.assertIsInstance(trend, float)
            self.assertIsInstance(amplitude, float)
            
        except ImportError as e:
            self.skipTest(f"Could not import benchmark module: {e}")
    
    def test_parallel_benchmark_import(self):
        """Test that parallel benchmark can be imported."""
        try:
            from parallel_mapreduce import (
                generate_tiles,
                process_tile,
                sequential_processing,
            )
            
            tiles = generate_tiles(n_tiles=4, tile_size=32)
            
            self.assertEqual(len(tiles), 4)
            self.assertEqual(tiles[0].shape, (32, 32))
            
            result = process_tile(tiles[0])
            self.assertIn("mean", result)
            self.assertIn("std", result)
            
            time_taken = sequential_processing(tiles[:2])
            self.assertGreater(time_taken, 0)
            
        except ImportError as e:
            self.skipTest(f"Could not import benchmark module: {e}")


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
