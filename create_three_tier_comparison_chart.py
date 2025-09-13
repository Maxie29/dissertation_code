#!/usr/bin/env python3
"""
Three-Tier Architecture Comparison Chart Generator

Creates comprehensive Local vs Edge vs Cloud comparison charts
similar to existing Trade-off Analysis visualizations.

Usage:
    python create_three_tier_comparison_chart.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

def setup_matplotlib():
    """Configure matplotlib for publication-quality plots."""
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['axes.axisbelow'] = True
    plt.rcParams['figure.dpi'] = 100
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['savefig.bbox'] = 'tight'

def load_experiment_data():
    """Load data from our three experiments."""
    experiments = {
        'Cloud-Heavy (SoC=20%)': 'results/20250905_130438',
        'Edge-Heavy (SoC=80%)': 'results/20250905_130448', 
        'Local-Heavy (SoC=80%)': 'results/20250905_130542'
    }
    
    data = {}
    for label, path in experiments.items():
        summary_path = Path(path) / 'summary_statistics.csv'
        per_task_path = Path(path) / 'per_task_results.csv'
        
        if summary_path.exists() and per_task_path.exists():
            summary_df = pd.read_csv(summary_path)
            per_task_df = pd.read_csv(per_task_path)
            
            data[label] = {
                'summary': summary_df.iloc[0],
                'per_task': per_task_df
            }
        else:
            print(f"WARNING: Data not found for {label} at {path}")
    
    return data

def create_energy_latency_tradeoff_chart(data, output_dir):
    """Create the main Energy vs Latency trade-off chart."""
    setup_matplotlib()
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Define colors for each tier
    colors = {
        'Cloud-Heavy (SoC=20%)': '#1f77b4',  # Blue
        'Edge-Heavy (SoC=80%)': '#ff7f0e',   # Orange  
        'Local-Heavy (SoC=80%)': '#2ca02c'   # Green
    }
    
    # Extract metrics for plotting
    latencies = []
    energies = []
    labels = []
    
    for label, exp_data in data.items():
        summary = exp_data['summary']
        
        latency_ms = summary['latency_mean_ms']
        energy_wh = summary['total_energy_wh']
        
        latencies.append(latency_ms)
        energies.append(energy_wh)
        labels.append(label)
        
        # Plot point with error bars (using P95-P50 as error estimate)
        latency_error = summary['latency_p95_ms'] - summary['latency_p50_ms']
        energy_std = summary['energy_per_task_mean_wh'] * np.sqrt(summary['total_tasks'])  # Rough estimate
        
        ax.errorbar(latency_ms, energy_wh, 
                   xerr=latency_error/4,  # Rough error estimate
                   yerr=energy_std/4,     # Rough error estimate
                   fmt='o', markersize=12, capsize=5,
                   color=colors[label], label=label)
        
        # Add execution distribution as text
        local_pct = summary['local_ratio'] * 100
        edge_pct = summary['edge_ratio'] * 100  
        cloud_pct = summary['cloud_ratio'] * 100
        
        # Position text offset from point
        text_x = latency_ms + 50
        text_y = energy_wh
        
        if 'Cloud' in label:
            dist_text = f"L:{local_pct:.0f}% E:{edge_pct:.0f}% C:{cloud_pct:.0f}%"
        else:
            dist_text = f"Local:{local_pct:.0f}% Edge:{edge_pct:.0f}%"
            
        ax.annotate(dist_text, (text_x, text_y), 
                   fontsize=9, ha='left', va='center',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=colors[label], alpha=0.2))
    
    # Formatting
    ax.set_xlabel('Average Latency (ms)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Energy Consumption (Wh)', fontsize=12, fontweight='bold')
    ax.set_title('Local vs Edge vs Cloud: Energy-Latency Trade-off Analysis', 
                fontsize=14, fontweight='bold', pad=20)
    
    # Add grid and legend
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=11)
    
    # Add annotation explaining the trade-off
    ax.text(0.02, 0.98, 
           'Energy Ranking: Cloud < Edge < Local\nLatency Ranking: Local < Cloud < Edge', 
           transform=ax.transAxes, fontsize=10,
           verticalalignment='top', horizontalalignment='left',
           bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    
    # Save the plot
    output_path = output_dir / 'three_tier_energy_latency_tradeoff.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Energy-Latency trade-off chart saved to: {output_path}")
    
    plt.show()

def create_execution_distribution_comparison(data, output_dir):
    """Create execution distribution comparison chart."""
    setup_matplotlib()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Extract data for bar chart
    scenarios = []
    local_counts = []
    edge_counts = []
    cloud_counts = []
    
    for label, exp_data in data.items():
        summary = exp_data['summary']
        scenarios.append(label.replace(' (SoC=', '\n(SoC='))  # Line break for readability
        local_counts.append(summary['local_count'])
        edge_counts.append(summary['edge_count'])
        cloud_counts.append(summary['cloud_count'])
    
    # Stacked bar chart
    x = np.arange(len(scenarios))
    width = 0.6
    
    bars1 = ax1.bar(x, local_counts, width, label='Local', color='#2ca02c', alpha=0.8)
    bars2 = ax1.bar(x, edge_counts, width, bottom=local_counts, label='Edge', color='#ff7f0e', alpha=0.8)
    bars3 = ax1.bar(x, edge_counts, width, 
                   bottom=[l+e for l,e in zip(local_counts, edge_counts)], 
                   label='Cloud', color='#1f77b4', alpha=0.8)
    
    ax1.set_xlabel('Execution Scenario', fontweight='bold')
    ax1.set_ylabel('Number of Tasks', fontweight='bold')
    ax1.set_title('Task Execution Distribution by Scenario', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios, fontsize=10)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add percentage labels on bars
    for i, (local, edge, cloud) in enumerate(zip(local_counts, edge_counts, cloud_counts)):
        total = local + edge + cloud
        if local > 0:
            ax1.text(i, local/2, f'{local/total*100:.1f}%', 
                    ha='center', va='center', fontweight='bold', color='white')
        if edge > 0:
            ax1.text(i, local + edge/2, f'{edge/total*100:.1f}%', 
                    ha='center', va='center', fontweight='bold', color='white')
        if cloud > 0:
            ax1.text(i, local + edge + cloud/2, f'{cloud/total*100:.1f}%', 
                    ha='center', va='center', fontweight='bold', color='white')
    
    # Energy consumption comparison
    energy_data = []
    energy_labels = []
    
    for label, exp_data in data.items():
        summary = exp_data['summary']
        energy_data.append(summary['total_energy_wh'])
        energy_labels.append(label.replace(' (SoC=', '\n(SoC='))
    
    colors_energy = ['#1f77b4', '#ff7f0e', '#2ca02c']
    bars_energy = ax2.bar(energy_labels, energy_data, color=colors_energy, alpha=0.8, width=0.6)
    
    ax2.set_xlabel('Execution Scenario', fontweight='bold')  
    ax2.set_ylabel('Total Energy Consumption (Wh)', fontweight='bold')
    ax2.set_title('Energy Consumption by Scenario', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar, value in zip(bars_energy, energy_data):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.3f}Wh',
                ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    
    # Save the plot
    output_path = output_dir / 'three_tier_distribution_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Distribution comparison chart saved to: {output_path}")
    
    plt.show()

def create_performance_summary_table(data, output_dir):
    """Create a comprehensive performance summary table."""
    setup_matplotlib()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')
    
    # Prepare table data
    table_data = []
    headers = ['Metric', 'Cloud-Heavy\n(SoC=20%)', 'Edge-Heavy\n(SoC=80%)', 'Local-Heavy\n(SoC=80%)']
    
    metrics = [
        ('Average Latency (ms)', 'latency_mean_ms', '{:.1f}'),
        ('Median Latency (ms)', 'latency_median_ms', '{:.1f}'),
        ('P95 Latency (ms)', 'latency_p95_ms', '{:.1f}'),
        ('Total Energy (Wh)', 'total_energy_wh', '{:.3f}'),
        ('Energy per Task (Wh)', 'energy_per_task_mean_wh', '{:.4f}'),
        ('Local Execution (%)', 'local_ratio', '{:.1f}'),
        ('Edge Execution (%)', 'edge_ratio', '{:.1f}'),
        ('Cloud Execution (%)', 'cloud_ratio', '{:.1f}'),
        ('Deadline Miss Rate (%)', 'deadline_miss_rate', '{:.1f}'),
        ('Final SoC (%)', 'final_soc', '{:.1f}'),
    ]
    
    for metric_name, metric_key, format_str in metrics:
        row = [metric_name]
        for label in ['Cloud-Heavy (SoC=20%)', 'Edge-Heavy (SoC=80%)', 'Local-Heavy (SoC=80%)']:
            if label in data:
                value = data[label]['summary'][metric_key]
                if 'ratio' in metric_key and metric_key != 'deadline_miss_rate':
                    value *= 100  # Convert to percentage
                elif metric_key == 'deadline_miss_rate':
                    value *= 100  # Already in decimal form
                formatted_value = format_str.format(value)
                row.append(formatted_value)
            else:
                row.append('N/A')
        table_data.append(row)
    
    # Create table
    table = ax.table(cellText=table_data,
                    colLabels=headers,
                    cellLoc='center',
                    loc='center',
                    bbox=[0, 0, 1, 1])
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2.0)
    
    # Color coding for headers
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#E8E8E8')
        table[(0, i)].set_text_props(weight='bold')
    
    # Color code the best values in each row (green for best)
    for row_idx, (metric_name, metric_key, _) in enumerate(metrics, 1):
        values = []
        for col_idx in range(1, 4):  # Skip metric name column
            try:
                cell_text = table[(row_idx, col_idx)].get_text().get_text()
                if cell_text != 'N/A':
                    values.append((float(cell_text), col_idx))
            except ValueError:
                continue
        
        if values:
            # Determine if lower or higher is better
            better_lower = metric_key in ['latency_mean_ms', 'latency_median_ms', 'latency_p95_ms', 
                                         'total_energy_wh', 'energy_per_task_mean_wh', 'deadline_miss_rate']
            
            if better_lower:
                best_col = min(values, key=lambda x: x[0])[1]
            else:
                best_col = max(values, key=lambda x: x[0])[1]
                
            table[(row_idx, best_col)].set_facecolor('#C8E6C9')  # Light green
    
    plt.title('Three-Tier Architecture Performance Comparison\n' + 
             'Local vs Edge vs Cloud Execution Analysis', 
             fontsize=16, fontweight='bold', pad=20)
    
    # Save the table
    output_path = output_dir / 'three_tier_performance_table.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Performance summary table saved to: {output_path}")
    
    plt.show()

def main():
    """Main execution function."""
    print("Three-Tier Architecture Comparison Chart Generator")
    print("=" * 50)
    
    # Setup output directory
    output_dir = Path('three_tier_analysis')
    output_dir.mkdir(exist_ok=True)
    
    # Load experiment data
    print("Loading experiment data...")
    data = load_experiment_data()
    
    if len(data) < 3:
        print(f"ERROR: Only found {len(data)} experiments, need 3 for comparison")
        print("Available data:", list(data.keys()))
        return
    
    print(f"Successfully loaded {len(data)} experiments:")
    for label in data.keys():
        print(f"  - {label}")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    
    try:
        create_energy_latency_tradeoff_chart(data, output_dir)
        create_execution_distribution_comparison(data, output_dir)
        create_performance_summary_table(data, output_dir)
        
        print(f"\n✅ Successfully generated three-tier comparison charts!")
        print(f"📁 Output directory: {output_dir.absolute()}")
        print(f"📊 Generated files:")
        print(f"   - three_tier_energy_latency_tradeoff.png")  
        print(f"   - three_tier_distribution_comparison.png")
        print(f"   - three_tier_performance_table.png")
        
    except Exception as e:
        print(f"❌ Error generating charts: {e}")
        raise

if __name__ == "__main__":
    main()