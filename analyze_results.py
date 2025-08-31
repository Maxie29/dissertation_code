#!/usr/bin/env python3
"""
Quick analysis script for experimental results
"""
import pandas as pd
import os

def analyze_results():
    """Analyze the extracted experiment results"""
    
    print("=" * 60)
    print("BATTERY OFFLOADING EXPERIMENT ANALYSIS")
    print("=" * 60)
    
    # Check if extracted results exist
    if not os.path.exists('extracted_results'):
        print("❌ No extracted_results directory found.")
        print("Please extract your ZIP file first:")
        print("   Expand-Archive -Path baseline_results_*.zip -DestinationPath extracted_results")
        return
    
    # Analyze baseline results
    if os.path.exists('extracted_results/baseline/summary_statistics.csv'):
        print("\n📊 BASELINE EXPERIMENT SUMMARY")
        print("-" * 40)
        
        df_summary = pd.read_csv('extracted_results/baseline/summary_statistics.csv')
        print(df_summary.to_string(index=False))
        
        # Load per-task data for additional analysis
        if os.path.exists('extracted_results/baseline/per_task_results.csv'):
            df_tasks = pd.read_csv('extracted_results/baseline/per_task_results.csv')
            
            print(f"\n📋 TASK DETAILS (Total: {len(df_tasks)} tasks)")
            print("-" * 40)
            print(f"Task types distribution:")
            print(df_tasks['task_type'].value_counts())
            
            print(f"\nExecution site distribution:")
            print(df_tasks['execution_site'].value_counts())
            
            print(f"\nLatency statistics (ms):")
            print(f"  Mean: {df_tasks['latency_ms'].mean():.1f}")
            print(f"  Median: {df_tasks['latency_ms'].median():.1f}")
            print(f"  Min: {df_tasks['latency_ms'].min():.1f}")
            print(f"  Max: {df_tasks['latency_ms'].max():.1f}")
            
            print(f"\nEnergy statistics (Wh):")
            print(f"  Total consumed: {df_tasks['energy_wh_delta'].sum():.4f}")
            print(f"  Average per task: {df_tasks['energy_wh_delta'].mean():.6f}")
            
            print(f"\nBattery SoC range:")
            print(f"  Initial: {df_tasks['soc_before'].iloc[0]:.1f}%")
            print(f"  Final: {df_tasks['soc_after'].iloc[-1]:.1f}%")
            print(f"  Total decrease: {df_tasks['soc_before'].iloc[0] - df_tasks['soc_after'].iloc[-1]:.2f}%")
    
    # Analyze sweep results if available
    if os.path.exists('extracted_results/sweeps'):
        print(f"\n🔄 PARAMETER SWEEP RESULTS")
        print("-" * 40)
        
        if os.path.exists('extracted_results/sweeps/sweep_summary.csv'):
            df_sweep = pd.read_csv('extracted_results/sweeps/sweep_summary.csv')
            print(df_sweep.to_string(index=False))
        else:
            print("No sweep summary found.")
    
    print(f"\n✅ Analysis complete!")
    print(f"For detailed data, check the CSV files in extracted_results/")

if __name__ == "__main__":
    analyze_results()