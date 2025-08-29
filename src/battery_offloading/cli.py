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