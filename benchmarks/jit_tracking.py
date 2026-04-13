#!/usr/bin/env python3
"""
Julia JIT Compilation Tracking

Tracks Julia's JIT compilation times separately from execution times.
This is important because Julia's first-run compilation can dominate timings
if not properly warmup'd.

Based on Julia's @time macro approach.
"""

import json
import time
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class JITCompilationResult:
    benchmark: str
    compilation_time_s: float
    execution_time_s: float
    total_time_s: float
    compilation_overhead_pct: float
    is_cached: bool


class JuliaJITTracker:
    def __init__(self, julia_cmd: str = "julia"):
        self.julia_cmd = julia_cmd
        self.compilation_results: List[JITCompilationResult] = []
    
    def parse_julia_timing(self, output: str) -> Tuple[float, float, float]:
        """
        Parse Julia's @time macro output.
        
        Returns: (compilation_s, execution_s, total_s)
        """
        compilation_s = 0.0
        execution_s = 0.0
        total_s = 0.0
        
        compilation_pattern = r"Compilation:.*?(\d+\.?\d*)\s*s"
        if match := re.search(compilation_pattern, output, re.DOTALL):
            compilation_s = float(match.group(1))
        
        timing_pattern = r"(\d+\.?\d*)\s*seconds"
        if matches := re.findall(timing_pattern, output):
            if len(matches) >= 2:
                total_s = float(matches[0])
                execution_s = float(matches[1])
            elif len(matches) == 1:
                total_s = float(matches[0])
                execution_s = total_s - compilation_s
        
        return compilation_s, execution_s, total_s
    
    def run_julia_benchmark(
        self,
        code: str,
        benchmark_name: str,
        n_warmup: int = 3,
    ) -> JITCompilationResult:
        """
        Run a Julia benchmark with JIT tracking.
        
        First run includes JIT compilation, subsequent runs show cached performance.
        """
        script = f"""
using BenchmarkTools

# Warmup runs (trigger JIT compilation)
for _ in 1:{n_warmup}
    {code}
end

# Timing run with @time to capture compilation
@time begin
    {code}
end
"""
        
        result = subprocess.run(
            [self.julia_cmd, "-e", script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        compilation_s, execution_s, total_s = self.parse_julia_timing(result.stdout + result.stderr)
        
        compilation_overhead = (compilation_s / total_s * 100) if total_s > 0 else 0
        
        jit_result = JITCompilationResult(
            benchmark=benchmark_name,
            compilation_time_s=compilation_s,
            execution_time_s=execution_s,
            total_time_s=total_s,
            compilation_overhead_pct=compilation_overhead,
            is_cached=(n_warmup > 0),
        )
        
        self.compilation_results.append(jit_result)
        return jit_result
    
    def run_precompiled_benchmark(
        self,
        script_path: str,
        benchmark_name: str,
        n_runs: int = 5,
    ) -> Dict:
        """
        Run a precompiled Julia script and track times.
        
        Uses --compile=min to simulate no JIT overhead.
        """
        baseline_script = f"""
using Pkg
Pkg.precompile()
include("{script_path}")
"""
        
        nojit_script = f"""
using Pkg
Pkg.precompile()
# Force precompilation
include("{script_path}")
"""
        
        results = {
            "with_jit": [],
            "precompiled": [],
            "compilation_overhead": [],
        }
        
        for _ in range(n_runs):
            start = time.perf_counter()
            subprocess.run([self.julia_cmd, "-e", baseline_script], 
                         capture_output=True, timeout=60)
            results["with_jit"].append(time.perf_counter() - start)
        
        subprocess.run([self.julia_cmd, "-e", nojit_script], 
                     capture_output=True, timeout=120)
        
        for _ in range(n_runs):
            start = time.perf_counter()
            subprocess.run([self.julia_cmd, script_path], 
                         capture_output=True, timeout=60)
            results["precompiled"].append(time.perf_counter() - start)
        
        for i in range(n_runs):
            overhead = (results["with_jit"][i] - results["precompiled"][i]) / results["with_jit"][i] * 100
            results["compilation_overhead"].append(overhead)
        
        return results
    
    def print_jit_report(self):
        """Print JIT compilation analysis report."""
        print("\n" + "=" * 70)
        print("JULIA JIT COMPILATION ANALYSIS")
        print("=" * 70)
        
        for result in self.compilation_results:
            status = "cached" if result.is_cached else "first-run"
            print(f"\n{result.benchmark} ({status}):")
            print(f"  Compilation: {result.compilation_time_s:.4f}s")
            print(f"  Execution:   {result.execution_time_s:.4f}s")
            print(f"  Total:       {result.total_time_s:.4f}s")
            print(f"  Overhead:    {result.compilation_overhead_pct:.1f}%")
        
        if self.compilation_results:
            avg_overhead = sum(r.compilation_overhead_pct for r in self.compilation_results) / len(self.compilation_results)
            print(f"\nAverage compilation overhead: {avg_overhead:.1f}%")
            
            if avg_overhead > 10:
                print("\n⚠ WARNING: High JIT overhead detected!")
                print("  Consider increasing warmup runs or using precompilation.")
        else:
            print("\nNo JIT results recorded yet.")
        
        print("=" * 70)
    
    def export_results(self, output_path: str = "validation/jit_compilation.json"):
        """Export JIT tracking results."""
        output_dir = Path(output_path).parent
        output_dir.mkdir(exist_ok=True)
        
        data = {
            "results": [asdict(r) for r in self.compilation_results],
            "summary": {
                "total_benchmarks": len(self.compilation_results),
                "avg_compilation_time": (
                    sum(r.compilation_time_s for r in self.compilation_results) / len(self.compilation_results)
                    if self.compilation_results else 0
                ),
                "avg_overhead_pct": (
                    sum(r.compilation_overhead_pct for r in self.compilation_results) / len(self.compilation_results)
                    if self.compilation_results else 0
                ),
            },
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"JIT results saved to {output_path}")


def create_julia_precompile_script():
    """Create a precompilation script for faster Julia startup."""
    script = '''#!/usr/bin/env julia
"""
Precompile all Julia packages used in benchmarks.
Run this once before benchmarking to eliminate JIT overhead.
"""

using Pkg

# List of required packages
packages = [
    "CSV",
    "DataFrames",
    "MAT",
    "GeoDataFrames",
    "NearestNeighbors",
    "Statistics",
    "LinearAlgebra",
]

println("Precompiling Julia packages...")
for pkg in packages
    try
        @eval using $(Symbol(pkg))
        println("  ✓ $pkg")
    catch e
        println("  ✗ $pkg: $e")
    end
end

println("\\nPrecompilation complete!")

# Warmup common functions
println("\\nWarming up common functions...")
function warmup_benchmark()
    # Matrix operations
    A = rand(100, 100)
    B = rand(100, 100)
    C = A * B
    
    # Statistics
    x = rand(1000)
    m = mean(x)
    s = std(x)
    
    return m, s
end

for i in 1:3
    warmup_benchmark()
end

println("Warmup complete!")
'''
    
    script_path = Path("benchmarks/julia_precompile.jl")
    with open(script_path, "w") as f:
        f.write(script)
    
    print(f"Created precompilation script: {script_path}")


if __name__ == "__main__":
    tracker = JuliaJITTracker()
    
    test_code = """
    A = rand(1000, 1000)
    B = rand(1000, 1000)
    C = A * B
    mean(C)
    """
    
    print("Running JIT tracking test...")
    result = tracker.run_julia_benchmark(test_code, "matrix_test", n_warmup=3)
    
    tracker.print_jit_report()
    tracker.export_results()
    
    print("\nCreating precompilation script...")
    create_julia_precompile_script()
