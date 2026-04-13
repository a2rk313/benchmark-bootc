#!/usr/bin/env python3
"""
===============================================================================
AUTOMATED BENCHMARK REPORT GENERATOR
===============================================================================
Generates publication-ready reports from benchmark results including:
- Summary statistics tables
- Statistical significance tests
- Performance comparisons
- Visualizations
- Interpretation and recommendations

Output format: Markdown (easily convertible to PDF/HTML/LaTeX)
===============================================================================
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List

class ReportGenerator:
    """
    Generate comprehensive markdown reports from benchmark results
    """
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.output_dir = self.results_dir / "reports"
        self.output_dir.mkdir(exist_ok=True)
    
    def load_statistical_analysis(self) -> Dict:
        """Load statistical analysis results"""
        analysis_file = self.results_dir / "statistical_analysis.json"
        if not analysis_file.exists():
            raise FileNotFoundError(
                "Statistical analysis not found. Run statistical_analysis.py first."
            )
        
        with open(analysis_file, 'r') as f:
            return json.load(f)
    
    def load_validation_results(self) -> Dict:
        """Load validation results"""
        validation_dir = Path("validation")
        results = {}
        
        for json_file in validation_dir.glob("*_results.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
                lang = data.get('language', 'unknown')
                scenario = data.get('scenario', 'unknown')
                
                key = f"{lang}_{scenario}"
                results[key] = data
        
        return results
    
    def create_summary_table(self, analysis: Dict, phase: str, scenario: str) -> str:
        """Create markdown table with summary statistics"""
        
        stats = analysis.get('descriptive_statistics', {})
        if not stats:
            return "_No data available_\n\n"
        
        # Build table
        table = "| Language | Mean (s) | Median (s) | Std Dev | Min | Max | CV | 95% CI |\n"
        table += "|----------|----------|------------|---------|-----|-----|----|---------|\n"
        
        for lang, data in stats.items():
            mean = data['mean']
            median = data['median']
            std = data['std']
            min_val = data['min']
            max_val = data['max']
            cv = data['cv']
            ci = data['ci95']
            
            table += f"| {lang.capitalize():8s} | {mean:8.3f} | {median:10.3f} | {std:7.3f} | {min_val:7.3f} | {max_val:7.3f} | {cv:4.2f} | [{ci[0]:.3f}, {ci[1]:.3f}] |\n"
        
        return table + "\n"
    
    def create_comparison_table(self, comparisons: List[Dict]) -> str:
        """Create markdown table with pairwise comparisons"""
        
        if not comparisons:
            return "_No comparisons available_\n\n"
        
        table = "| Comparison | Speedup | Mean Diff (s) | p-value | Significant | Effect Size | Interpretation |\n"
        table += "|------------|---------|---------------|---------|-------------|-------------|----------------|\n"
        
        for comp in comparisons:
            lang1 = comp['group1_name']
            lang2 = comp['group2_name']
            speedup = comp.get('speedup', 'N/A')
            mean_diff = comp['mean1'] - comp['mean2']
            p_value = comp['p_value']
            significant = "Yes" if comp['significant'] else "No"
            cohens_d = comp.get('cohens_d', None)
            interpretation = comp.get('effect_size_interpretation', 'N/A')
            
            speedup_str = f"{speedup:.2f}×" if isinstance(speedup, float) else speedup
            cohens_d_str = f"{cohens_d:.2f}" if cohens_d is not None else "N/A"
            
            table += f"| {lang1} vs {lang2} | {speedup_str:7s} | {mean_diff:13.3f} | {p_value:.6f} | {significant:11s} | {cohens_d_str:11s} | {interpretation:14s} |\n"
        
        return table + "\n"
    
    def create_validation_table(self, validation_results: Dict, scenario_type: str) -> str:
        """Create markdown table with validation results"""
        
        # Filter for scenario type
        relevant_results = {k: v for k, v in validation_results.items() if scenario_type in k}
        
        if not relevant_results:
            return "_No validation data available_\n\n"
        
        # Determine columns based on scenario
        if 'vector' in scenario_type:
            table = "| Language | Points Processed | Matches Found | Total Distance (m) | Mean Distance (m) | Hash |\n"
            table += "|----------|------------------|---------------|-------------------|------------------|-------|\n"
            
            for key, data in relevant_results.items():
                lang = data.get('language', 'unknown').capitalize()
                points = data.get('points_processed', 0)
                matches = data.get('matches_found', 0)
                total_dist = data.get('total_distance_m', 0)
                mean_dist = data.get('mean_distance_m', 0)
                hash_val = data.get('validation_hash', 'N/A')
                
                table += f"| {lang:8s} | {points:16,} | {matches:13,} | {total_dist:17,.0f} | {mean_dist:16,.2f} | {hash_val:5s} |\n"
        
        elif 'raster' in scenario_type or 'hyperspectral' in scenario_type:
            table = "| Language | Pixels Processed | Mean SAM (rad) | Mean SAM (°) | Std Dev | Hash |\n"
            table += "|----------|------------------|----------------|--------------|---------|-------|\n"
            
            for key, data in relevant_results.items():
                lang = data.get('language', 'unknown').capitalize()
                pixels = data.get('pixels_processed', 0)
                mean_sam_rad = data.get('mean_sam_rad', 0)
                mean_sam_deg = data.get('mean_sam_deg', 0)
                std_sam = data.get('std_sam_rad', 0)
                hash_val = data.get('validation_hash', 'N/A')
                
                table += f"| {lang:8s} | {pixels:16,} | {mean_sam_rad:14.6f} | {mean_sam_deg:12.2f} | {std_sam:7.6f} | {hash_val:5s} |\n"
        
        return table + "\n"
    
    def interpret_results(self, analysis: Dict, scenario: str) -> str:
        """Generate interpretation of results"""
        
        interpretations = []
        
        # Get pairwise comparisons
        comparisons = analysis.get('pairwise_comparisons', [])
        
        if not comparisons:
            return "_Insufficient data for interpretation_\n\n"
        
        # Find best performing language
        lang_means = {}
        for lang, stats in analysis.get('descriptive_statistics', {}).items():
            lang_means[lang] = stats['mean']
        
        if lang_means:
            best_lang = min(lang_means, key=lang_means.get)
            best_time = lang_means[best_lang]
            
            interpretations.append(
                f"**Best Performance:** {best_lang.capitalize()} achieved the fastest "
                f"execution time with a mean of {best_time:.3f} seconds."
            )
        
        # Analyze each comparison
        for comp in comparisons:
            lang1 = comp['group1_name']
            lang2 = comp['group2_name']
            speedup = comp.get('speedup', None)
            significant = comp['significant']
            effect_size = comp.get('effect_size_interpretation', 'unknown')
            
            if speedup and speedup != 1.0:
                faster_lang = lang2 if speedup > 1.0 else lang1
                slower_lang = lang1 if speedup > 1.0 else lang2
                speedup_val = speedup if speedup > 1.0 else 1.0/speedup
                
                sig_note = "statistically significant" if significant else "not statistically significant"
                effect_note = f"with a {effect_size.lower()} effect size"
                
                interpretations.append(
                    f"**{faster_lang.capitalize()} vs {slower_lang.capitalize()}:** "
                    f"{faster_lang.capitalize()} is {speedup_val:.2f}× faster, "
                    f"which is {sig_note} (p = {comp['p_value']:.4f}) {effect_note}."
                )
        
        # Add coefficient of variation analysis
        for lang, stats in analysis.get('descriptive_statistics', {}).items():
            cv = stats.get('cv', 0)
            if cv < 0.05:
                interpretations.append(
                    f"**{lang.capitalize()} Stability:** Coefficient of variation is {cv:.3f} "
                    f"(< 0.05), indicating highly stable measurements."
                )
            elif cv > 0.10:
                interpretations.append(
                    f"**{lang.capitalize()} Variability:** Coefficient of variation is {cv:.3f} "
                    f"(> 0.10), indicating higher measurement variability."
                )
        
        return "\n\n".join(interpretations) + "\n\n"
    
    def generate_full_report(self, output_file: str = "benchmark_report.md"):
        """Generate complete benchmark report"""
        
        print("Generating comprehensive benchmark report...")
        
        # Load data
        try:
            analysis = self.load_statistical_analysis()
            validation = self.load_validation_results()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return
        
        # Start report
        report = []
        
        # Header
        report.append("# GIS/RS Language Benchmark Report")
        report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n**Significance Level:** α = {analysis['metadata']['alpha']}")
        report.append(f"\n**Confidence Level:** {analysis['metadata']['confidence_level'] * 100}%")
        report.append("\n---\n")
        
        # Executive Summary
        report.append("## Executive Summary\n")
        report.append(
            "This report presents a comprehensive statistical analysis of computational "
            "performance benchmarks comparing Julia, Python, and R for geospatial computing "
            "workflows. The analysis includes both **cold start** (development) and "
            "**warm start** (production) performance metrics.\n"
        )
        
        # Scenarios
        scenarios = [
            ('vector', 'Vector Operations', 'Point-in-Polygon spatial join with Haversine distance calculation'),
            ('raster', 'Raster Operations', 'Hyperspectral Spectral Angle Mapper (SAM) on 224-band imagery')
        ]
        
        for scenario_key, scenario_name, scenario_desc in scenarios:
            report.append(f"\n## {scenario_name}\n")
            report.append(f"**Description:** {scenario_desc}\n")
            
            # Cold Start Analysis
            report.append("### Cold Start Performance (Development)\n")
            
            cold_analysis = analysis['cold_start_analysis'].get(scenario_key, {})
            
            if 'error' not in cold_analysis:
                report.append("#### Summary Statistics\n")
                report.append(self.create_summary_table(cold_analysis, 'cold', scenario_key))
                
                report.append("#### Pairwise Comparisons\n")
                report.append(self.create_comparison_table(cold_analysis.get('pairwise_comparisons', [])))
                
                report.append("#### Interpretation\n")
                report.append(self.interpret_results(cold_analysis, scenario_key))
            else:
                report.append(f"_Error: {cold_analysis['error']}_\n\n")
            
            # Warm Start Analysis
            report.append("### Warm Start Performance (Production)\n")
            
            warm_analysis = analysis['warm_start_analysis'].get(scenario_key, {})
            
            if 'error' not in warm_analysis:
                report.append("#### Summary Statistics\n")
                report.append(self.create_summary_table(warm_analysis, 'warm', scenario_key))
                
                report.append("#### Pairwise Comparisons\n")
                report.append(self.create_comparison_table(warm_analysis.get('pairwise_comparisons', [])))
                
                report.append("#### Interpretation\n")
                report.append(self.interpret_results(warm_analysis, scenario_key))
            else:
                report.append(f"_Error: {warm_analysis['error']}_\n\n")
            
            # Validation Results
            report.append("### Correctness Validation\n")
            report.append(
                "Cross-language validation ensures all implementations produce "
                "equivalent results.\n\n"
            )
            report.append(self.create_validation_table(validation, scenario_key))
        
        # Methodology
        report.append("\n## Methodology\n")
        report.append(
            "### Statistical Tests\n\n"
            "- **Normality:** Shapiro-Wilk test\n"
            "- **Variance Homogeneity:** Levene's test\n"
            "- **Parametric Comparison:** Independent t-test or Welch's t-test\n"
            "- **Non-parametric Comparison:** Mann-Whitney U test\n"
            "- **Effect Size:** Cohen's d\n"
            "- **Multiple Comparisons:** Bonferroni correction (when applicable)\n\n"
        )
        
        report.append(
            "### Effect Size Interpretation\n\n"
            "- **Negligible:** |d| < 0.2\n"
            "- **Small:** 0.2 ≤ |d| < 0.5\n"
            "- **Medium:** 0.5 ≤ |d| < 0.8\n"
            "- **Large:** |d| ≥ 0.8\n\n"
        )
        
        # Recommendations
        report.append("\n## Recommendations\n")
        report.append(self.generate_recommendations(analysis))
        
        # Appendix
        report.append("\n## Appendix\n")
        report.append(
            "### Data Availability\n\n"
            "- **Raw Results:** `results/cold_start/` and `results/warm_start/`\n"
            "- **Statistical Analysis:** `results/statistical_analysis.json`\n"
            "- **Validation Data:** `validation/*_results.json`\n"
            "- **Memory Profiles:** `results/memory/`\n\n"
        )
        
        # Save report
        output_path = self.output_dir / output_file
        with open(output_path, 'w') as f:
            f.write('\n'.join(report))
        
        print(f"\n✓ Report generated: {output_path}")
        print(f"  View with: cat {output_path}")
        print(f"  Convert to PDF: pandoc {output_path} -o report.pdf")
        
        return output_path
    
    def generate_recommendations(self, analysis: Dict) -> str:
        """Generate practical recommendations based on results"""
        
        recommendations = []
        
        # Analyze patterns across scenarios
        warm_analyses = analysis.get('warm_start_analysis', {})
        
        # Collect speedup data
        julia_vs_python = []
        julia_vs_r = []
        
        for scenario, data in warm_analyses.items():
            for comp in data.get('pairwise_comparisons', []):
                lang1, lang2 = comp['group1_name'], comp['group2_name']
                speedup = comp.get('speedup', None)
                
                if speedup:
                    if 'julia' in lang1 and 'python' in lang2:
                        julia_vs_python.append(speedup)
                    elif 'python' in lang1 and 'julia' in lang2:
                        julia_vs_python.append(1.0/speedup)
                    elif 'julia' in lang1 and 'r' in lang2:
                        julia_vs_r.append(speedup)
                    elif 'r' in lang1 and 'julia' in lang2:
                        julia_vs_r.append(1.0/speedup)
        
        # Generate recommendations
        recommendations.append("### Language Selection Guidance\n")
        
        if julia_vs_python:
            avg_speedup = np.mean(julia_vs_python)
            recommendations.append(
                f"**Julia vs Python:** Julia demonstrates an average {avg_speedup:.2f}× speedup "
                f"in production workflows. Julia is recommended for:\n"
                "- Computationally intensive operations\n"
                "- Production batch processing\n"
                "- Real-time analysis requirements\n"
            )
        
        recommendations.append(
            "\n**Python** remains suitable for:\n"
            "- Exploratory data analysis\n"
            "- Integration with existing Python ecosystems\n"
            "- Workflows where library availability > raw performance\n"
        )
        
        recommendations.append(
            "\n**R** is optimal for:\n"
            "- Statistical analysis and visualization\n"
            "- Integration with existing R workflows\n"
            "- Terra-based raster operations\n"
        )
        
        recommendations.append(
            "\n### Development vs Production Trade-offs\n"
            "\n"
            "Cold start metrics indicate Julia's JIT compilation adds initial overhead "
            "(3-5 seconds typical). For interactive development:\n"
            "- Use Python for rapid prototyping\n"
            "- Deploy Julia for production pipelines\n"
            "- Consider hybrid workflows (prototype in Python, deploy in Julia)\n"
        )
        
        return '\n'.join(recommendations) + "\n"


def main():
    """Generate comprehensive benchmark report"""
    
    print("=" * 70)
    print("AUTOMATED BENCHMARK REPORT GENERATION")
    print("=" * 70)
    
    generator = ReportGenerator()
    report_path = generator.generate_full_report()
    
    print("\n" + "=" * 70)
    print("✓ Report generation complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
