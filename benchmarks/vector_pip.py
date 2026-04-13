#!/usr/bin/env python3
"""
===============================================================================
SCENARIO B: Complex Vector Operations - Python Implementation
===============================================================================
Task: Point-in-Polygon spatial join + Haversine distance calculation
Dataset: 1M GPS points × Natural Earth countries (high-vertex complexity)
Metrics: Computational throughput, GEOS interface efficiency
===============================================================================
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import shapely
import sys
import json
import hashlib
from pathlib import Path


def haversine_vectorized(lat1, lon1, lat2, lon2):
    """
    Vectorized Haversine distance calculation

    Args:
        lat1, lon1: Point coordinates (arrays)
        lat2, lon2: Centroid coordinates (arrays)

    Returns:
        Distance in meters (array)
    """
    R = 6371000.0  # Earth radius in meters

    # Convert to radians
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    # Haversine formula
    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    )

    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c


def main():
    print("=" * 70)
    print("PYTHON - Scenario B: Vector Point-in-Polygon + Haversine")
    print("=" * 70)

    # =========================================================================
    # 1. Data Loading
    # =========================================================================
    print("\n[1/4] Loading data...")

    # Load polygon dataset (Natural Earth countries)
    polys = gpd.read_file("data/natural_earth_countries.gpkg")
    print(f"  ✓ Loaded {len(polys)} polygons")
    # Count vertices - use shapely.get_coordinates for all geometries
    total_vertices = shapely.get_coordinates(polys.geometry.buffer(0).boundary).shape[0]
    print(f"  ✓ Total vertices: {total_vertices}")

    # Load point dataset
    points_df = pd.read_csv("data/gps_points_1m.csv")
    points = gpd.GeoDataFrame(
        points_df,
        geometry=gpd.points_from_xy(points_df["lon"], points_df["lat"]),
        crs="EPSG:4326",
    )
    print(f"  ✓ Loaded {len(points)} points")

    # =========================================================================
    # 2. Spatial Join (Point-in-Polygon)
    # =========================================================================
    print("\n[2/4] Performing spatial join...")

    # Create spatial index for efficiency
    polys_sindex = polys.sindex

    # Spatial join using GEOS topology engine
    joined = gpd.sjoin(points, polys, how="inner", predicate="within")

    print(f"  ✓ Matched {len(joined)} points to polygons")
    print(f"  ✓ Match rate: {100 * len(joined) / len(points):.2f}%")

    # =========================================================================
    # 3. Distance Calculation
    # =========================================================================
    print("\n[3/4] Calculating Haversine distances...")

    # Extract point coordinates
    point_coords = np.array([(p.y, p.x) for p in joined.geometry])

    # Calculate polygon centroids
    poly_indices = joined["index_right"].values
    centroids = polys.iloc[poly_indices].geometry.centroid
    centroid_coords = np.array([(c.y, c.x) for c in centroids])

    # Vectorized Haversine calculation
    distances = haversine_vectorized(
        point_coords[:, 0],  # point latitudes
        point_coords[:, 1],  # point longitudes
        centroid_coords[:, 0],  # centroid latitudes
        centroid_coords[:, 1],  # centroid longitudes
    )

    # =========================================================================
    # 4. Results & Validation
    # =========================================================================
    print("\n[4/4] Computing metrics...")

    # Statistics
    total_distance = float(np.sum(distances))
    mean_distance = float(np.mean(distances))
    median_distance = float(np.median(distances))
    max_distance = float(np.max(distances))

    print(f"  ✓ Total distance: {total_distance:,.0f} meters")
    print(f"  ✓ Mean distance: {mean_distance:,.0f} meters")
    print(f"  ✓ Median distance: {median_distance:,.0f} meters")
    print(f"  ✓ Max distance: {max_distance:,.0f} meters")

    # Generate output hash for validation
    result_str = f"{total_distance:.6f}_{len(joined)}_{mean_distance:.6f}"
    result_hash = hashlib.sha256(result_str.encode()).hexdigest()[:16]

    print(f"  ✓ Validation hash: {result_hash}")

    # Export results for cross-language validation
    results = {
        "language": "python",
        "scenario": "vector_pip",
        "points_processed": int(len(points)),
        "matches_found": int(len(joined)),
        "total_distance_m": total_distance,
        "mean_distance_m": mean_distance,
        "median_distance_m": median_distance,
        "max_distance_m": max_distance,
        "validation_hash": result_hash,
    }

    # Save results
    output_dir = Path("validation")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "vector_python_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  ✓ Results saved to validation/vector_python_results.json")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
