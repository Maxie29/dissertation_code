"""
Results Visualization Script for Battery Offloading Simulation.

This script generates comprehensive visualizations from simulation results using matplotlib.
It supports both single simulation results and sweep result analysis.

Usage:
    python -m battery_offloading.plot_results --results-dir results/20250829_180119
    python -m battery_offloading.plot_results --results-dir results/sweep_20250829_175938
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
from datetime import datetime


def setup_matplotlib():
    """Configure matplotlib for consistent, publication-quality plots."""
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['axes.axisbelow'] = True
    plt.rcParams['figure.dpi'] = 100
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['savefig.bbox'] = 'tight'


def find_latest_results(base_dir):
    """
    Find the most recent simulation results directory.
    
    Args:
        base_dir: Base directory to search for results
        
    Returns:
        tuple: (results_dir, per_task_file, summary_file) or None if not found
    """
    results_path = Path(base_dir)
    
    if not results_path.exists():
        return None
    
    # Look for per_task_results.csv and summary_statistics.csv directly
    per_task_file = results_path / "per_task_results.csv"
    summary_file = results_path / "summary_statistics.csv"
    
    if per_task_file.exists() and summary_file.exists():
        return results_path, per_task_file, summary_file
    
    # Look for timestamp directories (single simulation results)
    timestamp_dirs = []
    for item in results_path.iterdir():
        if item.is_dir():
            # Check for timestamp pattern
            name = item.name.replace('_', '').replace('-', '')
            if name.isdigit() and len(name) >= 8:
                timestamp_dirs.append(item)
    
    if timestamp_dirs:
        # Get the most recent directory
        latest_dir = max(timestamp_dirs, key=lambda x: x.name)
        per_task_file = latest_dir / "per_task_results.csv"
        summary_file = latest_dir / "summary_statistics.csv"
        
        if per_task_file.exists() and summary_file.exists():
            return latest_dir, per_task_file, summary_file
    
    return None


def plot_latency_distribution(per_task_df, save_path):
    """
    Plot histogram of task latency distribution with execution site breakdown.
    
    Args:
        per_task_df: DataFrame with per-task results
        save_path: Path to save the plot
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Find latency column
    latency_col = None
    for col in ['latency_ms', 'total_latency_s', 'task_latency_ms']:
        if col in per_task_df.columns:
            latency_col = col
            break
    
    if not latency_col:
        ax.text(0.5, 0.5, 'No latency data available', 
                transform=ax.transAxes, ha='center', va='center', fontsize=16)
        ax.set_title('Task Latency Distribution (No Data Available)')
    else:
        # Convert to milliseconds if needed
        if latency_col == 'total_latency_s':
            latency_data = per_task_df[latency_col] * 1000
            unit = 'ms'
        else:
            latency_data = per_task_df[latency_col]
            unit = 'ms'
        
        # Create histogram with execution site coloring
        if 'execution_site' in per_task_df.columns:
            sites = per_task_df['execution_site'].unique()
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Blue, Orange, Green
            
            for i, site in enumerate(sites):
                site_data = per_task_df[per_task_df['execution_site'] == site]
                if len(site_data) > 0:
                    ax.hist(site_data[latency_col] if latency_col != 'total_latency_s' 
                           else site_data[latency_col] * 1000, 
                           bins=20, alpha=0.7, 
                           label=f'{site} ({len(site_data)} tasks)', 
                           color=colors[i % len(colors)])
        else:
            ax.hist(latency_data, bins=20, alpha=0.7, color='#1f77b4')
        
        # Add statistics lines
        mean_latency = latency_data.mean()
        p95_latency = latency_data.quantile(0.95)
        ax.axvline(mean_latency, color='red', linestyle='--', alpha=0.7, linewidth=2)
        ax.axvline(p95_latency, color='orange', linestyle='--', alpha=0.7, linewidth=2)
        
        ax.set_xlabel(f'Task Latency ({unit})')
        ax.set_ylabel('Number of Tasks')
        ax.set_title('Task Latency Distribution by Execution Site')
        
        # Create legend with statistics
        legend_labels = []
        if 'execution_site' in per_task_df.columns:
            legend_labels.extend([f'{site} ({len(per_task_df[per_task_df["execution_site"] == site])} tasks)' 
                                for site in per_task_df['execution_site'].unique()])
        legend_labels.extend([f'Mean: {mean_latency:.1f}{unit}', f'P95: {p95_latency:.1f}{unit}'])
        ax.legend(legend_labels)
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Latency distribution plot saved to: {save_path}")


