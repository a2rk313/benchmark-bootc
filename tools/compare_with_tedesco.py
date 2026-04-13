#!/usr/bin/env python3
"""
===============================================================================
Comparison with Tedesco et al. (2025) Published Results
===============================================================================
Compare your matrix operations benchmark results with Tedesco et al. (2025)
"Computational Benchmark Study in Spatio-Temporal Statistics"
===============================================================================
"""

import json
import sys
from pathlib import Path

# Tedesco et al. (2025) results - Table C1, k=1 (2500×2500 matrices)
# Note: These are minimum times from their published results
TEDESCO_RESULTS = {
    'crossproduct': {
        'Python_NumPy': 0.033,
        'Julia': 0.182,
        'R_OpenBLAS': 0.034,
        'R_BLAS': 4.206
    },
    'determinant': {
        'Python_NumPy': 0.118,
        'Julia': 0.152,
        'R_OpenBLAS': 0.044,
        'R_BLAS': 2.390
    },
    'sorting': {
        'Python': 0.007,
        'Julia': 0.031,
        'R': 0.077
    }
}

def load_your_results():
    """Load your matrix operations results."""
    your_results = {}
    
    for lang in ['python', 'julia', 'r']:
        result_file = f'results/matrix_ops_{lang}.json'
        
        if not Path(result_file).exists():
            print(f"⚠ Missing: {result_file}")
            print(f"   Run: python3 benchmarks/matrix_ops.{'' if lang == 'python' else 'jl' if lang == 'julia' else 'R'}")
            continue
        
        with open(result_file) as f:
            data = json.load(f)
            your_results[lang] = data['results']
    
    if not your_results:
        print("\n❌ No matrix operations results found!")
        print("   Run the matrix operations benchmarks first:")
        print("   python3 benchmarks/matrix_ops.py")
        print("   julia benchmarks/matrix_ops.jl")
        print("   Rscript benchmarks/matrix_ops.R")
        sys.exit(1)
    
    return your_results

