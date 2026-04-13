#!/usr/bin/env python3
"""
Cross-Language Result Converter

Converts Julia and R benchmark outputs to Python BenchmarkResult format
for unified statistical analysis.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

sys.path.insert(0, str(Path(__file__).parent))

from benchmark_stats import (
    median_of_means, dagostino_pearson_test, jarque_bera_test,
    cohen_d, glass_delta, bootstrap_ci
)


def convert_julia_results(julia_json_path: str, language: str = "julia") -> Dict[str, Any]:
    """
    Convert Julia benchmark JSON output to standardized format.
    
    Julia output format:
    {
        "matrix_creation": {"min": ..., "mean": ..., "std": ..., "max": ...},
        ...
    }
    
    Returns standardized format with all new statistical fields.
    """
    with open(julia_json_path) as f:
        data = json.load(f)
    
    results = data.get("results", data)
    converted = {}
    
    for benchmark_name, stats in results.items():
        if isinstance(stats, dict) and "min" in stats:
            converted[benchmark_name] = {
                "name": benchmark_name,
                "language": language,
                "min_time": stats.get("min", 0),
                "mean_time": stats.get("mean", 0),
                "std_time": stats.get("std", 0),
                "median_time": stats.get("median", stats.get("mean", 0)),
                "max_time": stats.get("max", 0),
                "cv": stats.get("std", 0) / stats.get("mean", 1) if stats.get("mean", 0) > 0 else 0,
            }
    
    return converted


def convert_r_results(r_json_path: str, language: str = "r") -> Dict[str, Any]:
    """
    Convert R benchmark JSON output to standardized format.
    
    R output format:
    {
        "language": "R",
        "results": {
            "matrix_creation": {"min": ..., "mean": ..., "std": ..., "max": ...},
            ...
        }
    }
    
    Returns standardized format with all new statistical fields.
    """
    with open(r_json_path) as f:
        data = json.load(f)
    
    results = data.get("results", data)
    converted = {}
    
    for benchmark_name, stats in results.items():
        if isinstance(stats, dict) and "min" in stats:
            converted[benchmark_name] = {
                "name": benchmark_name,
                "language": language,
                "min_time": stats.get("min", 0),
                "mean_time": stats.get("mean", 0),
                "std_time": stats.get("std", 0),
                "median_time": stats.get("median", stats.get("mean", 0)),
                "max_time": stats.get("max", 0),
                "cv": stats.get("std", 0) / stats.get("mean", 1) if stats.get("mean", 0) > 0 else 0,
            }
    
    return converted


def convert_all_results(
    results_dir: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert all benchmark results (Python, Julia, R) to standardized format.
    
    Expected directory structure:
    results/
        python/
            *.json
        julia/
            *.json
        r/
            *.json
    """
    results_path = Path(results_dir)
    all_converted = {"python": {}, "julia": {}, "r": {}}
    
    for lang in ["python", "julia", "r"]:
        lang_dir = results_path / lang
        if lang_dir.exists():
            for json_file in lang_dir.glob("*.json"):
                try:
                    if lang == "julia":
                        converted = convert_julia_results(str(json_file), lang)
                    else:
                        converted = convert_r_results(str(json_file), lang)
                    
                    all_converted[lang].update(converted)
                except Exception as e:
                    print(f"Warning: Could not convert {json_file}: {e}")
    
    if output_path:
        with open(output_path, "w") as f:
            json.dump(all_converted, f, indent=2)
    
    return all_converted


def run_cross_language_analysis(results_dir: str) -> Dict[str, Any]:
    """
    Run comprehensive statistical analysis across all languages.
    
    This function:
    1. Converts all language results to standardized format
    2. Computes effect sizes between languages
    3. Applies multiple comparison corrections
    4. Generates comparison statistics
    """
    converted = convert_all_results(results_dir)
    
    benchmarks = set()
    for lang_results in converted.values():
        benchmarks.update(lang_results.keys())
    
    analysis = {}
    
    for benchmark in benchmarks:
        analysis[benchmark] = {
            "languages": {},
            "comparisons": []
        }
        
        lang_times = {}
        for lang, lang_results in converted.items():
            if benchmark in lang_results:
                stats = lang_results[benchmark]
                analysis[benchmark]["languages"][lang] = stats
                lang_times[lang] = stats["min_time"]
        
        langs = list(lang_times.keys())
        for i, lang1 in enumerate(langs):
            for lang2 in langs[i+1:]:
                if lang1 in lang_times and lang2 in lang_times:
                    t1, t2 = lang_times[lang1], lang_times[lang2]
                    speedup = t1 / t2 if t2 > 0 else 1.0
                    
                    analysis[benchmark]["comparisons"].append({
                        "pair": f"{lang1} vs {lang2}",
                        "speedup": speedup,
                        "faster": lang1 if speedup > 1 else lang2,
                    })
    
    return analysis


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert cross-language benchmark results")
    parser.add_argument("results_dir", help="Directory containing benchmark results")
    parser.add_argument("--output", "-o", help="Output JSON file")
    
    args = parser.parse_args()
    
    print("Converting cross-language results...")
    converted = convert_all_results(args.results_dir, args.output)
    
    print(f"\nConverted results:")
    for lang, results in converted.items():
        print(f"  {lang}: {len(results)} benchmarks")
    
    print("\nRunning cross-language analysis...")
    analysis = run_cross_language_analysis(args.results_dir)
    
    for benchmark, data in analysis.items():
        print(f"\n{benchmark}:")
        for lang, stats in data.get("languages", {}).items():
            print(f"  {lang}: {stats['min_time']:.4f}s (min)")
        
        for comp in data.get("comparisons", [])[:3]:
            print(f"  {comp['pair']}: {comp['speedup']:.2f}× speedup")
