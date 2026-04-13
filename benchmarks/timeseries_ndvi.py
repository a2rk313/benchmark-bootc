#!/usr/bin/env python3
"""
==================================================================================
SCENARIO D: Time-Series NDVI Analysis - Python Implementation
==================================================================================
Task: Calculate NDVI statistics across time series
Dataset: Real MODIS NDVI time series (if available) or synthetic
         based on real MODIS patterns (46 timesteps × 100×100 spatial)
Metrics: Temporal aggregation, statistical computation, memory efficiency
==================================================================================
"""

import numpy as np
import json
import hashlib
from pathlib import Path
import time


def load_modis_ndvi():
    """Load real MODIS NDVI time series if available."""
    modis_paths = [
        "data/modis/modis_ndvi_timeseries.bin",
        "data/modis/modis_ndvi_timeseries.npy",
    ]

    for path in modis_paths:
        if Path(path).exists():
            try:
                if path.endswith(".bin"):
                    # Try to load with header info
                    hdr_path = path.replace(".bin", ".hdr")
                    if Path(hdr_path).exists():
                        with open(hdr_path) as f:
                            content = f.read()
                            for line in content.split("\n"):
                                if line.startswith("samples"):
                                    n_lon = int(line.split("=")[1].strip())
                                elif line.startswith("lines"):
                                    n_lat = int(line.split("=")[1].strip())
                                elif line.startswith("bands"):
                                    n_bands = int(line.split("=")[1].strip())

                        data = np.fromfile(path, dtype=np.float32)
                        # MODIS is BIL format: (bands, lines, samples)
                        data = data.reshape(n_bands, n_lat, n_lon)
                        print(f"  ✓ Loaded MODIS NDVI: {path} ({data.shape})")
                        return data
                elif path.endswith(".npy"):
                    data = np.load(path)
                    print(f"  ✓ Loaded MODIS NDVI: {path} ({data.shape})")
                    return data
            except Exception as e:
                print(f"  ⚠ Could not load {path}: {e}")

    print("  ⚠ MODIS NDVI not available")
    return None


def generate_modis_like_landsat(width=100, height=100, n_dates=46, seed=42):
    """
    Generate realistic MODIS-like time series based on real patterns.

    This captures essential characteristics of real MODIS NDVI:
    - Seasonal vegetation cycles
    - Spatial autocorrelation
    - Realistic noise characteristics

    Returns:
        ndvi_data: (n_dates, height, width) - NDVI values
    """
    np.random.seed(seed)

    # Create spatial structure (landscape features)
    x = np.linspace(-1, 1, width)
    y = np.linspace(-1, 1, height)
    xx, yy = np.meshgrid(x, y)

    # Base vegetation pattern
    vegetation_base = np.exp(-(xx**2 + yy**2) / 0.5)

    # Seasonal cycle
    t = np.linspace(0, 4 * np.pi, n_dates)
    seasonal = (np.sin(t) + 1) / 2  # 0 to 1

    # Build time series
    ndvi_data = np.zeros((n_dates, height, width), dtype=np.float32)

    for i in range(n_dates):
        # Base vegetation scaled by seasonality
        vegetation = vegetation_base * (0.3 + 0.5 * seasonal[i])

        # Add inter-annual variation
        noise = np.random.randn(height, width) * 0.05

        # Clamp to valid NDVI range
        ndvi = np.clip(vegetation + noise, -0.1, 1.0)
        ndvi_data[i] = ndvi

    return ndvi_data


def get_ndvi_data():
    """Get NDVI data from real MODIS or generate realistic fallback."""
    real_data = load_modis_ndvi()
    if real_data is not None:
        return real_data
    print("  → Generating realistic MODIS-like time series...")
    return generate_modis_like_landsat()


def calculate_ndvi(red, nir):
    """
    Calculate NDVI = (NIR - Red) / (NIR + Red)
    """
    epsilon = 1e-8
    ndvi = (nir - red) / (nir + red + epsilon)
    return np.clip(ndvi, -1, 1)


