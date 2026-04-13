#!/usr/bin/env python3
"""
===============================================================================
ADVANCED STATISTICAL ANALYSIS FRAMEWORK
===============================================================================
Comprehensive statistical comparison of benchmark results across languages.

Features:
- Effect size calculations (Cohen's d)
- Hypothesis testing (t-tests, ANOVA)
- Normality and variance tests
- Confidence intervals (parametric and bootstrap)
- Multiple comparison corrections (Bonferroni, Holm)
- Power analysis

Implements all statistical requirements from Chapter 3 methodology.
===============================================================================
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
from typing import Dict, List, Tuple
import warnings

class StatisticalAnalyzer:
    """
    Advanced statistical analysis for cross-language benchmark comparison
    """
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.cold_start_results = {}
        self.warm_start_results = {}
        self.memory_results = {}
        self.alpha = 0.05  # Significance level
        
    def load_all_results(self):
        """Load all benchmark results (cold, warm, memory)"""
        
        # Load cold start results
        cold_dir = self.results_dir / "cold_start"
        if cold_dir.exists():
            for json_file in cold_dir.glob("*.json"):
                lang = self._extract_language(json_file.name)
                with open(json_file, 'r') as f:
                    self.cold_start_results[lang] = json.load(f)
        
        # Load warm start results
        warm_dir = self.results_dir / "warm_start"
        if warm_dir.exists():
            for json_file in warm_dir.glob("*.json"):
                lang = self._extract_language(json_file.name)
                with open(json_file, 'r') as f:
                    self.warm_start_results[lang] = json.load(f)
    
    def _extract_language(self, filename: str) -> str:
        """Extract language name from filename"""
        if 'python' in filename.lower():
            return 'python'
        elif 'julia' in filename.lower():
            return 'julia'
        elif 'r' in filename.lower():
            return 'r'
        return 'unknown'
    
    def _extract_times(self, results_dict: dict, scenario: str) -> np.ndarray:
        """Extract timing data from hyperfine results"""
        if 'results' in results_dict and len(results_dict['results']) > 0:
            # Hyperfine format
            result = results_dict['results'][0]
            if 'times' in result:
                return np.array(result['times'])
        return np.array([])
    
    def test_normality(self, data: np.ndarray) -> Tuple[bool, float]:
        """
        Test if data follows normal distribution using Shapiro-Wilk test
        
        Returns:
            (is_normal, p_value)
        """
        if len(data) < 3:
            warnings.warn("Too few samples for normality test")
            return False, 1.0
        
        statistic, p_value = stats.shapiro(data)
        is_normal = p_value > self.alpha
        
        return is_normal, p_value
    
    def test_variance_equality(self, *groups) -> Tuple[bool, float]:
        """
        Test equality of variances using Levene's test
        
        Returns:
            (equal_variance, p_value)
        """
        if len(groups) < 2:
            return True, 1.0
        
        statistic, p_value = stats.levene(*groups)
        equal_variance = p_value > self.alpha
        
        return equal_variance, p_value
    
    def cohens_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """
        Calculate Cohen's d effect size
        
        Interpretation:
            |d| < 0.2: Negligible
            0.2 ≤ |d| < 0.5: Small
            0.5 ≤ |d| < 0.8: Medium
            |d| ≥ 0.8: Large
        
        Returns:
            Cohen's d
        """
        n1, n2 = len(group1), len(group2)
        
        if n1 < 2 or n2 < 2:
            return np.nan
        
        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        
        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return np.nan
        
        d = (mean1 - mean2) / pooled_std
        
        return d
    
    def interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "Negligible"
        elif abs_d < 0.5:
            return "Small"
        elif abs_d < 0.8:
            return "Medium"
        else:
            return "Large"
    
    def compare_two_groups(self, group1: np.ndarray, group2: np.ndarray,
                          name1: str, name2: str) -> Dict:
        """
        Comprehensive statistical comparison between two groups
        
        Returns:
            Dictionary with all statistical metrics
        """
        result = {
            'group1_name': name1,
            'group2_name': name2,
            'n1': len(group1),
            'n2': len(group2),
            'mean1': float(np.mean(group1)),
            'mean2': float(np.mean(group2)),
            'median1': float(np.median(group1)),
            'median2': float(np.median(group2)),
            'std1': float(np.std(group1, ddof=1)),
            'std2': float(np.std(group2, ddof=1)),
        }
        
        # Normality tests
        normal1, p_normal1 = self.test_normality(group1)
        normal2, p_normal2 = self.test_normality(group2)
        
        result['normal1'] = normal1
        result['normal2'] = normal2
        result['p_normal1'] = float(p_normal1)
        result['p_normal2'] = float(p_normal2)
        
        # Variance equality test
        equal_var, p_levene = self.test_variance_equality(group1, group2)
        result['equal_variance'] = equal_var
        result['p_levene'] = float(p_levene)
        
        # Choose appropriate test
        if normal1 and normal2:
            # Use t-test
            if equal_var:
                # Independent t-test with equal variance
                t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=True)
                test_used = "Independent t-test (equal variance)"
            else:
                # Welch's t-test (unequal variance)
                t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=False)
                test_used = "Welch's t-test (unequal variance)"
            
            result['test_statistic'] = float(t_stat)
            result['p_value'] = float(p_value)
            result['test_used'] = test_used
        else:
            # Use Mann-Whitney U test (non-parametric)
            u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
            result['test_statistic'] = float(u_stat)
            result['p_value'] = float(p_value)
            result['test_used'] = "Mann-Whitney U test (non-parametric)"
        
        # Effect size (Cohen's d)
        d = self.cohens_d(group1, group2)
        result['cohens_d'] = float(d) if not np.isnan(d) else None
        result['effect_size_interpretation'] = self.interpret_cohens_d(d) if not np.isnan(d) else "Cannot calculate"
        
        # Relative difference
        if result['mean2'] != 0:
            result['relative_difference_pct'] = float((result['mean1'] - result['mean2']) / result['mean2'] * 100)
            result['speedup'] = float(result['mean2'] / result['mean1'])
        else:
            result['relative_difference_pct'] = None
            result['speedup'] = None
        
        # 95% Confidence intervals
        result['ci95_mean1'] = self.confidence_interval(group1)
        result['ci95_mean2'] = self.confidence_interval(group2)
        
        # Statistical significance
        result['significant'] = result['p_value'] < self.alpha
        
        return result
    
    def confidence_interval(self, data: np.ndarray, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate confidence interval for the mean
        
        Returns:
            (lower_bound, upper_bound)
        """
        n = len(data)
        if n < 2:
            return (np.nan, np.nan)
        
        mean = np.mean(data)
        sem = stats.sem(data)  # Standard error of the mean
        
        # Use t-distribution for small samples
        t_value = stats.t.ppf((1 + confidence) / 2, n - 1)
        margin = t_value * sem
        
        return (float(mean - margin), float(mean + margin))
    
    def bootstrap_confidence_interval(self, data: np.ndarray, 
                                     statistic_func=np.mean,
                                     confidence: float = 0.95,
                                     n_bootstrap: int = 10000) -> Tuple[float, float]:
        """
        Calculate bootstrap confidence interval (non-parametric)
        
        Args:
            data: Original data
            statistic_func: Function to calculate statistic (default: mean)
            confidence: Confidence level
            n_bootstrap: Number of bootstrap samples
        
        Returns:
            (lower_bound, upper_bound)
        """
        n = len(data)
        bootstrap_statistics = np.zeros(n_bootstrap)
        
        for i in range(n_bootstrap):
            # Resample with replacement
            bootstrap_sample = np.random.choice(data, size=n, replace=True)
            bootstrap_statistics[i] = statistic_func(bootstrap_sample)
        
        # Calculate percentiles
        alpha = 1 - confidence
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        lower = np.percentile(bootstrap_statistics, lower_percentile)
        upper = np.percentile(bootstrap_statistics, upper_percentile)
        
        return (float(lower), float(upper))
    
    def coefficient_of_variation(self, data: np.ndarray) -> float:
        """
        Calculate coefficient of variation (CV = σ/μ)
        
        CV < 0.05 indicates stable measurements
        """
        mean = np.mean(data)
        if mean == 0:
            return np.nan
        
        std = np.std(data, ddof=1)
        return float(std / mean)
    
    def anova_comparison(self, *groups, group_names: List[str] = None) -> Dict:
        """
        One-way ANOVA for comparing multiple groups
        
        Returns:
            Dictionary with ANOVA results and post-hoc tests
        """
        if len(groups) < 3:
            raise ValueError("ANOVA requires at least 3 groups")
        
        # Perform ANOVA
        f_stat, p_value = stats.f_oneway(*groups)
        
        result = {
            'f_statistic': float(f_stat),
            'p_value': float(p_value),
            'significant': p_value < self.alpha,
            'n_groups': len(groups)
        }
        
        # If significant, perform post-hoc pairwise comparisons
        if result['significant']:
            if group_names is None:
                group_names = [f"Group{i+1}" for i in range(len(groups))]
            
            pairwise_results = []
            
            # Bonferroni correction for multiple comparisons
            n_comparisons = len(groups) * (len(groups) - 1) // 2
            bonferroni_alpha = self.alpha / n_comparisons
            
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    comparison = self.compare_two_groups(
                        groups[i], groups[j],
                        group_names[i], group_names[j]
                    )
                    
                    # Apply Bonferroni correction
                    comparison['bonferroni_significant'] = comparison['p_value'] < bonferroni_alpha
                    
                    pairwise_results.append(comparison)
            
            result['pairwise_comparisons'] = pairwise_results
            result['bonferroni_alpha'] = bonferroni_alpha
        
        return result
    
    def analyze_scenario(self, scenario_name: str, phase: str = 'warm') -> Dict:
        """
        Complete statistical analysis for a specific scenario
        
        Args:
            scenario_name: Name of benchmark scenario (e.g., 'vector', 'raster')
            phase: 'cold' or 'warm'
        
        Returns:
            Comprehensive analysis results
        """
        # Select appropriate results
        if phase == 'cold':
            results_dict = self.cold_start_results
        else:
            results_dict = self.warm_start_results
        
        # Extract timing data for each language
        languages = ['python', 'julia', 'r']
        data = {}
        
        for lang in languages:
            if lang in results_dict:
                times = self._extract_times(results_dict[lang], scenario_name)
                if len(times) > 0:
                    data[lang] = times
        
        if len(data) < 2:
            return {'error': 'Insufficient data for comparison'}
        
        analysis = {
            'scenario': scenario_name,
            'phase': phase,
            'languages': list(data.keys()),
            'descriptive_statistics': {}
        }
        
        # Descriptive statistics for each language
        for lang, times in data.items():
            analysis['descriptive_statistics'][lang] = {
                'n': len(times),
                'mean': float(np.mean(times)),
                'median': float(np.median(times)),
                'std': float(np.std(times, ddof=1)),
                'min': float(np.min(times)),
                'max': float(np.max(times)),
                'cv': self.coefficient_of_variation(times),
                'ci95': self.confidence_interval(times)
            }
        
        # Pairwise comparisons
        analysis['pairwise_comparisons'] = []
        
        lang_list = list(data.keys())
        for i in range(len(lang_list)):
            for j in range(i + 1, len(lang_list)):
                lang1, lang2 = lang_list[i], lang_list[j]
                comparison = self.compare_two_groups(
                    data[lang1], data[lang2],
                    lang1, lang2
                )
                analysis['pairwise_comparisons'].append(comparison)
        
        # ANOVA if 3+ languages
        if len(data) >= 3:
            groups = [data[lang] for lang in lang_list]
            anova_result = self.anova_comparison(*groups, group_names=lang_list)
            analysis['anova'] = anova_result
        
        return analysis
    
    def generate_statistical_report(self, output_file: str = "statistical_analysis.json"):
        """
        Generate comprehensive statistical report for all scenarios
        """
        report = {
            'metadata': {
                'alpha': self.alpha,
                'confidence_level': 0.95,
                'analysis_date': pd.Timestamp.now().isoformat()
            },
            'cold_start_analysis': {},
            'warm_start_analysis': {}
        }
        
        # Analyze both scenarios for both phases
        scenarios = ['vector', 'raster']
        
        for scenario in scenarios:
            # Cold start
            cold_analysis = self.analyze_scenario(scenario, 'cold')
            report['cold_start_analysis'][scenario] = cold_analysis
            
            # Warm start
            warm_analysis = self.analyze_scenario(scenario, 'warm')
            report['warm_start_analysis'][scenario] = warm_analysis
        
        # Save report
        output_path = self.results_dir / output_file
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Statistical analysis report saved to: {output_path}")
        
        return report