def plot_soc_curve(per_task_df, save_path):
    """
    Plot battery State of Charge (SoC) over time.
    
    Args:
        per_task_df: DataFrame with per-task results
        save_path: Path to save the plot
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Check for required columns
    if 'soc_after' in per_task_df.columns and 'completion_time_s' in per_task_df.columns:
        time_data = per_task_df['completion_time_s']
        soc_data = per_task_df['soc_after']
        
        # Add initial point if available
        if 'soc_before' in per_task_df.columns and len(per_task_df) > 0:
            initial_soc = per_task_df.iloc[0]['soc_before']
            time_data = [0] + time_data.tolist()
            soc_data = [initial_soc] + soc_data.tolist()
        
        # Main SoC curve
        ax.plot(time_data, soc_data, 'b-', linewidth=3, marker='o', markersize=4, label='Battery SoC')
        
        # Add execution site markers
        if 'execution_site' in per_task_df.columns:
            site_colors = {'LOCAL': '#1f77b4', 'EDGE': '#ff7f0e', 'CLOUD': '#2ca02c'}
            for site, color in site_colors.items():
                site_mask = per_task_df['execution_site'] == site
                if site_mask.any():
                    ax.scatter(per_task_df[site_mask]['completion_time_s'], 
                             per_task_df[site_mask]['soc_after'],
                             c=color, s=50, alpha=0.8, label=f'{site} tasks', zorder=5)
        
        # Add SoC threshold line if available in summary
        ax.axhline(y=30, color='red', linestyle='--', alpha=0.5, label='SoC Threshold (30%)')
        
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Battery State of Charge (%)')
        ax.set_title('Battery SoC Curve Over Simulation Time')
        ax.set_ylim(0, 100)
        ax.legend()
        
        # Add annotations for key points
        final_soc = soc_data[-1] if isinstance(soc_data, list) else soc_data.iloc[-1]
        ax.annotate(f'Final SoC: {final_soc:.1f}%', 
                   xy=(time_data[-1] if isinstance(time_data, list) else time_data.iloc[-1], final_soc),
                   xytext=(10, 10), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
    else:
        ax.text(0.5, 0.5, 'SoC curve data not available\nRequired: soc_after, completion_time_s', 
                transform=ax.transAxes, ha='center', va='center', fontsize=14)
        ax.set_title('Battery SoC Curve (No Data Available)')
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Battery SoC (%)')
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"SoC curve plot saved to: {save_path}")


def plot_energy_boxplot(per_task_df, save_path):
    """
    Plot box plot of energy consumption by execution site.
    
    Args:
        per_task_df: DataFrame with per-task results
        save_path: Path to save the plot
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Find energy column
    energy_col = None
    for col in ['energy_wh', 'total_energy_wh', 'energy_consumed_wh', 'task_energy_wh']:
        if col in per_task_df.columns:
            energy_col = col
            break
    
    if energy_col and 'execution_site' in per_task_df.columns:
        # Prepare data for box plot
        sites = sorted(per_task_df['execution_site'].unique())
        energy_by_site = []
        site_labels = []
        
        for site in sites:
            site_data = per_task_df[per_task_df['execution_site'] == site][energy_col]
            if len(site_data) > 0:
                energy_by_site.append(site_data.values)
                site_labels.append(f'{site}\\n(n={len(site_data)})')
        
        if energy_by_site:
            # Create box plot
            box_plot = ax.boxplot(energy_by_site, labels=site_labels, patch_artist=True)
            
            # Color the boxes
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
            for patch, color in zip(box_plot['boxes'], colors[:len(energy_by_site)]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            # Add mean markers
            for i, data in enumerate(energy_by_site):
                mean_val = np.mean(data)
                ax.scatter(i+1, mean_val, marker='D', color='red', s=50, zorder=10)
                ax.text(i+1, mean_val, f'{mean_val:.4f}', ha='center', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
            
            ax.set_xlabel('Execution Site')
            ax.set_ylabel('Energy Consumption per Task (Wh)')
            ax.set_title('Energy Consumption Distribution by Execution Site')
        else:
            ax.text(0.5, 0.5, 'No energy data for plotting', 
                   transform=ax.transAxes, ha='center', va='center', fontsize=14)
            ax.set_title('Energy Consumption Box Plot (No Data)')
    else:
        ax.text(0.5, 0.5, f'Energy data not available\\nRequired: {energy_col or "energy_wh"}, execution_site\\nAvailable: {list(per_task_df.columns)[:10]}...', 
                transform=ax.transAxes, ha='center', va='center', fontsize=12)
        ax.set_title('Energy Consumption Box Plot (No Data Available)')
        ax.set_xlabel('Execution Site')
        ax.set_ylabel('Energy Consumption (Wh)')
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Energy box plot saved to: {save_path}")


def plot_distribution_pies(per_task_df, save_path):
    """
    Plot pie charts showing distribution of tasks across execution sites and task types.
    
    Args:
        per_task_df: DataFrame with per-task results
        save_path: Path to save the plot
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Execution Site Distribution
    if 'execution_site' in per_task_df.columns:
        site_counts = per_task_df['execution_site'].value_counts()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        
        wedges, texts, autotexts = ax1.pie(site_counts.values, 
                                          labels=site_counts.index,
                                          colors=colors[:len(site_counts)],
                                          autopct='%1.1f%%',
                                          startangle=90,
                                          textprops={'fontsize': 11})
        
        ax1.set_title('Task Distribution by Execution Site', fontsize=14, fontweight='bold')
        
        # Add count information
        total_tasks = len(per_task_df)
        info_text = f'Total Tasks: {total_tasks}\\n'
        for site, count in site_counts.items():
            info_text += f'{site}: {count} tasks\\n'
        ax1.text(0, -1.4, info_text, transform=ax1.transAxes, ha='center', va='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
    else:
        ax1.text(0.5, 0.5, 'Execution site data\\nnot available', 
                transform=ax1.transAxes, ha='center', va='center', fontsize=14)
        ax1.set_title('Execution Site Distribution (No Data)')
    
    # Task Type Distribution
    if 'task_type' in per_task_df.columns:
        type_counts = per_task_df['task_type'].value_counts()
        colors = ['#d62728', '#9467bd', '#8c564b']
        
        wedges, texts, autotexts = ax2.pie(type_counts.values,
                                          labels=type_counts.index,
                                          colors=colors[:len(type_counts)],
                                          autopct='%1.1f%%',
                                          startangle=90,
                                          textprops={'fontsize': 11})
        
        ax2.set_title('Task Distribution by Task Type', fontsize=14, fontweight='bold')
        
        # Add count information
        info_text = ''
        for task_type, count in type_counts.items():
            info_text += f'{task_type}: {count} tasks\\n'
        ax2.text(0, -1.4, info_text, transform=ax2.transAxes, ha='center', va='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
    else:
        ax2.text(0.5, 0.5, 'Task type data\\nnot available', 
                transform=ax2.transAxes, ha='center', va='center', fontsize=14)
        ax2.set_title('Task Type Distribution (No Data)')
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Distribution pie charts saved to: {save_path}")


def plot_task_timeline(per_task_df, save_path):
    """
    Plot task execution timeline with execution site coloring.
    
    Args:
        per_task_df: DataFrame with per-task results
        save_path: Path to save the plot
    """
    fig, ax = plt.subplots(figsize=(14, 8))
    
    if ('arrival_time_s' in per_task_df.columns and 
        'completion_time_s' in per_task_df.columns and
        len(per_task_df) > 0):
        
        # Color mapping for execution sites
        color_map = {'LOCAL': '#1f77b4', 'EDGE': '#ff7f0e', 'CLOUD': '#2ca02c'}
        
        # Sort by arrival time for better visualization
        df_sorted = per_task_df.sort_values('arrival_time_s')
        
        # Plot each task as a horizontal bar
        for i, (_, row) in enumerate(df_sorted.iterrows()):
            start_time = row['arrival_time_s']
            end_time = row['completion_time_s']
            site = row.get('execution_site', 'UNKNOWN')
            color = color_map.get(site, '#cccccc')
            
            # Calculate processing time (queue + execution)
            duration = end_time - start_time
            
            ax.barh(i, duration, left=start_time, 
                   color=color, alpha=0.7, height=0.8,
                   edgecolor='black', linewidth=0.5)
            
            # Add task ID annotation for first few tasks
            if i < 10:
                task_id = row.get('task_id', i)
                ax.text(start_time + duration/2, i, f'T{task_id}', 
                       ha='center', va='center', fontsize=8, fontweight='bold')
        
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Task Index (sorted by arrival time)')
        ax.set_title('Task Execution Timeline by Site')
        
        # Create custom legend
        legend_elements = []
        for site, color in color_map.items():
            if site in per_task_df.get('execution_site', pd.Series()).values:
                count = len(per_task_df[per_task_df['execution_site'] == site])
                legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, alpha=0.7, 
                                                   label=f'{site} ({count} tasks)'))
        ax.legend(handles=legend_elements, loc='upper right')
        
        # Add grid for time reference
        ax.grid(True, axis='x', alpha=0.3)
        
    else:
        ax.text(0.5, 0.5, 'Timeline data not available\\nRequired: arrival_time_s, completion_time_s', 
                transform=ax.transAxes, ha='center', va='center', fontsize=14)
        ax.set_title('Task Timeline (No Data Available)')
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Task Index')
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Task timeline plot saved to: {save_path}")


def plot_performance_summary(per_task_df, summary_df, save_path):
    """
    Plot a comprehensive performance summary with multiple metrics.
    
    Args:
        per_task_df: DataFrame with per-task results
        summary_df: DataFrame with summary statistics
        save_path: Path to save the plot
    """
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Latency vs Task Index (showing system performance over time)
    if 'latency_ms' in per_task_df.columns or 'total_latency_s' in per_task_df.columns:
        latency_col = 'latency_ms' if 'latency_ms' in per_task_df.columns else 'total_latency_s'
        latency_data = per_task_df[latency_col]
        if latency_col == 'total_latency_s':
            latency_data = latency_data * 1000
        
        ax1.plot(latency_data.index, latency_data, 'b-', alpha=0.7, linewidth=2)
        ax1.axhline(latency_data.mean(), color='red', linestyle='--', alpha=0.7, label=f'Mean: {latency_data.mean():.1f}ms')
        ax1.set_xlabel('Task Index')
        ax1.set_ylabel('Latency (ms)')
        ax1.set_title('Task Latency Over Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
    else:
        ax1.text(0.5, 0.5, 'No latency data', transform=ax1.transAxes, ha='center', va='center')
        ax1.set_title('Task Latency Over Time (No Data)')
    
    # 2. Energy consumption per task
    energy_col = None
    for col in ['energy_wh', 'total_energy_wh', 'energy_consumed_wh']:
        if col in per_task_df.columns:
            energy_col = col
            break
    
    if energy_col:
        ax2.bar(range(len(per_task_df)), per_task_df[energy_col], alpha=0.7, color='green')
        ax2.axhline(per_task_df[energy_col].mean(), color='red', linestyle='--', 
                   label=f'Mean: {per_task_df[energy_col].mean():.4f}Wh')
        ax2.set_xlabel('Task Index')
        ax2.set_ylabel('Energy (Wh)')
        ax2.set_title('Energy Consumption per Task')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    else:
        ax2.text(0.5, 0.5, 'No energy data', transform=ax2.transAxes, ha='center', va='center')
        ax2.set_title('Energy Consumption per Task (No Data)')
    
    # 3. Execution site over time
    if 'execution_site' in per_task_df.columns:
        sites = per_task_df['execution_site'].unique()
        site_to_num = {site: i for i, site in enumerate(sites)}
        site_nums = [site_to_num[site] for site in per_task_df['execution_site']]
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        for i, site in enumerate(sites):
            site_mask = per_task_df['execution_site'] == site
            ax3.scatter(per_task_df[site_mask].index, 
                       [site_to_num[site]] * sum(site_mask),
                       c=colors[i % len(colors)], alpha=0.7, s=50, label=site)
        
        ax3.set_xlabel('Task Index')
        ax3.set_ylabel('Execution Site')
        ax3.set_yticks(range(len(sites)))
        ax3.set_yticklabels(sites)
        ax3.set_title('Task Execution Site Over Time')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, 'No execution site data', transform=ax3.transAxes, ha='center', va='center')
        ax3.set_title('Task Execution Site Over Time (No Data)')
    
    # 4. Summary metrics bar chart
    if len(summary_df) > 0:
        # Try to extract key metrics from summary
        metrics_to_plot = {}
        for _, row in summary_df.iterrows():
            metric_name = row.get('metric', row.get('Metric', str(row.iloc[0])))
            value = row.get('value', row.get('Value', row.iloc[1]))
            
            # Only plot numeric metrics
            try:
                float_value = float(value)
                if 'latency' in metric_name.lower():
                    metrics_to_plot[f'{metric_name} (ms)'] = float_value
                elif 'energy' in metric_name.lower():
                    metrics_to_plot[f'{metric_name} (Wh)'] = float_value
                elif 'soc' in metric_name.lower():
                    metrics_to_plot[f'{metric_name} (%)'] = float_value
            except (ValueError, TypeError):
                continue
        
        if metrics_to_plot:
            ax4.bar(range(len(metrics_to_plot)), list(metrics_to_plot.values()), 
                   color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'][:len(metrics_to_plot)])
            ax4.set_xticks(range(len(metrics_to_plot)))
            ax4.set_xticklabels(list(metrics_to_plot.keys()), rotation=45, ha='right')
            ax4.set_ylabel('Value')
            ax4.set_title('Key Performance Metrics')
            ax4.grid(True, alpha=0.3)
        else:
            ax4.text(0.5, 0.5, 'No numeric summary metrics', transform=ax4.transAxes, ha='center', va='center')
            ax4.set_title('Key Performance Metrics (No Data)')
    else:
        ax4.text(0.5, 0.5, 'No summary data', transform=ax4.transAxes, ha='center', va='center')
        ax4.set_title('Key Performance Metrics (No Data)')
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Performance summary plot saved to: {save_path}")


def generate_all_plots(results_dir, per_task_file, summary_file):
    """
    Generate all visualization plots for the given results.
    
    Args:
        results_dir: Directory containing the results
        per_task_file: Path to per-task CSV file
        summary_file: Path to summary CSV file
    """
    # Load data
    try:
        per_task_df = pd.read_csv(per_task_file)
        summary_df = pd.read_csv(summary_file)
        print(f"Loaded {len(per_task_df)} task records from {per_task_file}")
        print(f"Loaded {len(summary_df)} summary metrics from {summary_file}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return False
    
    # Create figures directory
    figures_dir = results_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    print(f"Saving plots to: {figures_dir}")
    
    # Generate all plots
    plot_functions = [
        (plot_latency_distribution, "latency_distribution.png"),
        (plot_soc_curve, "soc_curve.png"),
        (plot_energy_boxplot, "energy_boxplot.png"),
        (plot_distribution_pies, "distribution_pies.png"),
        (plot_task_timeline, "task_timeline.png"),
        (lambda df, path: plot_performance_summary(df, summary_df, path), "performance_summary.png")
    ]
    
    successful_plots = 0
    for plot_func, filename in plot_functions:
        try:
            plot_func(per_task_df, figures_dir / filename)
            successful_plots += 1
        except Exception as e:
            print(f"Error generating {filename}: {e}")
    
    print(f"\\nSuccessfully generated {successful_plots}/{len(plot_functions)} plots")
    return successful_plots >= 3  # Success if at least 3 plots generated


def main():
    """Main entry point for the plotting script."""
    parser = argparse.ArgumentParser(description='Generate visualization plots for battery offloading simulation results')
    parser.add_argument('--results-dir', required=True, help='Directory containing simulation results')
    parser.add_argument('--auto-find', action='store_true', help='Automatically find latest results in the directory')
    
    args = parser.parse_args()
    
    # Setup matplotlib
    setup_matplotlib()
    
    # Find results
    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"Error: Results directory '{results_dir}' does not exist")
        return 1
    
    if args.auto_find:
        result = find_latest_results(results_dir)
    else:
        # Look directly in the specified directory
        per_task_file = results_dir / "per_task_results.csv"
        summary_file = results_dir / "summary_statistics.csv"
        if per_task_file.exists() and summary_file.exists():
            result = (results_dir, per_task_file, summary_file)
        else:
            result = find_latest_results(results_dir)
    
    if result is None:
        print(f"Error: Could not find simulation results in '{results_dir}'")
        print("Expected files: per_task_results.csv, summary_statistics.csv")
        return 1
    
    results_dir, per_task_file, summary_file = result
    print(f"Found results in: {results_dir}")
    
    # Generate plots
    success = generate_all_plots(results_dir, per_task_file, summary_file)
    
    if success:
        print("\\nVisualization complete! Check the 'figures' directory for PNG files.")
        return 0
    else:
        print("\\nSome plots failed to generate. Check error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())