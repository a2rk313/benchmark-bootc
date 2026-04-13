#!/usr/bin/env python3
"""
==================================================================================
Matrix Operations Benchmark - Python Implementation
==================================================================================
Reproduces Tedesco et al. (2025) matrix operation benchmarks
Tasks: Creation/Transpose/Reshape, Power, Sorting, Cross-product, Determinant

Uses REAL SRTM DEM data for terrain-related operations.
==================================================================================
"""

import numpy as np
import sys
import json
import time
from pathlib import Path


def load_srtm_data():
    """Load real SRTM DEM data if available."""
    srtm_paths = [
        "data/srtm/srtm_merged.tif",
        "data/srtm/srtm_cuprite.tif",
        "data/srtm/srtm_cuprite.bin",
        "data/srtm/srtm_tile_10_163_329.tif",
    ]

    for path in srtm_paths:
        if Path(path).exists():
            try:
                if path.endswith(".tif"):
                    import rasterio

                    with rasterio.open(path) as src:
                        data = src.read(1).astype(np.float64)
                        print(f"  ✓ Loaded SRTM: {path} ({data.shape})")
                        return data
                elif path.endswith(".bin"):
                    data = np.fromfile(path, dtype=np.float32).astype(np.float64)
                    # Try to reshape based on header if available
                    hdr_path = path.replace(".bin", ".hdr")
                    if Path(hdr_path).exists():
                        with open(hdr_path) as f:
                            for line in f:
                                if line.startswith("samples"):
                                    cols = int(line.split("=")[1].strip())
                                elif line.startswith("lines"):
                                    rows = int(line.split("=")[1].strip())
                        data = data.reshape(rows, cols)
                    print(f"  ✓ Loaded SRTM: {path}")
                    return data
            except Exception as e:
                print(f"  ⚠ Could not load {path}: {e}")

    print("  ⚠ SRTM not available, using fallback terrain model")
    return None


def generate_terrain_fallback(n_rows=600, n_cols=600):
    """Generate realistic terrain data (fallback)."""
    np.random.seed(42)
    x = np.linspace(0, 10, n_cols)
    y = np.linspace(0, 10, n_rows)
    xx, yy = np.meshgrid(x, y)

    # Mountain range
    terrain = 1500 + 800 * np.exp(-((xx - 5) ** 2 + (yy - 5) ** 2) / 10)
    terrain += 200 * np.sin(xx * 2) * np.cos(yy * 1.5)

    # Add realistic noise (slope patterns)
    noise = np.cumsum(np.random.randn(n_rows, n_cols), axis=0) * 5
    noise += np.cumsum(np.random.randn(n_rows, n_cols), axis=1) * 5

    return (terrain + noise).astype(np.float64)


# Global terrain data
TERRAIN_DATA = None


def get_terrain_data():
    """Get terrain data, loading from SRTM if available."""
    global TERRAIN_DATA
    if TERRAIN_DATA is None:
        TERRAIN_DATA = load_srtm_data()
        if TERRAIN_DATA is None:
            TERRAIN_DATA = generate_terrain_fallback()
    return TERRAIN_DATA


def benchmark_matrix_creation_transpose_reshape(n=2500):
    """
    Task 1.1: Matrix Creation + Transpose + Reshape
    - Create n×n random matrix (or use real terrain)
    - Transpose it
    - Reshape to (n*3/5 × n*5/3)
    - Transpose again
    """
    terrain = get_terrain_data()

    start = time.perf_counter()

    # Use real terrain data (or create random for this test)
    A = np.random.randn(n, n)

    # Transpose
    A = A.T

    # Reshape
    new_rows = int(n * 2 / 5)
    new_cols = int(n * n / new_rows)
    A = A.reshape(new_rows, new_cols)

    # Transpose again
    A = A.T

    elapsed = time.perf_counter() - start
    return elapsed


def benchmark_matrix_power(n=2500):
    """
    Task 1.2: Element-wise Matrix Exponentiation
    - Use real terrain elevation data
    - Apply terrain analysis operations
    - Raise to power 10 (element-wise)
    """
    terrain = get_terrain_data()

    # Use real terrain or generate
    if terrain is not None and terrain.size >= n * n:
        # Use subset of real terrain
        start_row = np.random.randint(0, max(1, terrain.shape[0] - n))
        start_col = np.random.randint(0, max(1, terrain.shape[1] - n))
        A = terrain[start_row : start_row + n, start_col : start_col + n].copy()
    else:
        A = np.random.randn(n, n)

    # Normalize to positive values (elevation can't be negative in this context)
    A = np.abs(A - A.mean()) / (A.std() + 1e-10)

    # Timed operation
    start = time.perf_counter()
    A_pow = np.power(A, 10)
    elapsed = time.perf_counter() - start

    return elapsed


def benchmark_sorting(n=1_000_000):
    """
    Task 1.3: Sorting Random Values
    - Generate n random values (terrain-constrained)
    - Sort them in ascending order
    """
    # Pre-generate data (not timed)
    terrain = get_terrain_data()
    if terrain is not None and terrain.size >= n:
        arr = terrain.flatten()[:n].copy()
        np.random.shuffle(arr)
    else:
        arr = np.random.randn(n)

    # Timed operation (quicksort is NumPy default)
    start = time.perf_counter()
    arr_sorted = np.sort(arr)
    elapsed = time.perf_counter() - start

    return elapsed


