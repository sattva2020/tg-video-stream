#!/usr/bin/env python
"""
Simple test runner for ayugram-python tests.
"""
import sys
import os

# Add the ayugram-python directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pytest

    # Run the tests
    exit_code = pytest.main([
        'tests/test_types.py',
        'tests/test_exceptions.py',
        '-v',
        '--tb=short',
        '--color=yes'
    ])

    sys.exit(exit_code)
except ImportError as e:
    print(f"Error: {e}")
    print("pytest is not installed. Please run: pip install -e .[dev]")
    sys.exit(1)
