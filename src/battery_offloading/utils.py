"""
Utility functions for the battery offloading simulation.

This module provides common functionality used throughout the simulation
including timestamp handling, file I/O operations, data formatting,
and path management utilities.
"""

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import pandas as pd


def get_timestamp() -> str:
    """
    Get current timestamp in ISO format.
    
    Returns:
        Current timestamp as ISO 8601 formatted string
        
    Examples:
    >>> timestamp = get_timestamp()
    >>> isinstance(timestamp, str)
    True
    >>> 'T' in timestamp  # ISO format includes 'T' separator
    True
    """
    return datetime.now(timezone.utc).isoformat()


def get_timestamp_for_filename() -> str:
    """
    Get timestamp suitable for use in filenames.
    
    Returns:
        Timestamp string safe for use in filenames (no colons or spaces)
        
    Examples:
    >>> filename_timestamp = get_timestamp_for_filename()
    >>> ':' not in filename_timestamp
    True
    >>> ' ' not in filename_timestamp
    True
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if necessary.
    
    Args:
        path: Directory path to create
        
    Returns:
        Path object for the created/existing directory
        
    Examples:
    >>> test_dir = ensure_directory('test_output')
    >>> test_dir.exists()
    True
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def write_csv_row(file_path: Union[str, Path], row_data: Dict[str, Any], 
                  headers: Optional[List[str]] = None) -> None:
    """
    Write a single row to CSV file, creating file if necessary.
    
    Args:
        file_path: Path to the CSV file
        row_data: Dictionary containing the row data
        headers: Optional list of column headers (only used when creating new file)
        
    Examples:
    >>> write_csv_row('test.csv', {'time': 1.0, 'soc': 85.5}, ['time', 'soc'])
    >>> Path('test.csv').exists()
    True
    """
    file_path = Path(file_path)
    file_exists = file_path.exists()
    
    # Ensure parent directory exists
    ensure_directory(file_path.parent)
    
    with open(file_path, 'a', newline='', encoding='utf-8') as f:
        if not file_exists and headers:
            # Write headers for new file
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        
        # Write the data row
        if file_exists or headers:
            fieldnames = headers if headers else list(row_data.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(row_data)


def append_csv_rows(file_path: Union[str, Path], rows_data: List[Dict[str, Any]], 
                    headers: Optional[List[str]] = None) -> None:
    """
    Append multiple rows to CSV file efficiently.
    
    Args:
        file_path: Path to the CSV file
        rows_data: List of dictionaries containing row data
        headers: Optional list of column headers (only used when creating new file)
        
    Examples:
    >>> data = [{'time': 1.0, 'soc': 85.5}, {'time': 2.0, 'soc': 84.2}]
    >>> append_csv_rows('test_batch.csv', data, ['time', 'soc'])
    >>> Path('test_batch.csv').exists()
    True
    """
    if not rows_data:
        return
        
    file_path = Path(file_path)
    file_exists = file_path.exists()
    
    # Ensure parent directory exists
    ensure_directory(file_path.parent)
    
    with open(file_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = headers if headers else list(rows_data[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists and headers:
            writer.writeheader()
        
        writer.writerows(rows_data)


def load_csv_as_dataframe(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Load CSV file as pandas DataFrame.
    
    Args:
        file_path: Path to the CSV file to load
        
    Returns:
        DataFrame containing the CSV data
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        
    Examples:
    >>> # Assuming test.csv exists with time,soc columns
    >>> df = load_csv_as_dataframe('test.csv')
    >>> isinstance(df, pd.DataFrame)
    True
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    return pd.read_csv(file_path)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
        
    Examples:
    >>> format_duration(125.5)
    '2m 5.5s'
    >>> format_duration(3661.2)
    '1h 1m 1.2s'
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.1f}s"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"


def format_bytes(bytes_value: Union[int, float]) -> str:
    """
    Format byte count to human-readable string with appropriate units.
    
    Args:
        bytes_value: Size in bytes
        
    Returns:
        Formatted size string with units
        
    Examples:
    >>> format_bytes(1024)
    '1.0 KB'
    >>> format_bytes(1536000)
    '1.5 MB'
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(bytes_value)
    unit_index = 0
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Perform safe division with default value for division by zero.
    
    Args:
        numerator: Numerator value
        denominator: Denominator value  
        default: Default value to return if denominator is zero
        
    Returns:
        Division result or default value
        
    Examples:
    >>> safe_divide(10, 2)
    5.0
    >>> safe_divide(10, 0, -1)
    -1
    """
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp value between minimum and maximum bounds.
    
    Args:
        value: Value to clamp
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Clamped value within bounds
        
    Examples:
    >>> clamp(5.0, 0.0, 10.0)
    5.0
    >>> clamp(-5.0, 0.0, 10.0)
    0.0
    >>> clamp(15.0, 0.0, 10.0)
    10.0
    """
    return max(min_value, min(value, max_value))