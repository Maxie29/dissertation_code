#!/usr/bin/env python3
"""
Low Battery Threshold Validation Analysis

Analyzes experimental results to validate the 30% SoC threshold rule:
- SoC > 30%: GENERIC tasks should use LOCAL/EDGE based on edge_affinity
- SoC ≤ 30%: GENERIC tasks should MUST use CLOUD
- NAV/SLAM tasks should ALWAYS use LOCAL regardless of SoC
"""
import pandas as pd
import os
import glob
import json

def analyze_threshold_compliance(df, initial_soc, label):
    """Analyze compliance with 30% SoC threshold rule"""
    
    print(f"\n📊 ANALYSIS: {label} (Initial SoC: {initial_soc:.1f}%)")
    print("=" * 60)
    
    # Task type distribution
    task_counts = df['task_type'].value_counts()
    print(f"Task Distribution:")
    for task_type, count in task_counts.items():
        print(f"  {task_type}: {count}")
    
    # Execution site distribution  
    site_counts = df['execution_site'].value_counts()
    print(f"\nExecution Site Distribution:")
    for site, count in site_counts.items():
        print(f"  {site.upper()}: {count}")
    
    # Critical rule validation
    print(f"\n🔍 THRESHOLD RULE VALIDATION:")
    
    # Check NAV/SLAM tasks (should always be LOCAL)
    nav_slam_tasks = df[df['task_type'].isin(['NAV', 'SLAM'])]
    if len(nav_slam_tasks) > 0:
        nav_slam_local = nav_slam_tasks[nav_slam_tasks['execution_site'] == 'local']
        nav_slam_compliance = len(nav_slam_local) / len(nav_slam_tasks) * 100
        print(f"  NAV/SLAM LOCAL compliance: {nav_slam_compliance:.1f}% ({len(nav_slam_local)}/{len(nav_slam_tasks)})")
        
        if nav_slam_compliance == 100.0:
            print(f"  ✅ PASS: All NAV/SLAM tasks executed locally")
        else:
            non_local = nav_slam_tasks[nav_slam_tasks['execution_site'] != 'local']
            print(f"  ❌ FAIL: {len(non_local)} NAV/SLAM tasks executed remotely:")
            for _, task in non_local.iterrows():
                print(f"    Task {task['task_id']}: {task['task_type']} -> {task['execution_site'].upper()}")
    
    # Check GENERIC tasks based on SoC threshold
    generic_tasks = df[df['task_type'] == 'GENERIC']
    if len(generic_tasks) > 0:
        print(f"  GENERIC task analysis ({len(generic_tasks)} tasks):")
        
        if initial_soc > 30.0:
            # Above threshold: should use LOCAL/EDGE, no CLOUD
            cloud_generic = generic_tasks[generic_tasks['execution_site'] == 'cloud']
            if len(cloud_generic) == 0:
                print(f"    ✅ PASS: No GENERIC tasks used CLOUD (SoC > 30%)")
            else:
                print(f"    ❌ FAIL: {len(cloud_generic)} GENERIC tasks used CLOUD despite SoC > 30%")
                
            # Check LOCAL/EDGE distribution
            local_generic = len(generic_tasks[generic_tasks['execution_site'] == 'local'])
            edge_generic = len(generic_tasks[generic_tasks['execution_site'] == 'edge'])
            print(f"    LOCAL: {local_generic}, EDGE: {edge_generic}")
            
        else:  # SoC <= 30.0
            # At or below threshold: should use CLOUD only
            cloud_generic = generic_tasks[generic_tasks['execution_site'] == 'cloud']
            non_cloud_generic = generic_tasks[generic_tasks['execution_site'] != 'cloud']
            
            cloud_compliance = len(cloud_generic) / len(generic_tasks) * 100
            print(f"    CLOUD compliance: {cloud_compliance:.1f}% ({len(cloud_generic)}/{len(generic_tasks)})")
            
            if cloud_compliance == 100.0:
                print(f"    ✅ PASS: All GENERIC tasks used CLOUD (SoC ≤ 30%)")
            else:
                print(f"    ❌ FAIL: {len(non_cloud_generic)} GENERIC tasks violated threshold rule:")
                for site in non_cloud_generic['execution_site'].value_counts().items():
                    print(f"      {site[1]} tasks used {site[0].upper()}")
    
    # Battery level analysis
    print(f"\n🔋 BATTERY ANALYSIS:")
    print(f"  Initial SoC: {df['soc_before'].iloc[0]:.1f}%")
    print(f"  Final SoC: {df['soc_after'].iloc[-1]:.1f}%")
    print(f"  SoC decrease: {df['soc_before'].iloc[0] - df['soc_after'].iloc[-1]:.2f}%")
    print(f"  Minimum SoC reached: {df['soc_after'].min():.1f}%")
    
    # Check if threshold was crossed during simulation
    crossed_threshold = False
    for _, task in df.iterrows():
        if task['soc_before'] > 30.0 and task['soc_after'] <= 30.0:
            crossed_threshold = True
            print(f"  ⚠️  THRESHOLD CROSSED during task {task['task_id']} (SoC: {task['soc_before']:.1f}% → {task['soc_after']:.1f}%)")
            break
    
    if not crossed_threshold and df['soc_after'].min() <= 30.0:
        print(f"  ℹ️  Battery reached ≤30% but no threshold crossing detected in individual tasks")
    
    return {
        'label': label,
        'initial_soc': initial_soc,
        'final_soc': df['soc_after'].iloc[-1],
        'nav_slam_compliance': nav_slam_compliance if len(nav_slam_tasks) > 0 else None,
        'generic_cloud_compliance': cloud_compliance if len(generic_tasks) > 0 and initial_soc <= 30.0 else None,
        'threshold_crossed': crossed_threshold,
        'min_soc': df['soc_after'].min()
    }