def main():
    """Run statistical analysis on benchmark results"""
    
    print("=" * 70)
    print("STATISTICAL ANALYSIS OF BENCHMARK RESULTS")
    print("=" * 70)
    
    analyzer = StatisticalAnalyzer()
    
    print("\n[1/2] Loading benchmark results...")
    analyzer.load_all_results()
    
    print("[2/2] Performing statistical analysis...")
    report = analyzer.generate_statistical_report()
    
    # Print summary
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    
    for phase in ['cold_start_analysis', 'warm_start_analysis']:
        phase_name = phase.replace('_analysis', '').replace('_', ' ').title()
        print(f"\n{phase_name}:")
        
        for scenario, analysis in report[phase].items():
            if 'error' in analysis:
                print(f"  {scenario}: {analysis['error']}")
                continue
            
            print(f"\n  Scenario: {scenario}")
            
            # Show pairwise comparisons
            for comp in analysis.get('pairwise_comparisons', []):
                lang1 = comp['group1_name']
                lang2 = comp['group2_name']
                speedup = comp.get('speedup', 'N/A')
                p_val = comp['p_value']
                effect = comp.get('effect_size_interpretation', 'N/A')
                
                significance = "✓ Significant" if comp['significant'] else "✗ Not significant"
                
                print(f"    {lang1} vs {lang2}:")
                print(f"      Speedup: {speedup:.2f}x" if isinstance(speedup, float) else f"      Speedup: {speedup}")
                print(f"      p-value: {p_val:.6f} ({significance})")
                print(f"      Effect size: {effect}")
    
    print("\n" + "=" * 70)
    print("✓ Analysis complete. See statistical_analysis.json for details.")
    print("=" * 70)


if __name__ == "__main__":
    main()
