"""
Command Line Interface for Battery Offloading Simulation.

This module provides a Typer-based CLI for running battery offloading
simulations with configurable parameters and rich output formatting.
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from .config import Config
from .task import TaskGenerator
from .sim.runner import Runner
from .sim.sweep import SweepConfig, SweepRunner, is_sweep_config


app = typer.Typer(
    name="battery-offloading",
    help="Battery-aware task offloading simulation framework",
    no_args_is_help=True
)
console = Console()


@app.command()
def run(
    config: str = typer.Option(
        "configs/baseline.yaml",
        "--config", "-c",
        help="Path to YAML configuration file"
    ),
    num_tasks: Optional[int] = typer.Option(
        None,
        "--num-tasks", "-n",
        help="Number of tasks to simulate (overrides config)",
        min=1
    ),
    seed: Optional[int] = typer.Option(
        None,
        "--seed", "-s",
        help="Random seed for reproducibility"
    ),
    initial_soc: Optional[float] = typer.Option(
        None,
        "--initial-soc",
        help="Initial battery state of charge (0-100%)",
        min=0.0,
        max=100.0
    ),
    battery_capacity: Optional[float] = typer.Option(
        None,
        "--battery-capacity",
        help="Battery capacity in Wh",
        min=0.1
    ),
    results_dir: str = typer.Option(
        "results",
        "--results-dir", "-r",
        help="Directory to save results"
    ),
    no_save: bool = typer.Option(
        False,
        "--no-save",
        help="Don't save results to CSV files"
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Minimal output, only show final results"
    )
):
    """
    Run battery offloading simulation.
    
    This command loads a YAML configuration, generates tasks, runs the
    simulation with policy-based dispatch, and saves comprehensive
    results including per-task records and summary statistics.
    
    Examples:
        # Basic simulation with default config
        python -m battery_offloading.cli run
        
        # Custom configuration and parameters
        python -m battery_offloading.cli run \\
            --config configs/custom.yaml \\
            --num-tasks 500 \\
            --seed 42 \\
            --initial-soc 85.0
        
        # Quick run without saving results
        python -m battery_offloading.cli run \\
            --num-tasks 50 \\
            --no-save \\
            --quiet
    """
    try:
        # Display header
        if not quiet:
            console.print(Panel(
                "[bold blue]Battery Offloading Simulation Framework[/bold blue]",
                subtitle="Policy-based Task Dispatch with Energy Awareness"
            ))
        
        # Load and validate configuration
        if not quiet:
            console.print(f"[yellow]Loading configuration from {config}...[/yellow]")
        
        if not Path(config).exists():
            console.print(f"[red]Error: Configuration file '{config}' not found[/red]")
            raise typer.Exit(1)
        
        # Check if this is a sweep configuration
        if is_sweep_config(config):
            # Handle sweep configuration
            _run_sweep(config, num_tasks, seed, initial_soc, battery_capacity, results_dir, quiet)
            return
        
        try:
            sim_config = Config.from_yaml(config)
        except Exception as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
            raise typer.Exit(1)
        
        # Override configuration parameters if provided
        task_count = num_tasks if num_tasks is not None else 200  # Default to 200 tasks
        task_seed = seed if seed is not None else 42
        soc = initial_soc if initial_soc is not None else 80.0
        capacity = battery_capacity if battery_capacity is not None else 100.0
        
        if not quiet:
            _display_configuration(sim_config, task_count, task_seed, soc, capacity)
        
        # Create task generator
        if not quiet:
            console.print("\n[yellow]Initializing task generator...[/yellow]")
        
        task_gen = TaskGenerator(
            arrival_rate=sim_config.task_generation.arrival_rate_per_sec,
            nav_ratio=sim_config.task_generation.nav_ratio,
            slam_ratio=sim_config.task_generation.slam_ratio,
            edge_affinity_ratio=sim_config.task_generation.edge_affinity_ratio,
            avg_size_bytes=int(sim_config.task_generation.avg_data_size_mb * 1024 * 1024),
            avg_compute_demand=sim_config.task_generation.avg_operations,
            seed=task_seed
        )
        
        # Create and configure runner
        if not quiet:
            console.print("[yellow]Initializing simulation runner...[/yellow]")
        
        runner = Runner(
            config=sim_config,
            task_generator=task_gen,
            initial_soc=soc,
            battery_capacity_wh=capacity,
            results_dir=results_dir
        )
        
        # Run simulation with progress tracking
        if not quiet:
            console.print(f"\n[green]Starting simulation with {task_count} tasks...[/green]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Running simulation...", total=None)
                records, summary = runner.run(
                    num_tasks=task_count, 
                    save_results=not no_save
                )
                progress.update(task, description="Simulation completed")
        else:
            records, summary = runner.run(
                num_tasks=task_count, 
                save_results=not no_save
            )
        
        # Display results
        _display_results(summary, records, not no_save, results_dir)
        
        # Validate acceptance criteria
        validation = runner.metrics.validate_hard_rules()
        _display_validation(validation)
        
        console.print(f"\n[green]Simulation completed successfully![/green]")
        
        if not validation['all_rules_valid']:
            console.print("[red]Warning: Some hard rules failed validation![/red]")
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Simulation interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _run_sweep(
    config_path: str,
    num_tasks: Optional[int],
    seed: Optional[int],
    initial_soc: Optional[float],
    battery_capacity: Optional[float],
    results_dir: str,
    quiet: bool
):
    """Run parameter sweep using sweep configuration."""
    try:
        # Load sweep configuration
        sweep_config = SweepConfig(config_path)
        sweep_info = sweep_config.get_sweep_info()
        
        if not quiet:
            console.print(Panel(
                f"[bold magenta]Parameter Sweep: {sweep_info.get('name', 'Unnamed')}[/bold magenta]",
                subtitle=f"Description: {sweep_info.get('description', 'No description')}"
            ))
        
        # Set parameters with CLI overrides or defaults
        task_count = num_tasks if num_tasks is not None else 200
        seed_base = seed if seed is not None else 42
        # For sweeps, only use CLI values if explicitly provided, otherwise let config values take precedence
        soc = initial_soc if initial_soc is not None else None
        capacity = battery_capacity if battery_capacity is not None else None
        
        # Create and run sweep
        if not quiet:
            console.print(f"[yellow]Starting parameter sweep with {task_count} tasks per run...[/yellow]")
        
        sweep_runner = SweepRunner(sweep_config)
        
        # Run the sweep with progress indication
        if not quiet:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task("Running parameter sweep...", total=None)
                sweep_results = sweep_runner.run_sweep(
                    num_tasks=task_count,
                    initial_soc=soc,
                    battery_capacity_wh=capacity,
                    results_dir=results_dir,
                    seed_base=seed_base
                )
                progress.update(task, description="Parameter sweep completed")
        else:
            sweep_results = sweep_runner.run_sweep(
                num_tasks=task_count,
                initial_soc=soc,
                battery_capacity_wh=capacity,
                results_dir=results_dir,
                seed_base=seed_base
            )
        
        # Display sweep summary
        _display_sweep_results(sweep_results, sweep_info)
        
        # Check for any validation failures
        failed_runs = [r for r in sweep_results if not r.get('validation', {}).get('all_rules_valid', True)]
        if failed_runs and not quiet:
            console.print(f"[red]Warning: {len(failed_runs)} runs had validation failures![/red]")
        
        console.print(f"\n[green]Parameter sweep completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Error running parameter sweep: {e}[/red]")
        raise typer.Exit(1)


def _display_sweep_results(sweep_results: list, sweep_info: dict):
    """Display parameter sweep results summary."""
    console.print(f"\n[bold green]Parameter Sweep Results[/bold green]")
    
    # Summary statistics
    successful_runs = [r for r in sweep_results if 'error' not in r]
    failed_runs = [r for r in sweep_results if 'error' in r]
    
    summary_table = Table(title="Sweep Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white", justify="right")
    
    summary_table.add_row("Total runs", f"{len(sweep_results)}")
    summary_table.add_row("Successful runs", f"{len(successful_runs)}")
    summary_table.add_row("Failed runs", f"{len(failed_runs)}")
    
    if successful_runs:
        # Calculate aggregate metrics
        all_latencies = [r['metrics']['latency_mean_ms'] for r in successful_runs]
        all_energies = [r['metrics']['total_energy_wh'] for r in successful_runs]
        all_soc_drops = [r['metrics']['soc_drop'] for r in successful_runs]
        
        summary_table.add_row("", "")
        summary_table.add_row("Latency range", f"{min(all_latencies):.1f} - {max(all_latencies):.1f}ms")
        summary_table.add_row("Energy range", f"{min(all_energies):.3f} - {max(all_energies):.3f}Wh")
        summary_table.add_row("SoC drop range", f"{min(all_soc_drops):.2f} - {max(all_soc_drops):.2f}%")
    
    console.print(summary_table)
    
    # Detailed results table for successful runs
    if successful_runs:
        results_table = Table(title="Run Details", show_lines=True)
        results_table.add_column("Run", style="cyan", justify="center")
        results_table.add_column("Label", style="yellow")
        results_table.add_column("Latency\n(ms)", justify="right")
        results_table.add_column("Energy\n(Wh)", justify="right")
        results_table.add_column("SoC Drop\n(%)", justify="right")
        results_table.add_column("Local/Edge/Cloud\n(%)", justify="center")
        results_table.add_column("Valid", justify="center")
        
        for result in successful_runs[:10]:  # Show first 10 runs
            metrics = result['metrics']
            validation = result.get('validation', {})
            
            distribution = f"{metrics['local_ratio']:.0%}/{metrics['edge_ratio']:.0%}/{metrics['cloud_ratio']:.0%}"
            valid_status = "PASS" if validation.get('all_rules_valid', False) else "FAIL"
            valid_style = "green" if validation.get('all_rules_valid', False) else "red"
            
            results_table.add_row(
                str(result['run_id']),
                result['parameter_label'][:20],  # Truncate long labels
                f"{metrics['latency_mean_ms']:.1f}",
                f"{metrics['total_energy_wh']:.3f}",
                f"{metrics['soc_drop']:.2f}",
                distribution,
                f"[{valid_style}]{valid_status}[/{valid_style}]"
            )
        
        console.print(results_table)
        
        if len(successful_runs) > 10:
            console.print(f"[dim]... and {len(successful_runs) - 10} more runs[/dim]")
    
    # Show failed runs if any
    if failed_runs:
        console.print(f"\n[red]Failed Runs:[/red]")
        for result in failed_runs:
            console.print(f"  Run {result['run_id']} ({result['parameter_label']}): {result['error']}")


def _display_configuration(config, num_tasks: int, seed: int, soc: float, capacity: float):
    """Display configuration summary."""
    table = Table(title="Simulation Configuration", show_header=False)
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Tasks to simulate", f"{num_tasks:,}")
    table.add_row("Random seed", str(seed))
    table.add_row("Initial battery SoC", f"{soc:.1f}%")
    table.add_row("Battery capacity", f"{capacity:.1f} Wh")
    table.add_row("", "")
    table.add_row("Local processing rate", f"{config.local_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    table.add_row("Edge processing rate", f"{config.edge_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    table.add_row("Cloud processing rate", f"{config.cloud_service.processing_rate_ops_per_sec/1e6:.1f}M ops/s")
    table.add_row("", "")
    table.add_row("Task arrival rate", f"{config.task_generation.arrival_rate_per_sec:.2f} tasks/s")
    table.add_row("NAV task ratio", f"{config.task_generation.nav_ratio:.1%}")
    table.add_row("SLAM task ratio", f"{config.task_generation.slam_ratio:.1%}")
    table.add_row("Edge affinity ratio", f"{config.task_generation.edge_affinity_ratio:.1%}")
    
    console.print(table)


def _display_results(summary: dict, records: list, saved: bool, results_dir: str):
    """Display simulation results."""
    console.print(f"\n[bold green]Simulation Results[/bold green]")
    
    # Main metrics table
    metrics_table = Table(title="Key Metrics")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="white", justify="right")
    
    metrics_table.add_row("Total tasks processed", f"{summary['total_tasks']:,}")
    metrics_table.add_row("Simulation duration", f"{summary['simulation_duration_s']:.1f}s")
    metrics_table.add_row("", "")
    metrics_table.add_row("Mean latency", f"{summary['latency_mean_ms']:.1f}ms")
    metrics_table.add_row("Median latency (P50)", f"{summary['latency_p50_ms']:.1f}ms")
    metrics_table.add_row("P95 latency", f"{summary['latency_p95_ms']:.1f}ms")
    metrics_table.add_row("P99 latency", f"{summary['latency_p99_ms']:.1f}ms")
    metrics_table.add_row("", "")
    metrics_table.add_row("Total energy consumed", f"{summary['total_energy_wh']:.3f} Wh")
    metrics_table.add_row("Average per task", f"{summary['energy_per_task_mean_wh']:.4f} Wh")
    metrics_table.add_row("", "")
    metrics_table.add_row("Initial battery SoC", f"{summary['initial_soc']:.1f}%")
    metrics_table.add_row("Final battery SoC", f"{summary['final_soc']:.1f}%")
    metrics_table.add_row("SoC decrease", f"{summary['soc_drop']:.2f}%")
    
    console.print(metrics_table)
    
    # Site distribution table
    site_table = Table(title="Task Distribution")
    site_table.add_column("Execution Site", style="cyan")
    site_table.add_column("Count", justify="right")
    site_table.add_column("Percentage", justify="right")
    
    site_table.add_row("Local", f"{summary['local_count']:,}", f"{summary['local_ratio']:.1%}")
    site_table.add_row("Edge", f"{summary['edge_count']:,}", f"{summary['edge_ratio']:.1%}")
    site_table.add_row("Cloud", f"{summary['cloud_count']:,}", f"{summary['cloud_ratio']:.1%}")
    
    console.print(site_table)
    
    # Task type distribution
    type_table = Table(title="Task Types")
    type_table.add_column("Task Type", style="cyan")
    type_table.add_column("Count", justify="right")
    type_table.add_column("Percentage", justify="right")
    
    type_table.add_row("NAV", f"{summary['nav_count']:,}", f"{summary['nav_ratio']:.1%}")
    type_table.add_row("SLAM", f"{summary['slam_count']:,}", f"{summary['slam_ratio']:.1%}")
    type_table.add_row("GENERIC", f"{summary['generic_count']:,}", f"{summary['generic_ratio']:.1%}")
    
    console.print(type_table)
    
    # Deadline compliance if applicable
    if summary['tasks_with_deadlines'] > 0:
        console.print(f"\n[yellow]Deadline Compliance:[/yellow]")
        console.print(f"  Tasks with deadlines: {summary['tasks_with_deadlines']:,}")
        console.print(f"  Deadlines missed: {summary['deadlines_missed']:,}")
        console.print(f"  Miss rate: {summary['deadline_miss_rate']:.1%}")
    
    # File output information
    if saved:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        console.print(f"\n[blue]Results saved to:[/blue]")
        console.print(f"  Directory: {results_dir}/{timestamp}/")
        console.print(f"  Per-task data: per_task_results.csv")
        console.print(f"  Summary stats: summary_statistics.csv")


def _display_validation(validation: dict):
    """Display rule validation results."""
    console.print(f"\n[bold yellow]Hard Rules Validation[/bold yellow]")
    
    validation_table = Table()
    validation_table.add_column("Rule", style="white")
    validation_table.add_column("Status", justify="center")
    
    rules = [
        ("NAV/SLAM always execute locally", validation['nav_slam_always_local']),
        ("SoC curve is monotonic (non-increasing)", validation['soc_curve_monotonic']),
        ("Generic task rules consistent", validation['generic_rules_consistent'])
    ]
    
    for rule_name, passed in rules:
        status = Text("PASS", style="green") if passed else Text("FAIL", style="red")
        validation_table.add_row(rule_name, status)
    
    # Overall validation
    overall_status = Text("ALL VALID", style="bold green") if validation['all_rules_valid'] else Text("VIOLATIONS", style="bold red")
    validation_table.add_row("", "")
    validation_table.add_row("Overall validation", overall_status)
    
    console.print(validation_table)


@app.command()
def version():
    """Show version information."""
    from . import __version__, __author__
    
    console.print(Panel(
        f"[bold blue]Battery Offloading Simulation Framework[/bold blue]\n"
        f"Version: {__version__}\n"
        f"Author: {__author__}",
        title="Version Info"
    ))


@app.command()
def validate_config(
    config: str = typer.Argument(..., help="Path to YAML configuration file")
):
    """
    Validate a configuration file.
    
    This command loads and validates a YAML configuration file,
    reporting any errors or warnings.
    """
    try:
        console.print(f"[yellow]Validating configuration: {config}[/yellow]")
        
        if not Path(config).exists():
            console.print(f"[red]Error: Configuration file '{config}' not found[/red]")
            raise typer.Exit(1)
        
        sim_config = Config.from_yaml(config)
        
        console.print("[green]Configuration is valid![/green]")
        
        # Display configuration summary
        _display_configuration(sim_config, 200, 42, 80.0, 100.0)
        
    except Exception as e:
        console.print(f"[red]Configuration validation failed: {e}[/red]")
        raise typer.Exit(1)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()