def main():
    print("LOW BATTERY THRESHOLD VALIDATION ANALYSIS")
    print("=" * 80)
    print("Validating 30% SoC threshold rule compliance")
    print("")
    
    # Find validation results
    validation_dirs = []
    
    # Check extracted validation results
    if os.path.exists('validation_results'):
        validation_dirs.append('validation_results')
    
    # Check recent sweep results
    sweep_dirs = glob.glob('results/sweep_*')
    if sweep_dirs:
        latest_sweep = max(sweep_dirs, key=os.path.getmtime)
        validation_dirs.append(latest_sweep)
    
    # Check individual test results from recent runs
    recent_results = glob.glob('results/20*')
    recent_results = [d for d in recent_results if os.path.getmtime(d) > (pd.Timestamp.now().timestamp() - 3600)]  # Last hour
    validation_dirs.extend(recent_results)
    
    if not validation_dirs:
        print("❌ No validation results found!")
        print("Please run the low battery validation first:")
        print("   .\\scripts\\run_low_battery_test.ps1")
        return
    
    print(f"📁 Found {len(validation_dirs)} result directories to analyze")
    
    all_results = []
    
    # Analyze each result directory
    for result_dir in validation_dirs:
        csv_files = glob.glob(os.path.join(result_dir, '**/per_task_results.csv'), recursive=True)
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                if len(df) == 0:
                    continue
                    
                initial_soc = df['soc_before'].iloc[0]
                
                # Extract label from path
                path_parts = csv_file.replace('\\', '/').split('/')
                label = 'unknown'
                for part in path_parts:
                    if 'pct' in part or 'threshold' in part:
                        label = part
                        break
                if label == 'unknown':
                    label = f"soc_{initial_soc:.0f}pct"
                
                result = analyze_threshold_compliance(df, initial_soc, label)
                all_results.append(result)
                
            except Exception as e:
                print(f"⚠️  Error analyzing {csv_file}: {e}")
    
    # Summary analysis
    if all_results:
        print(f"\n📈 VALIDATION SUMMARY")
        print("=" * 80)
        
        # Sort results by initial SoC
        all_results.sort(key=lambda x: x['initial_soc'], reverse=True)
        
        print(f"{'Label':<25} {'Init SoC':<10} {'Final SoC':<11} {'NAV/SLAM':<10} {'Generic':<10} {'Threshold'}")
        print(f"{'='*25} {'='*10} {'='*11} {'='*10} {'='*10} {'='*9}")
        
        for result in all_results:
            nav_slam_status = f"{result['nav_slam_compliance']:.0f}%" if result['nav_slam_compliance'] is not None else "N/A"
            generic_status = f"{result['generic_cloud_compliance']:.0f}%" if result['generic_cloud_compliance'] is not None else "N/A"
            threshold_status = "CROSSED" if result['threshold_crossed'] else "NO"
            
            print(f"{result['label']:<25} {result['initial_soc']:>6.1f}% {result['final_soc']:>7.1f}% {nav_slam_status:>10} {generic_status:>10} {threshold_status:>9}")
        
        # Compliance summary
        print(f"\n🎯 COMPLIANCE SUMMARY:")
        nav_slam_passes = sum(1 for r in all_results if r['nav_slam_compliance'] == 100.0)
        nav_slam_total = sum(1 for r in all_results if r['nav_slam_compliance'] is not None)
        
        if nav_slam_total > 0:
            print(f"  NAV/SLAM always LOCAL: {nav_slam_passes}/{nav_slam_total} experiments passed")
        
        generic_passes = sum(1 for r in all_results if r['generic_cloud_compliance'] == 100.0)
        generic_total = sum(1 for r in all_results if r['generic_cloud_compliance'] is not None)
        
        if generic_total > 0:
            print(f"  GENERIC threshold rule: {generic_passes}/{generic_total} low-SoC experiments passed")
        
        threshold_crossings = sum(1 for r in all_results if r['threshold_crossed'])
        print(f"  Threshold crossings detected: {threshold_crossings}")
        
        # Overall validation result
        overall_pass = (nav_slam_passes == nav_slam_total) and (generic_passes == generic_total)
        if overall_pass:
            print(f"\n✅ OVERALL VALIDATION: PASS")
            print(f"   30% SoC threshold rule is correctly implemented!")
        else:
            print(f"\n❌ OVERALL VALIDATION: FAIL")
            print(f"   30% SoC threshold rule has compliance issues!")
        
    else:
        print("❌ No valid results found for analysis")

if __name__ == "__main__":
    main()