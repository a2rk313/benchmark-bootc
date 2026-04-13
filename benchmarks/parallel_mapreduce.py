#!/usr/bin/env python3
"""
Embarrassingly Parallel (Map-Reduce) Benchmark

Tests parallel processing capabilities by simulating a common GIS/RS workflow:
processing multiple independent spatial tiles/regions in parallel.

This is common in:
- Tile-based image processing (landsat, sentinel, drone imagery)
- Regional climate model processing
- Distributed feature extraction
"""

import numpy as np
import hashlib
import json
import time
from pathlib import Path
from typing import List, Callable, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing


def process_tile(tile_data: np.ndarray, operation: str = "ndvi_stats") -> dict:
    """
    Process a single spatial tile - simulates independent processing unit.
    
    Operations include:
    - NDVI statistics calculation
    - Spatial filtering
    - Zonal statistics
    """
    if operation == "ndvi_stats":
        mean_val = np.mean(tile_data)
        std_val = np.std(tile_data)
        max_val = np.max(tile_data)
        min_val = np.min(tile_data)
        percentile_25 = np.percentile(tile_data, 25)
        percentile_75 = np.percentile(tile_data, 75)
        
        return {
            "mean": float(mean_val),
            "std": float(std_val),
            "max": float(max_val),
            "min": float(min_val),
            "p25": float(percentile_25),
            "p75": float(percentile_75),
        }
    
    elif operation == "spatial_filter":
        from scipy.ndimage import uniform_filter
        filtered = uniform_filter(tile_data, size=3)
        return {
            "filtered_mean": float(np.mean(filtered)),
            "filtered_max": float(np.max(filtered)),
        }
    
    return {}


def generate_tiles(
    n_tiles: int,
    tile_size: int = 256,
    seed: int = 42,
) -> List[np.ndarray]:
    """Generate spatial tiles for parallel processing."""
    np.random.seed(seed)
    tiles = [
        np.random.rand(tile_size, tile_size).astype(np.float32)
        for _ in range(n_tiles)
    ]
    return tiles


def sequential_processing(
    tiles: List[np.ndarray],
    operation: str = "ndvi_stats",
) -> float:
    """Process tiles sequentially (baseline)."""
    start = time.perf_counter()
    for tile in tiles:
        process_tile(tile, operation)
    return time.perf_counter() - start


def parallel_processing_threads(
    tiles: List[np.ndarray],
    n_workers: int = 4,
    operation: str = "ndvi_stats",
) -> float:
    """Process tiles in parallel using threads."""
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        list(executor.map(lambda t: process_tile(t, operation), tiles))
    return time.perf_counter() - start


def parallel_processing_processes(
    tiles: List[np.ndarray],
    n_workers: int = 4,
    operation: str = "ndvi_stats",
) -> float:
    """Process tiles in parallel using processes."""
    start = time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            list(executor.map(process_tile, tiles, [operation] * len(tiles)))
    except (RuntimeError, OSError):
        for tile in tiles:
            process_tile(tile, operation)
    return time.perf_counter() - start


def parallel_map_reduce(
    tiles: List[np.ndarray],
    map_func: Callable,
    reduce_func: Callable,
    n_workers: int = 4,
) -> float:
    """Classic map-reduce pattern."""
    start = time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            mapped = executor.map(map_func, tiles)
            result = reduce_func(list(mapped))
    except (RuntimeError, OSError):
        mapped = [map_func(tile) for tile in tiles]
        result = reduce_func(mapped)
    return time.perf_counter() - start


