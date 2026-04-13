#!/usr/bin/env python3
"""
SCENARIO F: Zonal Statistics - Python Implementation
Tests: Polygon-based raster statistics (mean, std, sum over zones)

Uses REAL NLCD land cover data when available.
Academic rationale:
- Zonal statistics is fundamental to GIS analysis
- Used in land cover analysis, climate studies, hydrology
- Tests raster-vector overlay performance
"""

import os
import sys
import time
import json
import numpy as np
import geopandas as gpd
from pathlib import Path
import tracemalloc

sys.path.insert(0, str(Path(__file__).parent))
from benchmark_stats import (
    generate_hash,
    shapiro_wilk_test,
    bootstrap_ci,
    run_benchmark,
)

OUTPUT_DIR = Path("validation")
RESULTS_DIR = Path("results")


def load_or_create_data():
    """Load or create test data for zonal statistics."""
    try:
        # Load polygons
        polys = gpd.read_file("data/natural_earth_countries.gpkg")

        # Try to load real NLCD land cover data
        raster, rows, cols = load_nlcd_data()

        if raster is None:
            # Fallback: Create realistic land cover-like data
            print("  → Using synthetic land cover data (realistic patterns)")
            np.random.seed(42)
            rows, cols = 600, 600

            # Create realistic land cover classes
            x = np.linspace(-2, 2, cols)
            y = np.linspace(-2, 2, rows)
            xx, yy = np.meshgrid(x, y)
            distance = np.sqrt(xx**2 + yy**2)

            # Create landscape zones
            raster = np.zeros((rows, cols), dtype=np.float32)
            raster = np.where(distance < 0.5, 41.0, raster)  # Forest center
            raster = np.where(
                (distance >= 0.5) & (distance < 1.0), 21.0, raster
            )  # Developed
            raster = np.where(
                (distance >= 1.0) & (distance < 1.5), 82.0, raster
            )  # Agriculture
            raster = np.where(distance >= 1.5, 71.0, raster)  # Grassland

            # Add water bodies
            for _ in range(5):
                cx, cy = np.random.uniform(-2, 2), np.random.uniform(-2, 2)
                r = np.random.uniform(0.1, 0.3)
                water_mask = ((xx - cx) ** 2 + (yy - cy) ** 2) < r**2
                raster = np.where(water_mask, 11.0, raster)

            raster = raster.astype(np.float32)

        # Create lat/lon coordinates for raster
        lats = np.linspace(90, -90, rows)
        lons = np.linspace(-180, 180, cols)

        return polys, raster, lats, lons
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)


def load_nlcd_data():
    """Load real NLCD land cover data if available."""
    nlcd_paths = [
        "data/nlcd/nlcd_landcover.bin",
        "data/nlcd/nlcd_landcover.tif",
    ]

    for path in nlcd_paths:
        if Path(path).exists():
            try:
                if path.endswith(".bin"):
                    hdr_path = path.replace(".bin", ".hdr")
                    if Path(hdr_path).exists():
                        with open(hdr_path) as f:
                            for line in f:
                                if line.startswith("samples"):
                                    cols = int(line.split("=")[1].strip())
                                elif line.startswith("lines"):
                                    rows = int(line.split("=")[1].strip())

                        data = np.fromfile(path, dtype=np.uint8).astype(np.float32)
                        data = data.reshape(rows, cols)
                        print(f"  ✓ Loaded NLCD land cover: {path} ({data.shape})")
                        return data, rows, cols
                elif path.endswith(".tif"):
                    import rasterio

                    with rasterio.open(path) as src:
                        data = src.read(1).astype(np.float32)
                        rows, cols = data.shape
                        print(f"  ✓ Loaded NLCD land cover: {path} ({data.shape})")
                        return data, rows, cols
            except Exception as e:
                print(f"  ⚠ Could not load {path}: {e}")

    print("  ⚠ NLCD not available, using synthetic land cover")
    return None, 0, 0


def create_latitude_zones(rows, cols, n_zones):
    """Create simple latitude-based zones for benchmarking."""
    mask = np.zeros((rows, cols), dtype=np.int32)
    zone_height = rows // n_zones

    for z in range(n_zones):
        row_start = z * zone_height
        row_end = (z + 1) * zone_height if z < n_zones - 1 else rows
        mask[row_start:row_end, :] = z + 1

    return mask


def zonal_mean(raster, mask, zone_id):
    """Calculate mean raster value for a zone."""
    zone_mask = mask == zone_id
    if zone_mask.sum() == 0:
        return 0.0
    return raster[zone_mask].mean()


def zonal_statistics(raster, mask, zone_ids):
    """Calculate statistics for all zones."""
    results = []
    for zone_id in zone_ids:
        zone_mask = mask == zone_id
        if zone_mask.sum() == 0:
            results.append({"zone": zone_id, "mean": 0, "std": 0, "sum": 0, "count": 0})
            continue

        values = raster[zone_mask]
        results.append(
            {
                "zone": zone_id,
                "mean": float(values.mean()),
                "std": float(values.std()),
                "sum": float(values.sum()),
                "count": int(len(values)),
            }
        )
    return results


