#!/usr/bin/env python3
"""
Quick Memory Check for AyuGram Streamer

A simplified script to quickly verify memory usage characteristics.
Use this for fast checks without running full profiling suite.

Usage:
    python quick_memory_check.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def check_imports():
    """Check if all required modules import successfully."""
    print("="*60)
    print("1. Checking Imports")
    print("="*60)

    psutil_available = True
    try:
        import psutil
        print("✓ psutil available")
    except ImportError:
        print("⚠ psutil not available (install with: pip install psutil)")
        print("  Some memory checks will be skipped")
        psutil_available = False

    try:
        from ayugram_adapter import AyuGramAdapter, AYUGRAM_AVAILABLE
        print(f"✓ AyuGram adapter available (AYUGRAM_AVAILABLE={AYUGRAM_AVAILABLE})")
    except ImportError as e:
        print(f"✗ Failed to import AyuGram adapter: {e}")
        return False

    # Note: multi_channel_runner requires dotenv which may not be installed
    # We'll check it separately in the multi-channel function
    print("ⓘ multi_channel_runner check deferred (may need dotenv)")

    # Store psutil availability for other functions
    import builtins
    builtins.psutil_available = psutil_available

    return True


def check_current_memory():
    """Check current process memory usage."""
    print("\n" + "="*60)
    print("2. Current Memory Usage")
    print("="*60)

    import builtins
    if not getattr(builtins, 'psutil_available', False):
        print("⊘ Skipped (psutil not available)")
        return True  # Don't fail, just skip

    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()

        print(f"Process ID: {os.getpid()}")
        print(f"RSS (Resident Set Size): {mem_info.rss / 1024 / 1024:.2f} MB")
        print(f"VMS (Virtual Memory Size): {mem_info.vms / 1024 / 1024:.2f} MB")
        print(f"Memory %: {process.memory_percent():.2f}%")

        return True
    except Exception as e:
        print(f"✗ Error checking memory: {e}")
        return False


def check_adapter_memory():
    """Check memory usage of AyuGramAdapter instances."""
    print("\n" + "="*60)
    print("3. AyuGramAdapter Memory Test")
    print("="*60)

    import builtins
    psutil_ok = getattr(builtins, 'psutil_available', False)

    if not psutil_ok:
        print("⊘ Skipped detailed metrics (psutil not available)")
        print("  Basic adapter instantiation test will run instead...")

    try:
        from ayugram_adapter import AyuGramAdapter

        # Create mock client (AyuGramAdapter needs a Pyrogram client)
        print("\nCreating 3 AyuGramAdapter instances...")
        adapters = []

        for i in range(3):
            # Create a mock client object
            class MockClient:
                def __init__(self, session_id):
                    self.session_id = session_id

            mock_client = MockClient(f"test_session_{i}")
            adapter = AyuGramAdapter(mock_client)
            adapters.append(adapter)
            print(f"  ✓ Adapter {i} created successfully")

        # Verify adapters are properly isolated
        print("\nVerifying adapter isolation...")
        for i, adapter in enumerate(adapters):
            print(f"  Adapter {i}: _event_handlers={len(adapter._event_handlers)}, "
                  f"_is_running={adapter._is_running}")

        if psutil_ok:
            # Get memory metrics if psutil is available
            import psutil
            import os

            process = psutil.Process(os.getpid())
            current_mem = process.memory_info().rss / 1024 / 1024

            print(f"\nCurrent process memory: {current_mem:.2f} MB")
            print(f"Memory per adapter (approximate): {current_mem / 3:.2f} MB")
        else:
            print("\n⚠ Memory metrics unavailable (psutil not installed)")
            print("  Install psutil for detailed memory profiling: pip install psutil")

        return True

    except Exception as e:
        print(f"✗ Error testing adapter: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_multi_channel_memory():
    """Check memory characteristics for multi-channel setup."""
    print("\n" + "="*60)
    print("4. Multi-Channel Memory Characteristics")
    print("="*60)

    try:
        from multi_channel_runner import running_channels
        import builtins

        print(f"Current running channels: {len(running_channels)}")
        print(f"Running channel IDs: {list(running_channels.keys())}")

        if running_channels:
            if not getattr(builtins, 'psutil_available', False):
                print("\n⚠ Memory metrics unavailable (psutil not installed)")
                print("  Install psutil for detailed memory profiling: pip install psutil")
            else:
                import psutil
                import os

                process = psutil.Process(os.getpid())
                current_mem = process.memory_info().rss / 1024 / 1024

                print(f"\nCurrent process memory: {current_mem:.2f} MB")
                print(f"Memory per channel (approximate): {current_mem / len(running_channels):.2f} MB")

            # Check channel data
            for chat_id, channel_data in running_channels.items():
                print(f"\n  Channel {chat_id}:")
                print(f"    Backend: {channel_data.get('backend_type', 'unknown')}")
                print(f"    Has streaming_backend: {'streaming_backend' in channel_data}")
                print(f"    Has queue: {'queue' in channel_data}")
                print(f"    Has auto_end_handler: {'auto_end_handler' in channel_data}")

        else:
            print("\nNo channels currently running (expected for this test)")

        return True

    except ImportError as e:
        if 'dotenv' in str(e):
            print("ⓘ Skipped (dotenv not installed)")
            print("  Install python-dotenv: pip install python-dotenv")
            print("  Or use: pip install -r requirements.txt")
            return True  # Don't fail, just skip
        else:
            print(f"✗ Error importing multi_channel_runner: {e}")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"✗ Error checking multi-channel memory: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_recommendations():
    """Print recommendations based on checks."""
    print("\n" + "="*60)
    print("Recommendations")
    print("="*60)

    print("""
1. For production deployment:
   - Monitor memory usage per channel (target: <200 MB per channel)
   - Set up alerts for memory growth >10 MB/min
   - Run full profiler weekly: python profile_memory_usage.py --leak-detect

2. For development:
   - Quick check after code changes: python quick_memory_check.py
   - Profile new features: python profile_memory_usage.py --single
   - Test multi-channel: python profile_memory_usage.py --multi --channels 3

3. For tg-engine integration:
   - Current adapter is in stub mode (~1-2 MB per instance)
   - After tg-engine integration, expect 50-150 MB per channel
   - Re-run profiling after integration to get real metrics

4. If memory issues detected:
   - Run leak detection: python profile_memory_usage.py --leak-detect --duration 600
   - Check for unclosed event handlers
   - Verify stop_channel_stream() cleanup
   - Review queue manager buffer limits
""")


def main():
    """Run all quick checks."""
    print("\n" + "="*60)
    print("AyuGram Streamer - Quick Memory Check")
    print("="*60)
    print()

    all_passed = True

    # Run checks
    all_passed &= check_imports()
    all_passed &= check_current_memory()
    all_passed &= check_adapter_memory()
    all_passed &= check_multi_channel_memory()

    # Print recommendations
    print_recommendations()

    # Final status
    print("\n" + "="*60)
    if all_passed:
        print("✓ All checks passed!")
    else:
        print("✗ Some checks failed - see details above")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