def benchmark_crossproduct(n=2500):
    """
    Task 1.4: Matrix Cross-Product (A'A)
    - Create n×n random matrix
    - Compute A' * A
    """
    # Pre-generate data (not timed)
    A = np.random.randn(n, n)

    # Timed operation
    start = time.perf_counter()
    B = A.T @ A
    elapsed = time.perf_counter() - start

    return elapsed


def benchmark_determinant(n=2500):
    """
    Task 1.5: Matrix Determinant
    - Create n×n random matrix
    - Compute determinant
    """
    # Pre-generate data (not timed)
    A = np.random.randn(n, n)

    # Timed operation
    start = time.perf_counter()
    det_val = np.linalg.det(A)
    elapsed = time.perf_counter() - start

    return elapsed


def main():
    print("=" * 70)
    print("PYTHON - Matrix Operations Benchmark")
    print("=" * 70)

    # Configuration
    n_matrix = 2500  # Matrix size (matching Tedesco et al. k=1)
    n_sort = 1_000_000  # Sorting size
    n_runs = 30  # CLT threshold for stable bootstrap CIs  # Number of runs for statistical power
    n_warmup = 5  # Warmup runs (excluded from measurement)
    n_cache_warmup = 3  # Extra cache warmup iterations

    results = {}

    # Warmup phase (Chen & Revels 2016: exclude startup overhead)
    print(f"\n  Warming up ({n_warmup} runs + {n_cache_warmup} cache iterations)...")
    for _ in range(n_warmup):
        benchmark_matrix_creation_transpose_reshape(n_matrix)
    for _ in range(n_cache_warmup):
        benchmark_matrix_creation_transpose_reshape(n_matrix)
    print("  ✓ Warmup complete")

    # Task 1: creation/Transpose/Reshape
    print(f"\n[1/5] Matrix Creation + Transpose + Reshape ({n_matrix}×{n_matrix})...")
    times = [
        benchmark_matrix_creation_transpose_reshape(n_matrix) for _ in range(n_runs)
    ]
    results["matrix_creation"] = {
        "mean": float(np.mean(times)),
        "std": float(np.std(times)),
        "min": float(np.min(times)),
        "max": float(np.max(times)),
    }
    print(f"  ✓ Min: {results['matrix_creation']['min']:.4f}s (primary)")
    print(
        f"  ✓ Mean: {results['matrix_creation']['mean']:.4f}s ± {results['matrix_creation']['std']:.4f}s"
    )

    # Task 2: Matrix Power
    print(f"\n[2/5] Matrix Exponentiation ^10 ({n_matrix}×{n_matrix})...")
    for _ in range(n_warmup):
        benchmark_matrix_power(n_matrix)
    times = [benchmark_matrix_power(n_matrix) for _ in range(n_runs)]

    # Task 3: Sorting
    print(f"\n[3/5] Sorting {n_sort:,} Random Values...")
    for _ in range(n_warmup):
        benchmark_sorting(n_sort)
    times = [benchmark_sorting(n_sort) for _ in range(n_runs)]

    # Task 4: Cross-product
    print(f"\n[4/5] Cross-Product A'A ({n_matrix}×{n_matrix})...")
    for _ in range(n_warmup):
        benchmark_crossproduct(n_matrix)
    times = [benchmark_crossproduct(n_matrix) for _ in range(n_runs)]

    # Task 5: Determinant
    print(f"\n[5/5] Matrix Determinant ({n_matrix}×{n_matrix})...")
    for _ in range(n_warmup):
        benchmark_determinant(n_matrix)
    times = [benchmark_determinant(n_matrix) for _ in range(n_runs)]
    results["determinant"] = {
        "mean": float(np.mean(times)),
        "std": float(np.std(times)),
        "min": float(np.min(times)),
        "max": float(np.max(times)),
    }
    print(f"  ✓ Min: {results['determinant']['min']:.4f}s (primary)")
    print(
        f"  ✓ Mean: {results['determinant']['mean']:.4f}s ± {results['determinant']['std']:.4f}s"
    )

    # Save results
    print("\n" + "=" * 70)
    print("SAVING RESULTS...")
    print("=" * 70)

    output = {
        "language": "Python",
        "numpy_version": np.__version__,
        "matrix_size": n_matrix,
        "sorting_size": n_sort,
        "n_runs": n_runs,
        "methodology": "Minimum time as primary estimator (Chen & Revels 2016)",
        "results": results,
    }

    Path("results").mkdir(exist_ok=True)
    with open("results/matrix_ops_python.json", "w") as f:
        json.dump(output, f, indent=2)

    print("✓ Results saved to: results/matrix_ops_python.json")
    print("\nNote: Minimum times are primary metrics (Chen & Revels 2016)")
    print("      Mean/median provided for context only")


if __name__ == "__main__":
    main()
