#!/usr/bin/env python3
"""
SCENARIO E: Raster Algebra & Band Math - Python Implementation
Tests: Band arithmetic, NDVI calculation, spectral indices

Academic rationale:
- Band math is fundamental to remote sensing analysis
- NDVI is the most widely used vegetation index
- Tests array operation performance and memory efficiency
"""

import os
import sys
import time
import json
import hashlib
import numpy as np
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from benchmark_stats import (
    generate_hash,
    shapiro_wilk_test,
    bootstrap_ci,
    run_benchmark,
    print_benchmark_summary,
)

HASH_SAMPLES = 100

OUTPUT_DIR = Path("validation")
RESULTS_DIR = Path("results")


def load_cuprite_bands():
    """Load Cuprite hyperspectral data as separate bands."""
    try:
        import scipy.io as sio

        mat_data = sio.loadmat("data/Cuprite.mat")
        data_key = [k for k in mat_data.keys() if not k.startswith("__")][0]
        data = mat_data[data_key]

        # Data may be stored as (rows, cols, bands) - transpose if needed
        if data.shape[0] != 512 and data.shape[2] == 512:
            data = np.transpose(data, (2, 0, 1))

        # Use specific bands for RGB+NIR simulation
        # Typical AVIRIS: Band 30 (560nm), Band 50 (670nm), Band 70 (780nm), Band 90 (900nm)
        band_560 = data[30, :, :].astype(np.float32)  # Green
        band_670 = data[50, :, :].astype(np.float32)  # Red
        band_780 = data[70, :, :].astype(np.float32)  # NIR
        band_900 = data[90, :, :].astype(np.float32)  # SWIR

        rows, cols = band_560.shape

        return {
            "green": band_560,
            "red": band_670,
            "nir": band_780,
            "swir": band_900,
            "shape": (data.shape[0], rows, cols),
        }
    except Exception as e:
        print(f"Warning: Could not load Cuprite data: {e}")
        print("Generating synthetic data instead...")
        rows, cols = 614, 512
        np.random.seed(42)
        return {
            "green": np.random.rand(rows, cols).astype(np.float32) * 1000,
            "red": np.random.rand(rows, cols).astype(np.float32) * 800,
            "nir": np.random.rand(rows, cols).astype(np.float32) * 2000,
            "swir": np.random.rand(rows, cols).astype(np.float32) * 1500,
            "shape": (4, rows, cols),
        }
    except Exception as e:
        print(f"Warning: Could not load Cuprite data: {e}")
        print("Generating synthetic data instead...")
        shape = (512, 614)
        np.random.seed(42)
        return {
            "green": np.random.rand(*shape).astype(np.float32) * 1000,
            "red": np.random.rand(*shape).astype(np.float32) * 800,
            "nir": np.random.rand(*shape).astype(np.float32) * 2000,
            "swir": np.random.rand(*shape).astype(np.float32) * 1500,
            "shape": (4, *shape),
        }


def benchmark_ndvi(nir, red):
    """Calculate NDVI: (NIR - Red) / (NIR + Red)"""
    numerator = nir - red
    denominator = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(denominator != 0, numerator / denominator, 0)
    return ndvi


def benchmark_band_arithmetic(green, red, nir, swir):
    """Test various band arithmetic operations."""
    results = {}

    # Basic arithmetic
    results["sum"] = green + red + nir + swir
    results["difference"] = nir - red
    results["ratio"] = np.where(red != 0, nir / red, 0)

    # EVI (Enhanced Vegetation Index)
    # EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
    blue = green * 0.8  # Approximate blue from green
    results["evi"] = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)

    # SAVI (Soil Adjusted Vegetation Index)
    # L = 0.5
    L = 0.5
    results["savi"] = ((nir - red) / (nir + red + L)) * (1 + L)

    # NDWI (Normalized Difference Water Index)
    results["ndwi"] = (green - nir) / (green + nir)

    # NBR (Normalized Burn Ratio)
    results["nbr"] = (nir - swir) / (nir + swir)

    return results


def benchmark_convolution_3x3(data):
    """Simple 3x3 mean filter (edge-preserving)."""
    from scipy.ndimage import uniform_filter

    return uniform_filter(data, size=3, mode="reflect")


def benchmark_terrain_metrics(dem):
    """Calculate terrain derivatives from DEM."""
    # Gradient (slope direction)
    dy, dx = np.gradient(dem)

    # Slope magnitude
    slope = np.sqrt(dx**2 + dy**2)

    # Aspect (direction of maximum slope)
    aspect = np.arctan2(dy, dx)

    return {"slope": slope, "aspect": aspect, "gradient_x": dx, "gradient_y": dy}


