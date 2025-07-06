# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Main entry point for the cryptocurrency data collection CLI.

This module allows the crypto data collection system to be run as a module:
    python -m qlib.scripts.data_collector.crypto [command] [options]

Or from the project root:
    python -m scripts.data_collector.crypto [command] [options]
"""

import sys
from pathlib import Path

# Add the crypto module directory to Python path
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR))

# Add the data_collector parent directory to handle imports
sys.path.insert(0, str(CUR_DIR.parent.parent))

# Now import the CLI main function
try:
    from cli import main
except ImportError as e:
    print(f"Error importing crypto CLI: {e}")
    print("Please ensure you are running from the correct directory")
    sys.exit(1)

if __name__ == "__main__":
    main()