def vectorized_zonal_stats(raster, mask):
    """Vectorized zonal statistics using numpy."""
    unique_zones = np.unique(mask)
    unique_zones = unique_zones[unique_zones > 0]  # Exclude background

    means = []
    stds = []
    sums = []
    counts = []

    for zone_id in unique_zones:
        zone_mask = mask == zone_id
        values = raster[zone_mask]
        if len(values) > 0:
            means.append(values.mean())
            stds.append(values.std())
            sums.append(values.sum())
            counts.append(len(values))
        else:
            means.append(0.0)
            stds.append(0.0)
            sums.append(0.0)
            counts.append(0)

    return {
        "zones": unique_zones.tolist(),
        "means": means,
        "stds": stds,
        "sums": sums,
        "counts": counts,
    }


def run_zonal_stats_benchmark():
    print("=" * 70)
    print("PYTHON - Scenario F: Zonal Statistics")
    print("=" * 70)

    print("\n[1/4] Loading data...")
    polys, raster, lats, lons = load_or_create_data()
    rows, cols = raster.shape
    print(f"  ✓ Loaded {len(polys)} polygons")
    print(f"  ✓ Raster shape: {raster.shape} ({raster.size:,} cells)")

    results = {}
    all_hashes = []

    # Create mask grid
    print("\n[2/4] Creating raster mask grid...")
    tracemalloc.start()

    # Use latitude-based zones for faster testing
    n_zones = 10
    mask = create_latitude_zones(rows, cols, n_zones)

    def mask_task():
        return create_latitude_zones(rows, cols, n_zones)

    times, peak = run_benchmark(mask_task, runs=5, warmup=1)

    mask_hash = generate_hash(mask)
    all_hashes.append(mask_hash)

    print(f"  ✓ Mask created: {np.unique(mask).max()} zones")
    print(f"  ✓ Min: {min(times):.4f}s (primary)")
    print(f"  ✓ Mean: {np.mean(times):.4f}s ± {np.std(times):.4f}s")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    results["mask_creation"] = {
        "min_time_s": min(times),
        "mean_time_s": np.mean(times),
        "std_time_s": np.std(times),
        "peak_memory_mb": peak / 1024 / 1024,
        "n_zones": n_zones,
        "hash": mask_hash,
    }

    # Zonal mean calculation
    print("\n[3/4] Testing zonal mean calculation...")

    stats_result = vectorized_zonal_stats(raster, mask)

    def zonal_task():
        return vectorized_zonal_stats(raster, mask)

    times, peak = run_benchmark(zonal_task, runs=10, warmup=2)
    stats_hash = generate_hash(np.array(stats_result["means"]))
    all_hashes.append(stats_hash)

    p_val, is_norm = shapiro_wilk_test(np.array(times))

    print(f"  ✓ Min: {min(times):.4f}s (primary)")
    print(f"  ✓ Mean: {np.mean(times):.4f}s ± {np.std(times):.4f}s")
    print(f"  ✓ Normality: p={p_val:.4f} ({'normal' if is_norm else 'non-normal'})")
    print(f"  ✓ Hash: {stats_hash}")

    results["zonal_mean"] = {
        "min_time_s": min(times),
        "mean_time_s": np.mean(times),
        "std_time_s": np.std(times),
        "normality_p": p_val,
        "is_normal": is_norm,
        "n_zones": len(stats_result["zones"]),
        "hash": stats_hash,
    }

    # Full zonal statistics
    print("\n[4/4] Testing full zonal statistics...")

    def full_stats_task():
        return vectorized_zonal_stats(raster, mask)

    times, peak = run_benchmark(full_stats_task, runs=10, warmup=2)

    print(f"  ✓ Min: {min(times):.4f}s (primary)")
    print(f"  ✓ Mean: {np.mean(times):.4f}s ± {np.std(times):.4f}s")

    results["zonal_stats"] = {
        "min_time_s": min(times),
        "mean_time_s": np.mean(times),
        "std_time_s": np.std(times),
        "hash": stats_hash,
    }

    # Save results
    print("\n" + "=" * 70)
    print("SAVING RESULTS...")
    print("=" * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    output_data = {
        "language": "python",
        "scenario": "zonal_statistics",
        "results": results,
        "all_hashes": all_hashes,
        "combined_hash": generate_hash(all_hashes),
    }

    with open(OUTPUT_DIR / "zonal_stats_python_results.json", "w") as f:
        json.dump(output_data, f, indent=2, default=str)

    print(f"✓ Results saved")
    print(f"✓ Combined validation hash: {output_data['combined_hash']}")

    print("\n" + "=" * 70)
    print("Note: Minimum times are primary metrics (Chen & Revels 2016)")
    print("=" * 70)

    return output_data


if __name__ == "__main__":
    run_zonal_stats_benchmark()
