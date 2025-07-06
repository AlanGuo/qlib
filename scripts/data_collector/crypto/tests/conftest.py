# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Pytest configuration for crypto data collector tests.
"""

import sys
import os
from pathlib import Path

# Add the crypto module directory to Python path for absolute imports
crypto_root = Path(__file__).parent.parent
if str(crypto_root) not in sys.path:
    sys.path.insert(0, str(crypto_root))

# Set environment variables for testing
os.environ["QLIB_TEST_MODE"] = "1"
