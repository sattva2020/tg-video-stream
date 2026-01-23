#!/usr/bin/env python3
"""Test import of BandwidthMonitor service."""
import sys
sys.path.insert(0, '.')

try:
    from src.services.bandwidth_monitor import BandwidthMonitor
    print("Service imported")
    sys.exit(0)
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)
