#!/usr/bin/env python3
"""
===============================================================================
PUBLICATION-READY VISUALIZATION GENERATOR
===============================================================================
Creates professional figures for thesis and publications including:
- Performance comparison bar charts
- Box plots with statistical annotations
- Speedup comparison charts
- Memory usage comparisons
- Cold vs warm start comparisons

All figures are publication-quality (300 DPI, vector format options)
===============================================================================
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple

# Set publication-quality defaults
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'serif'
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9

# Color palette (colorblind-friendly)
COLORS = {
    'python': '#E69F00',  # Orange
    'julia': '#56B4E9',   # Sky blue
    'r': '#009E73'        # Green
}

class Visualizer:
    """
    Generate publication-quality visualizations
    """
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.figures_dir = self.results_dir / "figures"
        self.figures_dir.mkdir(exist_ok=True)
        
        # Set seaborn style
        sns.set_style("whitegrid")
        sns.set_palette([COLORS['python'], COLORS['julia'], COLORS['r']])
    
    def load_hyperfine_results(self, filename: str) -> Dict:
        """Load results from hyperfine JSON"""
        filepath = self.results_dir / filename
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def extract_times(self, results: Dict) -> np.ndarray:
        """Extract timing array from hyperfine results"""
        if results and 'results' in results and len(results['results']) > 0:
            return np.array(results['results'][0]['times'])
        return np.array([])
    
    def create_performance_comparison(self, scenario: str, phase: str = 'warm'):
        """
        Create bar chart comparing mean execution times
        
        Args:
            scenario: 'vector' or 'raster'
            phase: 'cold' or 'warm'
        """
        # Load data
        phase_dir = "warm_start" if phase == "warm" else "cold_start"
        
        data = []
        for lang in ['python', 'julia', 'r']:
            results = self.load_hyperfine_results(
                f"{phase_dir}/{scenario}_{lang}_{phase}.json"
            )
            if results:
                times = self.extract_times(results)
                if len(times) > 0:
                    data.append({
                        'Language': lang.capitalize(),
                        'Mean Time (s)': np.mean(times),
                        'Std Dev': np.std(times, ddof=1)
                    })
        
        if not data:
            print(f"No data for {scenario} {phase} comparison")
            return
        
        df = pd.DataFrame(data)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 6))
        
        x = np.arange(len(df))
        bars = ax.bar(x, df['Mean Time (s)'], 
                      yerr=df['Std Dev'],
                      color=[COLORS[lang.lower()] for lang in df['Language']],
                      capsize=5, alpha=0.8, edgecolor='black', linewidth=1)
        
        ax.set_xlabel('Language', fontweight='bold')
        ax.set_ylabel('Execution Time (seconds)', fontweight='bold')
        
        scenario_name = "Vector Operations" if scenario == "vector" else "Raster Operations"
        phase_name = "Cold Start" if phase == "cold" else "Warm Start"
        ax.set_title(f'{scenario_name}: {phase_name} Performance', fontweight='bold')
        
        ax.set_xticks(x)
        ax.set_xticklabels(df['Language'])
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}s',
                   ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        # Save
        filename = f"{scenario}_{phase}_comparison.png"
        plt.savefig(self.figures_dir / filename, dpi=300, bbox_inches='tight')
        plt.savefig(self.figures_dir / filename.replace('.png', '.pdf'), 
                   format='pdf', bbox_inches='tight')
        print(f"  ✓ Saved: {filename}")
        plt.close()
    
    def create_boxplot_comparison(self, scenario: str, phase: str = 'warm'):
        """
        Create box plots showing distribution of execution times
        """
        # Load data
        phase_dir = "warm_start" if phase == "warm" else "cold_start"
        
        data = []
        for lang in ['python', 'julia', 'r']:
            results = self.load_hyperfine_results(
                f"{phase_dir}/{scenario}_{lang}_{phase}.json"
            )
            if results:
                times = self.extract_times(results)
                for time_val in times:
                    data.append({
                        'Language': lang.capitalize(),
                        'Time (s)': time_val
                    })
        
        if not data:
            print(f"No data for {scenario} {phase} boxplot")
            return
        
        df = pd.DataFrame(data)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create boxplot with custom colors
        bp = df.boxplot(column='Time (s)', by='Language', ax=ax,
                        patch_artist=True, return_type='dict')
        
        # Color the boxes
        for patch, lang in zip(bp['boxes'], df['Language'].unique()):
            patch.set_facecolor(COLORS[lang.lower()])
            patch.set_alpha(0.7)
        
        scenario_name = "Vector Operations" if scenario == "vector" else "Raster Operations"
        phase_name = "Cold Start" if phase == "cold" else "Warm Start"
        ax.set_title(f'{scenario_name}: {phase_name} Distribution', fontweight='bold')
        ax.set_xlabel('Language', fontweight='bold')
        ax.set_ylabel('Execution Time (seconds)', fontweight='bold')
        
        plt.suptitle('')  # Remove default title
        
        plt.tight_layout()
        
        # Save
        filename = f"{scenario}_{phase}_boxplot.png"
        plt.savefig(self.figures_dir / filename, dpi=300, bbox_inches='tight')
        plt.savefig(self.figures_dir / filename.replace('.png', '.pdf'),
                   format='pdf', bbox_inches='tight')
        print(f"  ✓ Saved: {filename}")
        plt.close()
    
    def create_speedup_chart(self, scenario: str, phase: str = 'warm'):
        """
        Create speedup comparison chart (relative to Python baseline)
        """
        # Load data
        phase_dir = "warm_start" if phase == "warm" else "cold_start"
        
        means = {}
        for lang in ['python', 'julia', 'r']:
            results = self.load_hyperfine_results(
                f"{phase_dir}/{scenario}_{lang}_{phase}.json"
            )
            if results:
                times = self.extract_times(results)
                if len(times) > 0:
                    means[lang] = np.mean(times)
        
        if 'python' not in means or len(means) < 2:
            print(f"Insufficient data for {scenario} {phase} speedup chart")
            return
        
        # Calculate speedups (Python = baseline)
        baseline = means['python']
        speedups = {lang: baseline / time for lang, time in means.items()}
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 6))
        
        languages = list(speedups.keys())
        languages_cap = [lang.capitalize() for lang in languages]
        speedup_values = [speedups[lang] for lang in languages]
        colors_list = [COLORS[lang] for lang in languages]
        
        bars = ax.bar(languages_cap, speedup_values,
                     color=colors_list, alpha=0.8,
                     edgecolor='black', linewidth=1)
        
        # Add reference line at 1.0
        ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1.5,
                  label='Baseline (Python)', alpha=0.7)
        
        ax.set_xlabel('Language', fontweight='bold')
        ax.set_ylabel('Speedup (× faster than Python)', fontweight='bold')
        
        scenario_name = "Vector Operations" if scenario == "vector" else "Raster Operations"
        phase_name = "Cold Start" if phase == "cold" else "Warm Start"
        ax.set_title(f'{scenario_name}: {phase_name} Speedup', fontweight='bold')
        
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            label = f'{height:.2f}×' if height >= 1.0 else f'{height:.2f}×'
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   label, ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        
        # Save
        filename = f"{scenario}_{phase}_speedup.png"
        plt.savefig(self.figures_dir / filename, dpi=300, bbox_inches='tight')
        plt.savefig(self.figures_dir / filename.replace('.png', '.pdf'),
                   format='pdf', bbox_inches='tight')
        print(f"  ✓ Saved: {filename}")
        plt.close()
    
    def create_cold_vs_warm_comparison(self, scenario: str):
        """
        Compare cold start vs warm start for each language
        """
        data = []
        
        for lang in ['python', 'julia', 'r']:
            # Cold start
            cold_results = self.load_hyperfine_results(
                f"cold_start/{scenario}_{lang}_cold.json"
            )
            if cold_results:
                cold_times = self.extract_times(cold_results)
                if len(cold_times) > 0:
                    data.append({
                        'Language': lang.capitalize(),
                        'Phase': 'Cold Start',
                        'Mean Time (s)': np.mean(cold_times)
                    })
            
            # Warm start
            warm_results = self.load_hyperfine_results(
                f"warm_start/{scenario}_{lang}_warm.json"
            )
            if warm_results:
                warm_times = self.extract_times(warm_results)
                if len(warm_times) > 0:
                    data.append({
                        'Language': lang.capitalize(),
                        'Phase': 'Warm Start',
                        'Mean Time (s)': np.mean(warm_times)
                    })
        
        if not data:
            print(f"No data for {scenario} cold vs warm comparison")
            return
        
        df = pd.DataFrame(data)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Grouped bar chart
        languages = df['Language'].unique()
        x = np.arange(len(languages))
        width = 0.35
        
        cold_data = df[df['Phase'] == 'Cold Start'].set_index('Language')['Mean Time (s)']
        warm_data = df[df['Phase'] == 'Warm Start'].set_index('Language')['Mean Time (s)']
        
        bars1 = ax.bar(x - width/2, [cold_data.get(lang, 0) for lang in languages],
                      width, label='Cold Start', alpha=0.8,
                      color='#D55E00', edgecolor='black')
        
        bars2 = ax.bar(x + width/2, [warm_data.get(lang, 0) for lang in languages],
                      width, label='Warm Start', alpha=0.8,
                      color='#0072B2', edgecolor='black')
        
        ax.set_xlabel('Language', fontweight='bold')
        ax.set_ylabel('Execution Time (seconds)', fontweight='bold')
        
        scenario_name = "Vector Operations" if scenario == "vector" else "Raster Operations"
        ax.set_title(f'{scenario_name}: Cold Start vs Warm Start', fontweight='bold')
        
        ax.set_xticks(x)
        ax.set_xticklabels(languages)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.2f}s',
                           ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        
        # Save
        filename = f"{scenario}_cold_vs_warm.png"
        plt.savefig(self.figures_dir / filename, dpi=300, bbox_inches='tight')
        plt.savefig(self.figures_dir / filename.replace('.png', '.pdf'),
                   format='pdf', bbox_inches='tight')
        print(f"  ✓ Saved: {filename}")
        plt.close()
    
    def create_memory_comparison(self, scenario: str):
        """
        Create memory usage comparison chart
        """
        # Parse memory files
        memory_dir = self.results_dir / "memory"
        if not memory_dir.exists():
            print("Memory profiling results not found")
            return
        
        data = []
        for lang in ['python', 'julia', 'r']:
            mem_file = memory_dir / f"{scenario}_{lang}_memory.txt"
            if mem_file.exists():
                with open(mem_file, 'r') as f:
                    content = f.read()
                    # Extract maximum resident set size
                    for line in content.split('\n'):
                        if 'Maximum resident set size' in line:
                            # Extract number (in KB)
                            kb_value = int(line.split(':')[-1].strip())
                            mb_value = kb_value / 1024
                            data.append({
                                'Language': lang.capitalize(),
                                'Memory (MB)': mb_value
                            })
                            break
        
        if not data:
            print(f"No memory data for {scenario}")
            return
        
        df = pd.DataFrame(data)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 6))
        
        bars = ax.bar(df['Language'], df['Memory (MB)'],
                     color=[COLORS[lang.lower()] for lang in df['Language']],
                     alpha=0.8, edgecolor='black', linewidth=1)
        
        ax.set_xlabel('Language', fontweight='bold')
        ax.set_ylabel('Peak Memory Usage (MB)', fontweight='bold')
        
        scenario_name = "Vector Operations" if scenario == "vector" else "Raster Operations"
        ax.set_title(f'{scenario_name}: Memory Efficiency', fontweight='bold')
        
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f} MB',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        
        # Save
        filename = f"{scenario}_memory_comparison.png"
        plt.savefig(self.figures_dir / filename, dpi=300, bbox_inches='tight')
        plt.savefig(self.figures_dir / filename.replace('.png', '.pdf'),
                   format='pdf', bbox_inches='tight')
        print(f"  ✓ Saved: {filename}")
        plt.close()
    
    def generate_all_figures(self):
        """Generate all visualization figures"""
        
        scenarios = ['vector', 'raster']
        phases = ['cold', 'warm']
        
        print("\nGenerating performance comparison charts...")
        for scenario in scenarios:
            for phase in phases:
                self.create_performance_comparison(scenario, phase)
        
        print("\nGenerating box plots...")
        for scenario in scenarios:
            for phase in phases:
                self.create_boxplot_comparison(scenario, phase)
        
        print("\nGenerating speedup charts...")
        for scenario in scenarios:
            for phase in phases:
                self.create_speedup_chart(scenario, phase)
        
        print("\nGenerating cold vs warm comparisons...")
        for scenario in scenarios:
            self.create_cold_vs_warm_comparison(scenario)
        
        print("\nGenerating memory comparisons...")
        for scenario in scenarios:
            self.create_memory_comparison(scenario)
        
        print(f"\n✓ All figures saved to: {self.figures_dir}")
        print(f"  PNG format: Publication-ready (300 DPI)")
        print(f"  PDF format: Vector graphics for LaTeX")


def main():
    """Generate all visualizations"""
    
    print("=" * 70)
    print("PUBLICATION-READY VISUALIZATION GENERATION")
    print("=" * 70)
    
    visualizer = Visualizer()
    visualizer.generate_all_figures()
    
    print("\n" + "=" * 70)
    print("✓ Visualization generation complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