def run_parallel_benchmark(
    n_tiles: int = 32,
    tile_size: int = 256,
    n_workers_list: List[int] = None,
    n_runs: int = 5,
) -> dict:
    """
    Run embarrassingly parallel benchmark suite.
    
    Args:
        n_tiles: Number of independent tiles
        tile_size: Size of each tile (n×n pixels)
        n_workers_list: List of worker counts to test
        n_runs: Number of benchmark runs
    """
    if n_workers_list is None:
        max_workers = min(multiprocessing.cpu_count(), 8)
        n_workers_list = [1, 2, 4, max_workers]
    
    print("=" * 70)
    print("Embarrassingly Parallel (Map-Reduce) Benchmark")
    print("=" * 70)
    print(f"Tiles: {n_tiles} × {tile_size}×{tile_size} pixels")
    print(f"Workers to test: {n_workers_list}")
    print(f"Runs per configuration: {n_runs}")
    
    tiles = generate_tiles(n_tiles, tile_size)
    
    total_pixels = n_tiles * tile_size * tile_size
    print(f"Total pixels: {total_pixels:,} ({total_pixels / 1e6:.1f}M)")
    
    results = {
        "config": {
            "n_tiles": n_tiles,
            "tile_size": tile_size,
            "total_pixels": total_pixels,
            "n_workers_list": n_workers_list,
            "n_runs": n_runs,
        },
        "sequential": {},
        "parallel_threads": {},
        "parallel_processes": {},
        "map_reduce": {},
    }
    
    print("\n--- Sequential Baseline ---")
    seq_times = []
    for run in range(n_runs):
        t = sequential_processing(tiles)
        seq_times.append(t)
    seq_time = np.median(seq_times)
    results["sequential"] = {
        "median_time": float(seq_time),
        "all_times": [float(t) for t in seq_times],
        "throughput": float(total_pixels / seq_time),
    }
    print(f"Sequential: {seq_time:.4f}s ({results['sequential']['throughput']:.0f} px/s)")
    
    for n_workers in n_workers_list:
        if n_workers == 1:
            continue
            
        print(f"\n--- Threads (n={n_workers}) ---")
        thread_times = []
        for run in range(n_runs):
            t = parallel_processing_threads(tiles, n_workers)
            thread_times.append(t)
        thread_time = np.median(thread_times)
        speedup = seq_time / thread_time
        efficiency = speedup / n_workers
        
        results["parallel_threads"][n_workers] = {
            "median_time": float(thread_time),
            "speedup": float(speedup),
            "efficiency": float(efficiency),
            "throughput": float(total_pixels / thread_time),
        }
        print(f"Threads ({n_workers}): {thread_time:.4f}s, "
              f"speedup={speedup:.2f}×, efficiency={efficiency:.1%}")
        
        print(f"\n--- Processes (n={n_workers}) ---")
        proc_times = []
        for run in range(n_runs):
            t = parallel_processing_processes(tiles, n_workers)
            proc_times.append(t)
        proc_time = np.median(proc_times)
        speedup = seq_time / proc_time
        efficiency = speedup / n_workers
        
        results["parallel_processes"][n_workers] = {
            "median_time": float(proc_time),
            "speedup": float(speedup),
            "efficiency": float(efficiency),
            "throughput": float(total_pixels / proc_time),
        }
        print(f"Processes ({n_workers}): {proc_time:.4f}s, "
              f"speedup={speedup:.2f}×, efficiency={efficiency:.1%}")
        
        print(f"\n--- Map-Reduce (n={n_workers}) ---")
        mr_times = []
        for run in range(n_runs):
            t = parallel_map_reduce(
                tiles, 
                lambda t: process_tile(t, "ndvi_stats"),
                lambda x: x,
                n_workers
            )
            mr_times.append(t)
        mr_time = np.median(mr_times)
        speedup = seq_time / mr_time
        efficiency = speedup / n_workers
        
        results["map_reduce"][n_workers] = {
            "median_time": float(mr_time),
            "speedup": float(speedup),
            "efficiency": float(efficiency),
            "throughput": float(total_pixels / mr_time),
        }
        print(f"Map-Reduce ({n_workers}): {mr_time:.4f}s, "
              f"speedup={speedup:.2f}×, efficiency={efficiency:.1%}")
    
    all_speedups = []
    for n_workers in n_workers_list:
        if n_workers > 1 and n_workers in results["parallel_processes"]:
            all_speedups.append(results["parallel_processes"][n_workers]["speedup"])
    
    results["summary"] = {
        "max_speedup": float(max(all_speedups)) if all_speedups else 1.0,
        "optimal_workers": (
            max(n_workers_list, 
                key=lambda w: results["parallel_processes"].get(w, {}).get("speedup", 0))
            if results["parallel_processes"] else 1
        ),
        "parallel_efficiency_loss": (
            1.0 - min(all_speedups) if all_speedups else 0.0
        ),
    }
    
    result_hash = hashlib.sha256(
        json.dumps(results["config"], sort_keys=True).encode()
    ).hexdigest()[:16]
    results["validation_hash"] = result_hash
    
    print(f"\n{'=' * 70}")
    print("Summary:")
    print(f"  Max speedup: {results['summary']['max_speedup']:.2f}×")
    print(f"  Optimal workers: {results['summary']['optimal_workers']}")
    print(f"  Validation hash: {result_hash}")
    print(f"{'=' * 70}")
    
    return results


if __name__ == "__main__":
    results = run_parallel_benchmark(n_tiles=32, tile_size=256, n_runs=5)
    
    output_dir = Path("validation")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "parallel_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
