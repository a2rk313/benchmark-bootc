#!/usr/bin/env python3
"""
===============================================================================
CROSS-LANGUAGE VALIDATION SCRIPT
===============================================================================
Validates that all language implementations produce equivalent results.
Checks:
1. Numerical precision (within acceptable tolerance)
2. Output consistency (same number of matches/pixels)
3. Validation hash agreement
===============================================================================
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def load_results(validation_dir="validation"):
    """Load all validation JSON files"""
    results = defaultdict(dict)
    
    validation_path = Path(validation_dir)
    if not validation_path.exists():
        print(f"{Colors.RED}Error: Validation directory not found: {validation_dir}{Colors.END}")
        return None
    
    for json_file in validation_path.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            scenario = data.get('scenario', 'unknown')
            language = data.get('language', 'unknown')
            results[scenario][language] = data
            
        except Exception as e:
            print(f"{Colors.YELLOW}Warning: Could not load {json_file}: {e}{Colors.END}")
    
    return results

def validate_vector_results(results):
    """Validate vector (point-in-polygon) results"""
    print(f"\n{Colors.BOLD}Vector Benchmark Validation{Colors.END}")
    print("=" * 70)
    
    if 'vector_pip' not in results or len(results['vector_pip']) < 2:
        print(f"{Colors.YELLOW}⚠ Insufficient vector results for comparison{Colors.END}")
        return False
    
    langs = list(results['vector_pip'].keys())
    baseline = results['vector_pip'][langs[0]]
    
    all_valid = True
    
    # 1. Check match counts
    print(f"\n{Colors.BLUE}1. Match Count Validation{Colors.END}")
    match_counts = {}
    for lang, data in results['vector_pip'].items():
        matches = data.get('matches_found', 0)
        match_counts[lang] = matches
        print(f"  {lang:8s}: {matches:,} matches")
    
    # Allow small variations (up to 1% difference due to floating-point)
    match_values = list(match_counts.values())
    max_diff = max(match_values) - min(match_values)
    tolerance = 0.01 * min(match_values)  # 1% tolerance
    
    if max_diff <= tolerance:
        print(f"  {Colors.GREEN}✓ Match counts are consistent{Colors.END}")
    else:
        print(f"  {Colors.RED}✗ Match counts vary by {max_diff:,} (>{tolerance:.0f} tolerance){Colors.END}")
        all_valid = False
    
    # 2. Check distance statistics
    print(f"\n{Colors.BLUE}2. Distance Statistics Validation{Colors.END}")
    
    mean_distances = {}
    for lang, data in results['vector_pip'].items():
        mean_dist = data.get('mean_distance_m', 0)
        mean_distances[lang] = mean_dist
        print(f"  {lang:8s}: {mean_dist:,.2f} m")
    
    # Check relative error
    mean_values = list(mean_distances.values())
    mean_avg = sum(mean_values) / len(mean_values)
    max_rel_error = max(abs(v - mean_avg) / mean_avg for v in mean_values) * 100
    
    if max_rel_error < 0.1:  # < 0.1% relative error
        print(f"  {Colors.GREEN}✓ Mean distances agree (max error: {max_rel_error:.4f}%){Colors.END}")
    else:
        print(f"  {Colors.YELLOW}⚠ Mean distances vary (max error: {max_rel_error:.4f}%){Colors.END}")
        if max_rel_error > 1.0:
            all_valid = False
    
    # 3. Check validation hashes
    print(f"\n{Colors.BLUE}3. Validation Hash Comparison{Colors.END}")
    
    hashes = {}
    for lang, data in results['vector_pip'].items():
        hash_val = data.get('validation_hash', 'N/A')
        hashes[lang] = hash_val
        print(f"  {lang:8s}: {hash_val}")
    
    unique_hashes = len(set(hashes.values()))
    if unique_hashes == 1:
        print(f"  {Colors.GREEN}✓ All hashes match - results are identical{Colors.END}")
    else:
        print(f"  {Colors.YELLOW}⚠ Hashes differ - minor numerical variations present{Colors.END}")
        # This is acceptable if the statistical measures agree
    
    return all_valid

def validate_raster_results(results):
    """Validate raster (SAM) results"""
    print(f"\n{Colors.BOLD}Raster Benchmark Validation{Colors.END}")
    print("=" * 70)
    
    if 'hyperspectral_sam' not in results or len(results['hyperspectral_sam']) < 2:
        print(f"{Colors.YELLOW}⚠ Insufficient raster results for comparison{Colors.END}")
        return False
    
    langs = list(results['hyperspectral_sam'].keys())
    all_valid = True
    
    # 1. Check pixels processed
    print(f"\n{Colors.BLUE}1. Pixel Count Validation{Colors.END}")
    pixel_counts = {}
    for lang, data in results['hyperspectral_sam'].items():
        pixels = data.get('pixels_processed', 0)
        pixel_counts[lang] = pixels
        print(f"  {lang:8s}: {pixels:,} pixels")
    
    if len(set(pixel_counts.values())) == 1:
        print(f"  {Colors.GREEN}✓ All implementations processed same number of pixels{Colors.END}")
    else:
        print(f"  {Colors.RED}✗ Pixel counts differ - implementation mismatch{Colors.END}")
        all_valid = False
    
    # 2. Check reference spectrum consistency
    print(f"\n{Colors.BLUE}2. Reference Spectrum Validation{Colors.END}")
    
    ref_hashes = {}
    for lang, data in results['hyperspectral_sam'].items():
        ref_hash = data.get('reference_hash', 'N/A')
        ref_hashes[lang] = ref_hash
        print(f"  {lang:8s}: {ref_hash}")
    
    if len(set(ref_hashes.values())) == 1:
        print(f"  {Colors.GREEN}✓ All using same reference spectrum (seed=42){Colors.END}")
    else:
        print(f"  {Colors.RED}✗ Reference spectra differ - results not comparable{Colors.END}")
        all_valid = False
    
    # 3. Check SAM statistics
    print(f"\n{Colors.BLUE}3. SAM Statistics Validation{Colors.END}")
    
    mean_sams = {}
    for lang, data in results['hyperspectral_sam'].items():
        mean_sam = data.get('mean_sam_rad', 0)
        mean_sam_deg = data.get('mean_sam_deg', 0)
        mean_sams[lang] = mean_sam
        print(f"  {lang:8s}: {mean_sam:.6f} rad ({mean_sam_deg:.2f}°)")
    
    # Check agreement
    mean_values = list(mean_sams.values())
    mean_avg = sum(mean_values) / len(mean_values)
    max_rel_error = max(abs(v - mean_avg) / mean_avg for v in mean_values) * 100
    
    if max_rel_error < 0.01:  # < 0.01% relative error
        print(f"  {Colors.GREEN}✓ SAM means agree (max error: {max_rel_error:.6f}%){Colors.END}")
    else:
        print(f"  {Colors.YELLOW}⚠ SAM means vary (max error: {max_rel_error:.6f}%){Colors.END}")
        if max_rel_error > 0.1:
            all_valid = False
    
    # 4. Check validation hashes
    print(f"\n{Colors.BLUE}4. Validation Hash Comparison{Colors.END}")
    
    hashes = {}
    for lang, data in results['hyperspectral_sam'].items():
        hash_val = data.get('validation_hash', 'N/A')
        hashes[lang] = hash_val
        print(f"  {lang:8s}: {hash_val}")
    
    unique_hashes = len(set(hashes.values()))
    if unique_hashes == 1:
        print(f"  {Colors.GREEN}✓ All hashes match - results are identical{Colors.END}")
    else:
        print(f"  {Colors.YELLOW}⚠ Hashes differ - minor numerical variations present{Colors.END}")
    
    return all_valid

def main():
    print(f"{Colors.BOLD}=" * 70)
    print("CROSS-LANGUAGE VALIDATION REPORT")
    print("=" * 70 + Colors.END)
    
    # Load all results
    results = load_results()
    
    if not results:
        print(f"\n{Colors.RED}✗ No validation results found{Colors.END}")
        print("Run benchmarks first: ./run_benchmarks.sh")
        return 1
    
    # Validate each scenario
    vector_valid = validate_vector_results(results)
    raster_valid = validate_raster_results(results)
    
    # Summary
    print(f"\n{Colors.BOLD}=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70 + Colors.END)
    
    if vector_valid and raster_valid:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL VALIDATIONS PASSED{Colors.END}")
        print(f"{Colors.GREEN}All language implementations produce consistent results.{Colors.END}")
        return_code = 0
    elif vector_valid or raster_valid:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ PARTIAL VALIDATION{Colors.END}")
        if vector_valid:
            print(f"{Colors.GREEN}  ✓ Vector benchmarks: PASS{Colors.END}")
        else:
            print(f"{Colors.RED}  ✗ Vector benchmarks: FAIL{Colors.END}")
        
        if raster_valid:
            print(f"{Colors.GREEN}  ✓ Raster benchmarks: PASS{Colors.END}")
        else:
            print(f"{Colors.RED}  ✗ Raster benchmarks: FAIL{Colors.END}")
        return_code = 1
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ VALIDATION FAILED{Colors.END}")
        print(f"{Colors.RED}Implementations produce inconsistent results.{Colors.END}")
        print("\nPossible issues:")
        print("  1. Different random seeds")
        print("  2. Algorithmic differences")
        print("  3. Numerical precision variations")
        print("  4. Data loading inconsistencies")
        return_code = 2
    
    print(f"\n{Colors.BOLD}=" * 70 + Colors.END)
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())