def run_raster_algebra_benchmark():
    """Main raster algebra benchmark."""
    print("=" * 70)
    print("PYTHON - Scenario E: Raster Algebra & Band Math")
    print("=" * 70)

    # Load data
    print("\n[1/4] Loading hyperspectral data...")
    bands = load_cuprite_bands()
    print(
        f"  ✓ Loaded {bands['shape'][0]} bands, shape: {bands['shape'][1:]} ({bands['shape'][1] * bands['shape'][2]:,} pixels)"
    )

    results = {}
    all_hashes = []

    # Benchmark NDVI
    print("\n[2/4] Testing NDVI calculation...")
    tracemalloc.start()

    def ndvi_task():
        return benchmark_ndvi(bands["nir"], bands["red"])

    times, peak = run_benchmark(ndvi_task, runs=10, warmup=2)
    ndvi_result = ndvi_task()
    ndvi_hash = generate_hash(ndvi_result)
    all_hashes.append(ndvi_hash)

    p_val, is_norm = shapiro_wilk_test(np.array(times))
    ci_lower, ci_upper = bootstrap_ci(np.array(times))

    print(f"  ✓ Min: {min(times):.4f}s (primary)")
    print(f"  ✓ Mean: {np.mean(times):.4f}s ± {np.std(times):.4f}s")
    print(f"  ✓ Peak memory: {peak:.2f} MB" if peak else "")
    print(f"  ✓ Hash: {ndvi_hash}")

    results["ndvi"] = {
        "min_time_s": min(times),
        "mean_time_s": np.mean(times),
        "std_time_s": np.std(times),
        "peak_memory_mb": peak,
        "normality_p": p_val,
        "is_normal": is_norm,
        "ci_95": [ci_lower, ci_upper],
        "hash": ndvi_hash,
    }

    # Benchmark band arithmetic
    print("\n[3/4] Testing band arithmetic (EVI, SAVI, NDWI, NBR)...")
    tracemalloc.reset_peak()

    def band_math_task():
        return benchmark_band_arithmetic(
            bands["green"], bands["red"], bands["nir"], bands["swir"]
        )

    times, peak = run_benchmark(band_math_task, runs=10, warmup=2)
    indices_result = band_math_task()
    indices_hash = generate_hash(list(indices_result.values()))
    all_hashes.append(indices_hash)

    p_val, is_norm = shapiro_wilk_test(np.array(times))
    ci_lower, ci_upper = bootstrap_ci(np.array(times))

    print(f"  ✓ Min: {min(times):.4f}s (primary)")
    print(f"  ✓ Mean: {np.mean(times):.4f}s ± {np.std(times):.4f}s")
    print(f"  ✓ Hash: {indices_hash}")

    results["band_arithmetic"] = {
        "min_time_s": min(times),
        "mean_time_s": np.mean(times),
        "std_time_s": np.std(times),
        "peak_memory_mb": peak,
        "normality_p": p_val,
        "is_normal": is_norm,
        "ci_95": [ci_lower, ci_upper],
        "hash": indices_hash,
    }

    # Benchmark convolution
    print("\n[4/4] Testing 3x3 convolution filter...")
    tracemalloc.reset_peak()

    def conv_task():
        return benchmark_convolution_3x3(bands["nir"])

    times, peak = run_benchmark(conv_task, runs=10, warmup=2)
    conv_result = conv_task()
    conv_hash = generate_hash(conv_result)
    all_hashes.append(conv_hash)

    p_val, is_norm = shapiro_wilk_test(np.array(times))
    ci_lower, ci_upper = bootstrap_ci(np.array(times))

    print(f"  ✓ Min: {min(times):.4f}s (primary)")
    print(f"  ✓ Mean: {np.mean(times):.4f}s ± {np.std(times):.4f}s")
    print(f"  ✓ Hash: {conv_hash}")

    results["convolution_3x3"] = {
        "min_time_s": min(times),
        "mean_time_s": np.mean(times),
        "std_time_s": np.std(times),
        "peak_memory_mb": peak,
        "normality_p": p_val,
        "is_normal": is_norm,
        "ci_95": [ci_lower, ci_upper],
        "hash": conv_hash,
    }

    # Save results
    print("\n" + "=" * 70)
    print("SAVING RESULTS...")
    print("=" * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    output_data = {
        "language": "python",
        "scenario": "raster_algebra",
        "data_shape": list(bands["shape"]),
        "results": results,
        "all_hashes": all_hashes,
        "combined_hash": generate_hash(all_hashes),
    }

    with open(OUTPUT_DIR / "raster_algebra_python_results.json", "w") as f:
        json.dump(output_data, f, indent=2)

    with open(RESULTS_DIR / "raster_algebra_python.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"✓ Results saved")
    print(f"✓ Combined validation hash: {output_data['combined_hash']}")

    print("\n" + "=" * 70)
    print("Note: Minimum times are primary metrics (Chen & Revels 2016)")
    print("      Mean/median provided for context only")
    print("=" * 70)

    return output_data


if __name__ == "__main__":
    run_raster_algebra_benchmark()
