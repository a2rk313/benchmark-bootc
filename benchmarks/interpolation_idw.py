#!/usr/bin/env python3
"""
===============================================================================
SCENARIO C: Spatial Interpolation - Python Implementation
===============================================================================
Task: Inverse Distance Weighting (IDW) interpolation on scattered points
Dataset: 50,000 random points → 1000x1000 grid interpolation
Metrics: Computational throughput, numerical efficiency, vectorization
===============================================================================
"""

import numpy as np
import pandas as pd
import json
import hashlib
import time
from pathlib import Path
from scipy.spatial import cKDTree

def idw_interpolation(points, values, grid_x, grid_y, power=2, neighbors=12):
    """
    Inverse Distance Weighting interpolation
    
    Args:
        points: (N, 2) array of point coordinates
        values: (N,) array of values at points
        grid_x, grid_y: Grid coordinates for interpolation
        power: IDW power parameter
        neighbors: Number of nearest neighbors to use
    
    Returns:
        Interpolated grid values
    """
    # Build KD-tree for fast nearest neighbor search
    tree = cKDTree(points)
    
    # Flatten grid for vectorized processing
    grid_points = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    
    # Query nearest neighbors
    distances, indices = tree.query(grid_points, k=neighbors)
    
    # Avoid division by zero
    distances = np.maximum(distances, 1e-10)
    
    # Calculate weights (inverse distance)
    weights = 1.0 / (distances ** power)
    
    # Normalize weights
    weights /= weights.sum(axis=1, keepdims=True)
    
    # Interpolate values
    interpolated = (weights * values[indices]).sum(axis=1)
    
    # Reshape to grid
    return interpolated.reshape(grid_x.shape)

def main():
    print("=" * 70)
    print("PYTHON - Scenario C: Spatial Interpolation (IDW)")
    print("=" * 70)
    
    # =========================================================================
    # 1. Generate synthetic scattered points
    # =========================================================================
    print("\n[1/4] Generating scattered point data...")
    
    np.random.seed(42)
    n_points = 50000
    
    # Random points in [0, 1000] x [0, 1000]
    x = np.random.uniform(0, 1000, n_points)
    y = np.random.uniform(0, 1000, n_points)
    
    # Synthetic elevation field with spatial structure
    values = (
        100 * np.sin(x / 200) * np.cos(y / 200) +  # Large-scale pattern
        50 * np.sin(x / 50) +                       # Medium-scale
        20 * np.random.randn(n_points)              # Noise
    )
    
    points = np.column_stack([x, y])
    
    print(f"  ✓ Generated {n_points:,} scattered points")
    print(f"  ✓ Value range: [{values.min():.2f}, {values.max():.2f}]")
    
    # =========================================================================
    # 2. Create interpolation grid
    # =========================================================================
    print("\n[2/4] Creating interpolation grid...")
    
    grid_resolution = 1000  # 1000x1000 grid
    grid_x, grid_y = np.meshgrid(
        np.linspace(0, 1000, grid_resolution),
        np.linspace(0, 1000, grid_resolution)
    )
    
    print(f"  ✓ Grid size: {grid_resolution} × {grid_resolution}")
    print(f"  ✓ Total interpolation points: {grid_resolution**2:,}")
    
    # =========================================================================
    # 3. Perform IDW interpolation
    # =========================================================================
    print("\n[3/4] Performing IDW interpolation...")
    
    start_time = time.time()
    interpolated = idw_interpolation(points, values, grid_x, grid_y, power=2, neighbors=12)
    elapsed_time = time.time() - start_time
    
    print(f"  ✓ Interpolation complete in {elapsed_time:.2f} seconds")
    print(f"  ✓ Interpolated value range: [{interpolated.min():.2f}, {interpolated.max():.2f}]")
    
    # =========================================================================
    # 4. Compute statistics and validate
    # =========================================================================
    print("\n[4/4] Computing metrics...")
    
    # Calculate interpolation quality metrics
    mean_value = float(np.mean(interpolated))
    std_value = float(np.std(interpolated))
    median_value = float(np.median(interpolated))
    
    # Calculate processing rate
    points_per_second = (grid_resolution ** 2) / elapsed_time
    
    print(f"  ✓ Mean interpolated value: {mean_value:.2f}")
    print(f"  ✓ Std dev: {std_value:.2f}")
    print(f"  ✓ Processing rate: {points_per_second:,.0f} grid points/second")
    
    # Generate validation hash
    result_str = f"{mean_value:.6f}_{std_value:.6f}_{median_value:.6f}"
    result_hash = hashlib.sha256(result_str.encode()).hexdigest()[:16]
    
    print(f"  ✓ Validation hash: {result_hash}")
    
    # Export results
    results = {
        "language": "python",
        "scenario": "interpolation_idw",
        "n_points": n_points,
        "grid_size": grid_resolution,
        "total_interpolated": grid_resolution ** 2,
        "execution_time_s": elapsed_time,
        "points_per_second": points_per_second,
        "mean_value": mean_value,
        "std_value": std_value,
        "median_value": median_value,
        "validation_hash": result_hash
    }
    
    # Save results
    output_dir = Path("validation")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "interpolation_python_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n  ✓ Results saved to validation/interpolation_python_results.json")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
