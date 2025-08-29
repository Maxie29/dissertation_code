# Battery Offloading Research Project

A Python simulation framework for studying task offloading strategies in battery-constrained mobile computing environments.

## Project Overview

This project simulates a mobile device that can execute tasks locally or offload them to edge/cloud computing resources based on battery state and task characteristics.

## Task Dispatch Rules (Hard Requirements)

The system follows strict task dispatch rules:

1. **Special Tasks**: NAV and SLAM tasks **always execute locally** regardless of battery level
2. **Non-Special Tasks**: 
   - If SoC ≤ 30% → **Execute on Cloud**
   - If SoC > 30% → Choose between Local and Edge based on task's `edge_affinity` field:
     - `edge_affinity: true` → **Execute on Edge**
     - `edge_affinity: false` → **Execute on Local**
3. **No Migration**: Task execution location is decided at dispatch time and cannot change during execution
4. **No Additional Logic**: No availability, connection stability, or other unapproved decision factors

## Installation

### Prerequisites
- Python 3.11

### Setup Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

### 1. Verify Installation
```bash
pytest -q
```

### 2. Load Baseline Configuration
```python
from src.battery_offloading.config import Config

# Load baseline configuration
config = Config.from_yaml('configs/baseline.yaml')
print(f"Battery capacity: {config.battery.capacity_mah}mAh")
print(f"Initial SoC: {config.battery.initial_soc}%")
print(f"SoC threshold: {config.simulation.soc_threshold}%")
```

### 3. Run a Baseline Experiment
```python
# TODO: Add simulation runner example once implemented
print("Simulation framework ready!")
```

## Project Structure

```
battery_offloading/
├── src/battery_offloading/          # Main package
│   ├── __init__.py                  # Package initialization
│   ├── enums.py                     # TaskType and Site enums
│   ├── config.py                    # Configuration management
│   └── utils.py                     # Utility functions
├── configs/                         # Configuration files
│   └── baseline.yaml               # Baseline experiment configuration
├── tests/                          # Test suite
│   └── test_sanity.py              # Smoke tests
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Configuration

The project uses YAML configuration files with Pydantic validation. See `configs/baseline.yaml` for an example configuration with:

- Battery specifications (capacity, initial SoC)
- Service processing rates (local, edge, cloud)
- Network parameters (latency, bandwidth)
- Task generation parameters
- Simulation thresholds and ratios

## Testing

Run tests with:
```bash
pytest -q                    # Quick test output
pytest -v                    # Verbose test output
pytest tests/test_sanity.py  # Run specific test file
```

## Dependencies

- **simpy**: Discrete event simulation
- **numpy**: Numerical computing
- **pandas**: Data manipulation and analysis
- **pyyaml**: YAML configuration parsing
- **typer**: Command-line interface
- **rich**: Rich terminal output
- **matplotlib**: Plotting and visualization
- **pytest**: Testing framework
- **pydantic**: Data validation and settings management