def main():
    print("=" * 70)
    print("PYTHON - Scenario D: Time-Series NDVI Analysis")
    print("=" * 70)

    # =========================================================================
    # 1. Load MODIS NDVI time series (or generate realistic fallback)
    # =========================================================================
    print("\n[1/5] Loading MODIS NDVI time series...")

    start_time = time.time()
    ndvi_data = get_ndvi_data()
    gen_time = time.time() - start_time

    n_dates, height, width = ndvi_data.shape
    data_size_mb = ndvi_data.nbytes / (1024**2)

    print(f"  ✓ Time series: {n_dates} dates × {width}×{height} spatial")
    print(f"  ✓ Data size: {data_size_mb:.1f} MB")
    print(f"  ✓ Load time: {gen_time:.2f} seconds")

    # =========================================================================
    # 2. Calculate NDVI statistics (data is already NDVI)
    # =========================================================================
    print("\n[2/5] Computing NDVI statistics...")

    start_time = time.time()
    ndvi_stack = ndvi_data  # Already NDVI from MODIS

    calc_time = time.time() - start_time

    print(f"  ✓ NDVI data loaded: {n_dates} dates")
    print(f"  ✓ Load time: {calc_time:.2f} seconds")
    print(f"  ✓ NDVI range: [{ndvi_stack.min():.3f}, {ndvi_stack.max():.3f}]")

    # =========================================================================
    # 3. Temporal statistics
    # =========================================================================
    print("\n[3/5] Computing temporal statistics...")

    start_time = time.time()

    # Pixel-wise temporal statistics
    mean_ndvi = np.mean(ndvi_stack, axis=0)
    std_ndvi = np.std(ndvi_stack, axis=0)
    max_ndvi = np.max(ndvi_stack, axis=0)
    min_ndvi = np.min(ndvi_stack, axis=0)

    # Trend detection (simple linear regression slope)
    time_index = np.arange(n_dates).reshape(-1, 1, 1)

    # Vectorized linear regression
    mean_time = time_index.mean()
    mean_ndvi_time = ndvi_stack.mean(axis=0)

    numerator = ((time_index - mean_time) * (ndvi_stack - mean_ndvi_time)).sum(axis=0)
    denominator = ((time_index - mean_time) ** 2).sum()

    ndvi_trend = numerator / denominator

    stats_time = time.time() - start_time

    print(f"  ✓ Temporal statistics computed")
    print(f"  ✓ Computation time: {stats_time:.2f} seconds")
    print(f"  ✓ Mean NDVI (spatial avg): {mean_ndvi.mean():.3f}")
    print(f"  ✓ Average trend: {ndvi_trend.mean():.6f} NDVI/16-days")

    # =========================================================================
    # 4. Phenology metrics
    # =========================================================================
    print("\n[4/5] Extracting phenology metrics...")

    start_time = time.time()

    # Find peak vegetation month for each pixel
    peak_month = np.argmax(ndvi_stack, axis=0)

    # Calculate growing season length (periods above threshold)
    threshold = 0.3
    growing_season = (ndvi_stack > threshold).sum(axis=0)

    # Calculate seasonal amplitude
    amplitude = max_ndvi - min_ndvi

    pheno_time = time.time() - start_time

    print(f"  ✓ Phenology metrics extracted")
    print(f"  ✓ Computation time: {pheno_time:.2f} seconds")
    print(f"  ✓ Average peak period: {peak_month.mean():.1f}")
    print(f"  ✓ Average growing season: {growing_season.mean():.1f} 16-day periods")
    print(f"  ✓ Average amplitude: {amplitude.mean():.3f}")

    # =========================================================================
    # 5. Results and validation
    # =========================================================================
    print("\n[5/5] Computing final metrics...")

    total_time = calc_time + stats_time + pheno_time
    pixels_processed = width * height * n_dates
    throughput = pixels_processed / total_time

    print(f"  ✓ Total processing time: {total_time:.2f} seconds")
    print(f"  ✓ Throughput: {throughput:,.0f} pixel-dates/second")

    # Generate validation hash
    result_str = (
        f"{mean_ndvi.mean():.6f}_{ndvi_trend.mean():.6f}_{amplitude.mean():.6f}"
    )
    result_hash = hashlib.sha256(result_str.encode()).hexdigest()[:16]

    print(f"  ✓ Validation hash: {result_hash}")

    # Export results
    results = {
        "language": "python",
        "scenario": "timeseries_ndvi",
        "image_size": f"{width}x{height}",
        "n_dates": n_dates,
        "total_pixels_processed": pixels_processed,
        "execution_time_s": total_time,
        "throughput_pixels_per_sec": throughput,
        "mean_ndvi": float(mean_ndvi.mean()),
        "mean_trend": float(ndvi_trend.mean()),
        "mean_amplitude": float(amplitude.mean()),
        "avg_growing_season": float(growing_season.mean()),
        "validation_hash": result_hash,
    }

    # Save results
    output_dir = Path("validation")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "timeseries_python_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  ✓ Results saved to validation/timeseries_python_results.json")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
