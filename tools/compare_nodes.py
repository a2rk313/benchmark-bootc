#!/usr/bin/env python3
"""
===============================================================================
NODE COMPARISON ANALYZER
===============================================================================
Compares benchmark results between two computing nodes (e.g., laptop vs cloud)
Generates detailed analysis for thesis Chapter 4.

Usage:
    python3 tools/compare_nodes.py \\
        --node-a results/laptop/ \\
        --node-b results/codespaces/ \\
        --output results/node_comparison.md
===============================================================================
"""

import json
import argparse
from pathlib import Path
import numpy as np
from typing import Dict, List

class NodeComparator:
    def __init__(self, node_a_dir: str, node_b_dir: str, 
                 node_a_name: str = "Laptop", node_b_name: str = "Codespaces"):
        self.node_a_dir = Path(node_a_dir)
        self.node_b_dir = Path(node_b_dir)
        self.node_a_name = node_a_name
        self.node_b_name = node_b_name
        
    def load_benchmark_results(self, results_dir: Path, scenario: str, lang: str) -> Dict:
        """Load hyperfine results JSON"""
        warm_file = results_dir / "warm_start" / f"{scenario}_{lang}_warm.json"
        
        if not warm_file.exists():
            return None
            
        with open(warm_file, 'r') as f:
            data = json.load(f)
            
        if 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            return {
                'mean': result.get('mean', 0),
                'stddev': result.get('stddev', 0),
                'median': result.get('median', 0),
                'min': result.get('min', 0),
                'max': result.get('max', 0),
                'times': result.get('times', [])
            }
        return None
    
    def compare_scenario(self, scenario: str, languages: List[str]) -> Dict:
        """Compare a specific scenario across both nodes"""
        
        comparison = {
            'scenario': scenario,
            'languages': {}
        }
        
        for lang in languages:
            node_a_result = self.load_benchmark_results(self.node_a_dir, scenario, lang)
            node_b_result = self.load_benchmark_results(self.node_b_dir, scenario, lang)
            
            if node_a_result and node_b_result:
                speedup = node_b_result['mean'] / node_a_result['mean']
                
                comparison['languages'][lang] = {
                    'node_a_mean': node_a_result['mean'],
                    'node_b_mean': node_b_result['mean'],
                    'speedup': speedup,
                    'faster_node': self.node_a_name if speedup > 1.0 else self.node_b_name,
                    'difference_pct': abs(1 - speedup) * 100
                }
        
        return comparison
    
    def generate_markdown_report(self, comparisons: List[Dict], output_file: str):
        """Generate comprehensive markdown report"""
        
        report = []
        
        # Header
        report.append("# Multi-Node Performance Comparison")
        report.append(f"\n**Node A:** {self.node_a_name}")
        report.append(f"**Node B:** {self.node_b_name}")
        report.append("\n---\n")
        
        # Executive Summary
        report.append("## Executive Summary\n")
        
        # Find overall patterns
        node_a_wins = 0
        node_b_wins = 0
        total_comparisons = 0
        
        for comp in comparisons:
            for lang, data in comp['languages'].items():
                total_comparisons += 1
                if data['faster_node'] == self.node_a_name:
                    node_a_wins += 1
                else:
                    node_b_wins += 1
        
        report.append(f"**Total Comparisons:** {total_comparisons}")
        report.append(f"**{self.node_a_name} Faster:** {node_a_wins} times ({node_a_wins/total_comparisons*100:.1f}%)")
        report.append(f"**{self.node_b_name} Faster:** {node_b_wins} times ({node_b_wins/total_comparisons*100:.1f}%)\n")
        
        # Detailed Scenario Comparison
        for comp in comparisons:
            scenario_name = comp['scenario'].replace('_', ' ').title()
            report.append(f"## {scenario_name}\n")
            
            # Create comparison table
            report.append("| Language | Node A Time (s) | Node B Time (s) | Speedup | Faster Node | Difference |")
            report.append("|----------|----------------|----------------|---------|-------------|------------|")
            
            for lang, data in comp['languages'].items():
                speedup_str = f"{data['speedup']:.2f}×"
                diff_str = f"{data['difference_pct']:.1f}%"
                
                report.append(
                    f"| {lang.capitalize():8s} | "
                    f"{data['node_a_mean']:14.3f} | "
                    f"{data['node_b_mean']:14.3f} | "
                    f"{speedup_str:7s} | "
                    f"{data['faster_node']:11s} | "
                    f"{diff_str:10s} |"
                )
            
            report.append("")
            
            # Analysis
            report.append("### Analysis\n")
            
            # Find language with biggest difference
            max_diff_lang = max(comp['languages'].items(), 
                               key=lambda x: x[1]['difference_pct'])
            
            report.append(
                f"**{max_diff_lang[0].capitalize()}** shows the largest performance "
                f"variance ({max_diff_lang[1]['difference_pct']:.1f}% difference), "
                f"with {max_diff_lang[1]['faster_node']} performing better.\n"
            )
        
        # Performance Portability Analysis
        report.append("---\n")
        report.append("## Performance Portability Analysis\n")
        
        report.append("### Language-Specific Portability\n")
        
        # Calculate average variance per language
        lang_variances = {}
        for comp in comparisons:
            for lang, data in comp['languages'].items():
                if lang not in lang_variances:
                    lang_variances[lang] = []
                lang_variances[lang].append(data['difference_pct'])
        
        report.append("| Language | Avg. Variance | Portability Rating |")
        report.append("|----------|--------------|-------------------|")
        
        for lang, variances in sorted(lang_variances.items()):
            avg_var = np.mean(variances)
            
            if avg_var < 10:
                rating = "Excellent"
            elif avg_var < 20:
                rating = "Good"
            elif avg_var < 30:
                rating = "Moderate"
            else:
                rating = "Variable"
            
            report.append(f"| {lang.capitalize():8s} | {avg_var:12.1f}% | {rating:17s} |")
        
        report.append("")
        
        # Conclusions
        report.append("## Conclusions\n")
        
        best_portable = min(lang_variances.items(), key=lambda x: np.mean(x[1]))
        worst_portable = max(lang_variances.items(), key=lambda x: np.mean(x[1]))
        
        report.append(
            f"1. **Most Portable:** {best_portable[0].capitalize()} "
            f"({np.mean(best_portable[1]):.1f}% average variance across platforms)\n"
        )
        
        report.append(
            f"2. **Least Portable:** {worst_portable[0].capitalize()} "
            f"({np.mean(worst_portable[1]):.1f}% average variance)\n"
        )
        
        if node_a_wins > node_b_wins:
            report.append(
                f"3. **Platform Preference:** {self.node_a_name} demonstrates superior "
                f"performance in {node_a_wins/total_comparisons*100:.0f}% of comparisons, "
                f"likely due to higher single-threaded clock speeds.\n"
            )
        else:
            report.append(
                f"3. **Platform Preference:** {self.node_b_name} demonstrates superior "
                f"performance in {node_b_wins/total_comparisons*100:.0f}% of comparisons.\n"
            )
        
        # Save report
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(report))
        
        print(f"✓ Node comparison report saved to: {output_path}")
        
        return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Compare benchmark results across two compute nodes'
    )
    parser.add_argument(
        '--node-a',
        required=True,
        help='Path to Node A results directory (e.g., results/laptop/)'
    )
    parser.add_argument(
        '--node-b',
        required=True,
        help='Path to Node B results directory (e.g., results/codespaces/)'
    )
    parser.add_argument(
        '--node-a-name',
        default='Laptop',
        help='Name for Node A (default: Laptop)'
    )
    parser.add_argument(
        '--node-b-name',
        default='Codespaces',
        help='Name for Node B (default: Codespaces)'
    )
    parser.add_argument(
        '--output',
        default='results/node_comparison.md',
        help='Output file path (default: results/node_comparison.md)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("NODE COMPARISON ANALYZER")
    print("=" * 70)
    print()
    
    comparator = NodeComparator(
        args.node_a,
        args.node_b,
        args.node_a_name,
        args.node_b_name
    )
    
    # Scenarios to compare
    scenarios = ['vector', 'interpolation', 'timeseries', 'raster']
    languages = ['python', 'julia', 'r']
    
    print("Comparing scenarios:")
    comparisons = []
    
    for scenario in scenarios:
        print(f"  - {scenario}...")
        comparison = comparator.compare_scenario(scenario, languages)
        if comparison['languages']:  # Only add if we have data
            comparisons.append(comparison)
    
    print()
    print("Generating report...")
    report_path = comparator.generate_markdown_report(comparisons, args.output)
    
    print()
    print("=" * 70)
    print("✓ Analysis complete!")
    print(f"  View report: cat {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