def compare_and_report(your_results):
    """Generate comparison table and analysis."""
    
    print("=" * 100)
    print("COMPARISON WITH TEDESCO ET AL. (2025)")
    print("=" * 100)
    print()
    print("Paper: 'Computational Benchmark Study in Spatio-Temporal Statistics'")
    print("Authors: Lorenzo Tedesco, Jacopo Rodeschini, Philipp Otto")
    print("Journal: Environmetrics (2025)")
    print("DOI: 10.1002/env.70017")
    print()
    print("=" * 100)
    
    # Header
    print(f"\n{'Task':<20} {'Lang':<12} {'Your Min':<12} {'Tedesco':<12} {'Ratio':<10} {'Interpretation'}")
    print("-" * 100)
    
    tasks = ['crossproduct', 'determinant', 'sorting']
    
    comparison_data = []
    
    for task in tasks:
        # Python
        if 'python' in your_results:
            your_python = your_results['python'][task]['min']
            tedesco_python = TEDESCO_RESULTS[task].get('Python_NumPy') or TEDESCO_RESULTS[task].get('Python')
            ratio_python = your_python / tedesco_python
            
            interpretation = ""
            if ratio_python < 0.9:
                interpretation = "Your system faster"
            elif ratio_python > 1.1:
                interpretation = "Your system slower"
            else:
                interpretation = "✓ Similar (validates Tedesco)"
            
            print(f"{task:<20} {'Python':<12} {your_python:>10.4f}s  {tedesco_python:>10.4f}s  {ratio_python:>8.2f}×  {interpretation}")
            
            comparison_data.append({
                'task': task,
                'language': 'Python',
                'your_min': your_python,
                'tedesco_min': tedesco_python,
                'ratio': ratio_python
            })
        
        # Julia
        if 'julia' in your_results:
            your_julia = your_results['julia'][task]['min']
            tedesco_julia = TEDESCO_RESULTS[task]['Julia']
            ratio_julia = your_julia / tedesco_julia
            
            interpretation = ""
            if ratio_julia < 0.9:
                interpretation = "Your system faster"
            elif ratio_julia > 1.1:
                interpretation = "Your system slower"
            else:
                interpretation = "✓ Similar (validates Tedesco)"
            
            print(f"{task:<20} {'Julia':<12} {your_julia:>10.4f}s  {tedesco_julia:>10.4f}s  {ratio_julia:>8.2f}×  {interpretation}")
            
            comparison_data.append({
                'task': task,
                'language': 'Julia',
                'your_min': your_julia,
                'tedesco_min': tedesco_julia,
                'ratio': ratio_julia
            })
        
        # R
        if 'r' in your_results:
            your_r = your_results['r'][task]['min']
            tedesco_r = TEDESCO_RESULTS[task].get('R_OpenBLAS') or TEDESCO_RESULTS[task].get('R')
            ratio_r = your_r / tedesco_r
            
            interpretation = ""
            if ratio_r < 0.9:
                interpretation = "Your system faster"
            elif ratio_r > 1.1:
                interpretation = "Your system slower"
            else:
                interpretation = "✓ Similar (validates Tedesco)"
            
            print(f"{task:<20} {'R':<12} {your_r:>10.4f}s  {tedesco_r:>10.4f}s  {ratio_r:>8.2f}×  {interpretation}")
            
            comparison_data.append({
                'task': task,
                'language': 'R',
                'your_min': your_r,
                'tedesco_min': tedesco_r,
                'ratio': ratio_r
            })
        
        print()  # Blank line between tasks
    
    print("=" * 100)
    print("\nINTERPRETATION GUIDE")
    print("=" * 100)
    print()
    print("Ratio Interpretation:")
    print("  Ratio < 1.0: Your system is faster than Tedesco et al. hardware")
    print("  Ratio ≈ 1.0: Similar performance (validates their findings)")
    print("  Ratio > 1.0: Your system is slower (expected for laptop vs HPC node)")
    print()
    print("Key Points:")
    print("  • Absolute times vary by hardware (CPU, RAM, BLAS library)")
    print("  • RANKINGS should be consistent (which language is fastest for each task)")
    print("  • Ratios in range [0.5, 2.0] are typical for different hardware")
    print()
    
    # Check ranking consistency
    print("\nRANKING CONSISTENCY CHECK")
    print("=" * 100)
    print()
    
    print("Cross-product:")
    print("  Tedesco: Python (0.033s) ≈ R/OpenBLAS (0.034s) < Julia (0.182s)")
    if 'python' in your_results and 'julia' in your_results:
        your_py = your_results['python']['crossproduct']['min']
        your_jl = your_results['julia']['crossproduct']['min']
        if your_py < your_jl:
            print(f"  Yours:   Python ({your_py:.3f}s) < Julia ({your_jl:.3f}s)  ✓ Consistent")
        else:
            print(f"  Yours:   Julia ({your_jl:.3f}s) < Python ({your_py:.3f}s)  ⚠ Different ranking")
    
    print("\nDeterminant:")
    print("  Tedesco: R/OpenBLAS (0.044s) < Python (0.118s) < Julia (0.152s)")
    if 'python' in your_results and 'julia' in your_results and 'r' in your_results:
        your_r = your_results['r']['determinant']['min']
        your_py = your_results['python']['determinant']['min']
        your_jl = your_results['julia']['determinant']['min']
        if your_r < your_py < your_jl:
            print(f"  Yours:   R ({your_r:.3f}s) < Python ({your_py:.3f}s) < Julia ({your_jl:.3f}s)  ✓ Consistent")
        else:
            print(f"  Yours:   Different ranking order  ⚠ Investigate BLAS library")
    
    print("\nSorting:")
    print("  Tedesco: Python (0.007s) < Julia (0.031s) < R (0.077s)")
    if 'python' in your_results and 'julia' in your_results and 'r' in your_results:
        your_py = your_results['python']['sorting']['min']
        your_jl = your_results['julia']['sorting']['min']
        your_r = your_results['r']['sorting']['min']
        if your_py < your_jl < your_r:
            print(f"  Yours:   Python ({your_py:.3f}s) < Julia ({your_jl:.3f}s) < R ({your_r:.3f}s)  ✓ Consistent")
        else:
            print(f"  Yours:   Different ranking order  ⚠ Check implementation")
    
    # Save detailed comparison
    print("\n" + "=" * 100)
    print("SAVING DETAILED COMPARISON")
    print("=" * 100)
    
    with open('results/tedesco_comparison.json', 'w') as f:
        json.dump({
            'comparison': comparison_data,
            'tedesco_reference': TEDESCO_RESULTS,
            'methodology': 'Minimum times compared (Chen & Revels 2016)'
        }, f, indent=2)
    
    print("\n✓ Detailed results saved to: results/tedesco_comparison.json")
    
    # Generate markdown report
    markdown = """# Comparison with Tedesco et al. (2025)

## Reference Paper

**Title**: Computational Benchmark Study in Spatio-Temporal Statistics  
**Authors**: Lorenzo Tedesco, Jacopo Rodeschini, Philipp Otto  
**Journal**: Environmetrics (2025)  
**DOI**: 10.1002/env.70017

## Methodology

Both studies use matrix operations to benchmark programming language performance:
- Matrix size: 2500×2500 (k=1 in Tedesco et al.)
- Metrics: Minimum execution time (Chen & Revels 2016 methodology)
- Languages: Python (NumPy), Julia, R (OpenBLAS when available)

## Results Summary

### Cross-Product (A'A)
| Language | Your Result | Tedesco et al. | Ratio | Consistent? |
|----------|-------------|----------------|-------|-------------|
"""
    
    for item in comparison_data:
        if item['task'] == 'crossproduct':
            consistent = '✓' if 0.5 <= item['ratio'] <= 2.0 else '⚠'
            markdown += f"| {item['language']} | {item['your_min']:.4f}s | {item['tedesco_min']:.4f}s | {item['ratio']:.2f}× | {consistent} |\n"
    
    markdown += """\n### Matrix Determinant
| Language | Your Result | Tedesco et al. | Ratio | Consistent? |
|----------|-------------|----------------|-------|-------------|
"""
    
    for item in comparison_data:
        if item['task'] == 'determinant':
            consistent = '✓' if 0.5 <= item['ratio'] <= 2.0 else '⚠'
            markdown += f"| {item['language']} | {item['your_min']:.4f}s | {item['tedesco_min']:.4f}s | {item['ratio']:.2f}× | {consistent} |\n"
    
    markdown += """\n### Sorting (1M values)
| Language | Your Result | Tedesco et al. | Ratio | Consistent? |
|----------|-------------|----------------|-------|-------------|
"""
    
    for item in comparison_data:
        if item['task'] == 'sorting':
            consistent = '✓' if 0.5 <= item['ratio'] <= 2.0 else '⚠'
            markdown += f"| {item['language']} | {item['your_min']:.4f}s | {item['tedesco_min']:.4f}s | {item['ratio']:.2f}× | {consistent} |\n"
    
    markdown += """
## Interpretation

**Ratio Interpretation:**
- Ratio < 1.0: Your hardware is faster
- Ratio ≈ 1.0: Similar performance (validates Tedesco et al.)
- Ratio > 1.0: Your hardware is slower

**Key Finding:** Ratios in the range [0.5, 2.0] are typical and expected due to 
hardware differences (CPU model, RAM speed, BLAS library implementation).

**Most Important:** Language RANKINGS should match, not absolute times.

## Conclusion

Your results {validate/partially validate/differ from} the findings of Tedesco et al. (2025).

*Note: Fill in conclusion based on actual results observed.*
"""
    
    with open('results/tedesco_comparison.md', 'w') as f:
        f.write(markdown)
    
    print("✓ Markdown report saved to: results/tedesco_comparison.md")
    print("\n" + "=" * 100)
    print("COMPARISON COMPLETE")
    print("=" * 100)
    print("\nNext steps:")
    print("  1. Include comparison in thesis Section 5.5")
    print("  2. Discuss hardware differences vs. ranking consistency")
    print("  3. Cite Tedesco et al. (2025) in relevant sections")

if __name__ == "__main__":
    print("\n")
    your_results = load_your_results()
    compare_and_report(your_results)
