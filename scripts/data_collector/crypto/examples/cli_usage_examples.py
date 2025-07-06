#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
CLI Usage Examples for Cryptocurrency Data Collection

This file demonstrates various ways to use the enhanced CLI for cryptocurrency
data collection, validation, and management.
"""

import subprocess
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from pathlib import Path

# Example CLI commands as strings for documentation and testing


def basic_collection_examples():
    """Basic data collection examples."""
    
    examples = [
        # Basic collection with default settings
        "python -m scripts.data_collector.crypto collect",
        
        # Collection with specific exchanges
        "python -m scripts.data_collector.crypto collect --exchanges binance okx",
        
        # Collection with specific symbols
        "python -m scripts.data_collector.crypto collect --symbols BTC/USDT ETH/USDT SOL/USDT",
        
        # Collection with specific timeframes
        "python -m scripts.data_collector.crypto collect --timeframes 1h 4h 1d",
        
        # Collection with date range
        "python -m scripts.data_collector.crypto collect --start-date 2024-01-01 --end-date 2024-01-31",
        
        # Collection with lookback period
        "python -m scripts.data_collector.crypto collect --lookback-days 30",
        
        # Collection with custom output directory
        "python -m scripts.data_collector.crypto collect --output-dir ./my_crypto_data",
        
        # Collection with performance tuning
        "python -m scripts.data_collector.crypto collect --max-workers 8",
        
        # Collection with extended features
        "python -m scripts.data_collector.crypto collect --enable-extended-fields --enable-risk-metrics",
        
        # Incremental collection
        "python -m scripts.data_collector.crypto collect --incremental",
        
        # Dry run to see what would be collected
        "python -m scripts.data_collector.crypto collect --dry-run --verbose",
    ]
    
    return examples


def template_examples():
    """Template management examples."""
    
    examples = [
        # List available templates
        "python -m scripts.data_collector.crypto templates list",
        
        # Get template information
        "python -m scripts.data_collector.crypto templates info default",
        "python -m scripts.data_collector.crypto templates info production",
        "python -m scripts.data_collector.crypto templates info high_frequency",
        
        # Compare templates
        "python -m scripts.data_collector.crypto templates compare default production",
        "python -m scripts.data_collector.crypto templates compare simple high_frequency",
        
        # Get template recommendations
        "python -m scripts.data_collector.crypto templates recommend --exchanges binance okx",
        "python -m scripts.data_collector.crypto templates recommend --timeframes 1m 5m --extended-fields",
        "python -m scripts.data_collector.crypto templates recommend --risk-metrics",
        
        # Use templates for collection
        "python -m scripts.data_collector.crypto collect --template production",
        "python -m scripts.data_collector.crypto collect --template high_frequency --max-workers 4",
        "python -m scripts.data_collector.crypto collect --template research --symbols BTC/USDT ETH/USDT",
    ]
    
    return examples


def configuration_examples():
    """Configuration management examples."""
    
    examples = [
        # Use custom configuration file
        "python -m scripts.data_collector.crypto collect --config my_config.yaml",
        "python -m scripts.data_collector.crypto collect --config config.json",
        
        # Validate configuration file
        "python -m scripts.data_collector.crypto config validate my_config.yaml",
        "python -m scripts.data_collector.crypto config validate config.json",
        
        # Generate configuration file from template
        "python -m scripts.data_collector.crypto config generate --template production --output production_config.yaml",
        "python -m scripts.data_collector.crypto config generate --template default --output config.json --format json",
        
        # Override configuration with CLI parameters
        "python -m scripts.data_collector.crypto collect --config base_config.yaml --exchanges binance --timeframes 1d",
        "python -m scripts.data_collector.crypto collect --template production --output-dir ./prod_data --max-workers 16",
    ]
    
    return examples


def validation_examples():
    """Data validation examples."""
    
    examples = [
        # Basic data validation
        "python -m scripts.data_collector.crypto validate --data-dir ./crypto_data",
        
        # Validate specific symbols
        "python -m scripts.data_collector.crypto validate --data-dir ./crypto_data --symbols BTC/USDT ETH/USDT",
        
        # Validate specific timeframes
        "python -m scripts.data_collector.crypto validate --data-dir ./crypto_data --timeframes 1h 1d",
        
        # Generate validation report
        "python -m scripts.data_collector.crypto validate --data-dir ./crypto_data --output-report validation_report.json",
        
        # Validate with custom configuration
        "python -m scripts.data_collector.crypto validate --data-dir ./crypto_data --config validation_config.yaml",
        
        # Attempt to fix validation issues
        "python -m scripts.data_collector.crypto validate --data-dir ./crypto_data --fix-issues",
    ]
    
    return examples


def universe_management_examples():
    """Universe management examples."""
    
    examples = [
        # Update investment universe
        "python -m scripts.data_collector.crypto universe update",
        
        # Update universe with custom configuration
        "python -m scripts.data_collector.crypto universe update --config universe_config.yaml",
        
        # Save universe to file
        "python -m scripts.data_collector.crypto universe update --output-file universe.json",
        "python -m scripts.data_collector.crypto universe update --output-file universe.csv",
        
        # List current universe
        "python -m scripts.data_collector.crypto universe list",
        "python -m scripts.data_collector.crypto universe list --format json",
        "python -m scripts.data_collector.crypto universe list --format csv",
        "python -m scripts.data_collector.crypto universe list --format table",
    ]
    
    return examples


def risk_calculation_examples():
    """Risk metrics calculation examples."""
    
    examples = [
        # Calculate all risk metrics
        "python -m scripts.data_collector.crypto risk calculate --data-dir ./crypto_data",
        
        # Calculate specific risk metrics
        "python -m scripts.data_collector.crypto risk calculate --data-dir ./crypto_data --metrics volatility var",
        "python -m scripts.data_collector.crypto risk calculate --data-dir ./crypto_data --metrics sharpe drawdown",
        
        # Calculate for specific symbols
        "python -m scripts.data_collector.crypto risk calculate --data-dir ./crypto_data --symbols BTC/USDT ETH/USDT",
        
        # Save to custom output directory
        "python -m scripts.data_collector.crypto risk calculate --data-dir ./crypto_data --output-dir ./risk_metrics",
        
        # Calculate with custom configuration
        "python -m scripts.data_collector.crypto risk calculate --data-dir ./crypto_data --config risk_config.yaml",
    ]
    
    return examples


def advanced_workflow_examples():
    """Advanced workflow examples combining multiple commands."""
    
    workflows = [
        # Complete data collection and validation workflow
        [
            "# 1. Collect data using production template",
            "python -m scripts.data_collector.crypto collect --template production --output-dir ./prod_data",
            "",
            "# 2. Validate collected data",
            "python -m scripts.data_collector.crypto validate --data-dir ./prod_data --output-report validation.json",
            "",
            "# 3. Calculate risk metrics",
            "python -m scripts.data_collector.crypto risk calculate --data-dir ./prod_data --output-dir ./risk_metrics",
            "",
            "# 4. Update universe",
            "python -m scripts.data_collector.crypto universe update --output-file universe.json",
        ],
        
        # Research workflow
        [
            "# 1. Get template recommendations for research",
            "python -m scripts.data_collector.crypto templates recommend --extended-fields --risk-metrics",
            "",
            "# 2. Collect comprehensive data",
            "python -m scripts.data_collector.crypto collect --template research --symbols BTC/USDT ETH/USDT",
            "",
            "# 3. Validate and generate report",
            "python -m scripts.data_collector.crypto validate --data-dir ./crypto_data --output-report research_validation.json",
        ],
        
        # High-frequency trading workflow
        [
            "# 1. Collect high-frequency data",
            "python -m scripts.data_collector.crypto collect --template high_frequency --timeframes 1m 5m",
            "",
            "# 2. Validate high-frequency data",
            "python -m scripts.data_collector.crypto validate --data-dir ./crypto_data --timeframes 1m 5m",
            "",
            "# 3. Calculate short-term risk metrics",
            "python -m scripts.data_collector.crypto risk calculate --data-dir ./crypto_data --metrics volatility var",
        ],
    ]
    
    return workflows


def legacy_compatibility_examples():
    """Examples showing legacy compatibility."""
    
    examples = [
        # Force legacy CLI
        "python scripts/data_collector/crypto/collector.py --legacy download_data",
        
        # Force enhanced CLI
        "python scripts/data_collector/crypto/collector.py --enhanced collect",
        
        # Enhanced CLI commands work automatically
        "python scripts/data_collector/crypto/collector.py collect --template production",
        "python scripts/data_collector/crypto/collector.py templates list",
        
        # Legacy commands still work
        "python scripts/data_collector/crypto/collector.py download_data",
        "python scripts/data_collector/crypto/collector.py normalize_data",
    ]
    
    return examples


def print_examples():
    """Print all examples for documentation."""
    
    print("# Cryptocurrency Data Collection CLI Examples")
    print()
    
    print("## Basic Collection Examples")
    for example in basic_collection_examples():
        print(f"```bash\n{example}\n```")
    print()
    
    print("## Template Management Examples")
    for example in template_examples():
        print(f"```bash\n{example}\n```")
    print()
    
    print("## Configuration Management Examples")
    for example in configuration_examples():
        print(f"```bash\n{example}\n```")
    print()
    
    print("## Data Validation Examples")
    for example in validation_examples():
        print(f"```bash\n{example}\n```")
    print()
    
    print("## Universe Management Examples")
    for example in universe_management_examples():
        print(f"```bash\n{example}\n```")
    print()
    
    print("## Risk Calculation Examples")
    for example in risk_calculation_examples():
        print(f"```bash\n{example}\n```")
    print()
    
    print("## Advanced Workflow Examples")
    for i, workflow in enumerate(advanced_workflow_examples(), 1):
        print(f"### Workflow {i}")
        for line in workflow:
            if line.startswith("#"):
                print(line)
            elif line:
                print(f"```bash\n{line}\n```")
            else:
                print()
    print()
    
    print("## Legacy Compatibility Examples")
    for example in legacy_compatibility_examples():
        print(f"```bash\n{example}\n```")


if __name__ == "__main__":
    print_examples()
