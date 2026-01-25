#!/usr/bin/env python3
"""
Performance and Memory Profiling for AyuGram Streamer

This script profiles the memory usage and performance characteristics of the
AyuGram-based streaming implementation. It measures:

1. Memory usage per channel (RSS)
2. CPU usage during streaming
3. Stream startup time
4. Track transition time
5. Memory leak detection (over time)

Usage:
    # Profile single channel
    python profile_memory_usage.py --single --chat-id 123456

    # Profile multi-channel (concurrent streams)
    python profile_memory_usage.py --multi --channels 2

    # Run leak detection (long-running)
    python profile_memory_usage.py --leak-detect --duration 3600

Output:
    Results saved to streamer/profiling_results.json
"""

import asyncio
import json
import os
import psutil
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ayugram_adapter import AyuGramAdapter, AYUGRAM_AVAILABLE
    from multi_channel_runner import (
        start_channel_stream,
        stop_channel_stream,
        running_channels
    )
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("Make sure you're running from the streamer directory.")
    sys.exit(1)


class MemoryProfiler:
    """Profiles memory usage of streaming operations."""

    def __init__(self):
        self.process = psutil.Process()
        self.snapshots: List[Dict[str, Any]] = []
        self.baseline_memory = None

    def get_memory_info(self) -> Dict[str, float]:
        """Get current memory usage in MB."""
        mem_info = self.process.memory_info()
        return {
            'rss_mb': mem_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': mem_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': self.process.memory_percent(),
        }

    def get_cpu_info(self) -> Dict[str, float]:
        """Get current CPU usage."""
        return {
            'cpu_percent': self.process.cpu_percent(interval=0.1),
        }

    def take_snapshot(self, label: str) -> Dict[str, Any]:
        """Take a memory/CPU snapshot with a label."""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'label': label,
            **self.get_memory_info(),
            **self.get_cpu_info(),
        }
        self.snapshots.append(snapshot)
        return snapshot

    def set_baseline(self):
        """Set baseline memory before any operations."""
        self.baseline_memory = self.get_memory_info()
        return self.take_snapshot('baseline')

    def get_memory_increase(self) -> Dict[str, float]:
        """Calculate memory increase from baseline."""
        if not self.baseline_memory:
            return {'rss_mb': 0, 'vms_mb': 0}

        current = self.get_memory_info()
        return {
            'rss_mb': current['rss_mb'] - self.baseline_memory['rss_mb'],
            'vms_mb': current['vms_mb'] - self.baseline_memory['vms_mb'],
        }

    def print_snapshot(self, snapshot: Dict[str, Any]):
        """Print a snapshot in a readable format."""
        print(f"[{snapshot['timestamp']}] {snapshot['label']}")
        print(f"  RSS: {snapshot['rss_mb']:.2f} MB")
        print(f"  VMS: {snapshot['vms_mb']:.2f} MB")
        print(f"  Memory %: {snapshot['percent']:.2f}%")
        print(f"  CPU %: {snapshot['cpu_percent']:.2f}%")
        print()

    def save_results(self, filename: str = 'profiling_results.json'):
        """Save profiling results to JSON file."""
        results = {
            'timestamp': datetime.now().isoformat(),
            'snapshots': self.snapshots,
            'summary': self._generate_summary(),
        }

        output_path = Path(__file__).parent / filename
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to {output_path}")

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        if len(self.snapshots) < 2:
            return {}

        rss_values = [s['rss_mb'] for s in self.snapshots]
        cpu_values = [s['cpu_percent'] for s in self.snapshots]

        return {
            'total_snapshots': len(self.snapshots),
            'memory': {
                'min_mb': min(rss_values),
                'max_mb': max(rss_values),
                'avg_mb': sum(rss_values) / len(rss_values),
                'increase_mb': max(rss_values) - min(rss_values),
            },
            'cpu': {
                'min_percent': min(cpu_values),
                'max_percent': max(cpu_values),
                'avg_percent': sum(cpu_values) / len(cpu_values),
            },
        }


class StreamBenchmarker:
    """Benchmarks streaming operations."""

    def __init__(self):
        self.metrics: Dict[str, float] = {}

    async def measure_startup_time(self, chat_id: int, config: dict) -> float:
        """
        Measure time from start command to stream active.

        Returns:
            Startup time in seconds
        """
        print(f"Measuring startup time for chat {chat_id}...")

        start_time = time.time()

        # Start the stream
        await start_channel_stream(
            chat_id=chat_id,
            config=config,
            streaming_backend=None,  # Will be created internally
        )

        # Wait for stream to be active (check running_channels)
        timeout = 10
        while time.time() - start_time < timeout:
            if chat_id in running_channels:
                elapsed = time.time() - start_time
                print(f"✓ Stream started in {elapsed:.2f} seconds")
                return elapsed
            await asyncio.sleep(0.1)

        print(f"✗ Stream failed to start within {timeout} seconds")
        return -1

    async def measure_track_transition(self, chat_id: int) -> float:
        """
        Measure time from stream end to next track start.

        Returns:
            Transition time in seconds
        """
        print(f"Measuring track transition time for chat {chat_id}...")

        # This would require simulating a StreamEnded event and measuring
        # when the next track starts. For now, return estimated time.
        # TODO: Implement proper timing with mock queue

        return 0.0  # Placeholder

    def save_metrics(self, filename: str = 'benchmarks.json'):
        """Save benchmark metrics to JSON file."""
        output_path = Path(__file__).parent / filename
        with open(output_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)

        print(f"Benchmarks saved to {output_path}")


async def profile_single_channel(chat_id: int):
    """Profile memory and CPU usage for a single channel stream."""
    print(f"\n{'='*60}")
    print(f"Single Channel Profiling")
    print(f"{'='*60}\n")

    profiler = MemoryProfiler()
    benchmarker = StreamBenchmarker()

    # Baseline
    profiler.set_baseline()
    profiler.print_snapshot(profiler.snapshots[-1])

    # Create a mock config
    config = {
        'chat_id': chat_id,
        'session_string': 'mock_session',
        'api_id': 123456,
        'api_hash': 'mock_hash',
        'video_quality': '720p',
    }

    # Measure startup time
    if AYUGRAM_AVAILABLE:
        startup_time = await benchmarker.measure_startup_time(chat_id, config)
        benchmarker.metrics['startup_time_seconds'] = startup_time
        profiler.take_snapshot('after_startup')
        profiler.print_snapshot(profiler.snapshots[-1])

        # Keep stream running for a few seconds to measure steady-state
        print("Measuring steady-state resource usage (5 seconds)...")
        await asyncio.sleep(5)

        profiler.take_snapshot('steady_state')
        profiler.print_snapshot(profiler.snapshots[-1])

        # Stop the stream
        print("Stopping stream...")
        await stop_channel_stream(chat_id)
        await asyncio.sleep(1)

        profiler.take_snapshot('after_stop')
        profiler.print_snapshot(profiler.snapshots[-1])

    # Print summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    summary = profiler._generate_summary()
    print(f"Memory increase: {summary['memory']['increase_mb']:.2f} MB")
    print(f"Peak memory: {summary['memory']['max_mb']:.2f} MB")
    print(f"Average CPU: {summary['cpu']['avg_percent']:.2f}%")
    print(f"Startup time: {benchmarker.metrics.get('startup_time_seconds', 'N/A')} seconds")

    # Save results
    profiler.save_results('single_channel_profile.json')
    benchmarker.save_metrics('benchmarks.json')


async def profile_multi_channel(num_channels: int = 2):
    """Profile memory and CPU usage for multiple concurrent channels."""
    print(f"\n{'='*60}")
    print(f"Multi-Channel Profiling ({num_channels} channels)")
    print(f"{'='*60}\n")

    profiler = MemoryProfiler()

    # Baseline
    profiler.set_baseline()
    profiler.print_snapshot(profiler.snapshots[-1])

    chat_ids = [100000 + i for i in range(num_channels)]

    # Start each channel and measure memory
    for i, chat_id in enumerate(chat_ids, 1):
        print(f"\nStarting channel {i}/{num_channels} (chat_id={chat_id})...")

        config = {
            'chat_id': chat_id,
            'session_string': f'mock_session_{i}',
            'api_id': 123456,
            'api_hash': 'mock_hash',
            'video_quality': '720p',
        }

        if AYUGRAM_AVAILABLE:
            try:
                await start_channel_stream(
                    chat_id=chat_id,
                    config=config,
                    streaming_backend=None,
                )
                await asyncio.sleep(1)

                snapshot = profiler.take_snapshot(f'after_channel_{i}')
                profiler.print_snapshot(snapshot)

            except Exception as e:
                print(f"Error starting channel {i}: {e}")

    # Measure steady-state with all channels running
    if AYUGRAM_AVAILABLE and running_channels:
        print(f"\nMeasuring steady-state with {len(running_channels)} channels (5 seconds)...")
        await asyncio.sleep(5)

        profiler.take_snapshot('steady_state_all_channels')
        profiler.print_snapshot(profiler.snapshots[-1])

        # Calculate per-channel averages
        if profiler.baseline_memory:
            current = profiler.get_memory_info()
            total_increase = current['rss_mb'] - profiler.baseline_memory['rss_mb']
            per_channel = total_increase / num_channels

            print(f"\nTotal memory increase: {total_increase:.2f} MB")
            print(f"Per-channel average: {per_channel:.2f} MB")

        # Stop all channels
        print("\nStopping all channels...")
        for chat_id in list(running_channels.keys()):
            await stop_channel_stream(chat_id)

        await asyncio.sleep(1)

        profiler.take_snapshot('after_stop_all')
        profiler.print_snapshot(profiler.snapshots[-1])

    # Print summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    summary = profiler._generate_summary()
    print(f"Total memory increase: {summary['memory']['increase_mb']:.2f} MB")
    if num_channels > 0:
        print(f"Per-channel average: {summary['memory']['increase_mb'] / num_channels:.2f} MB")
    print(f"Peak memory: {summary['memory']['max_mb']:.2f} MB")
    print(f"Average CPU: {summary['cpu']['avg_percent']:.2f}%")

    # Save results
    profiler.save_results(f'multi_channel_{num_channels}_profile.json')


async def detect_memory_leaks(duration: int = 300):
    """
    Run for an extended period to detect memory leaks.

    Args:
        duration: Duration in seconds to run the test
    """
    print(f"\n{'='*60}")
    print(f"Memory Leak Detection ({duration}s)")
    print(f"{'='*60}\n")

    profiler = MemoryProfiler()
    tracemalloc.start()

    profiler.set_baseline()

    # Start a test channel
    chat_id = 999999
    config = {
        'chat_id': chat_id,
        'session_string': 'leak_test_session',
        'api_id': 123456,
        'api_hash': 'mock_hash',
        'video_quality': '720p',
    }

    if AYUGRAM_AVAILABLE:
        try:
            await start_channel_stream(chat_id, config, None)

            # Monitor memory over time
            print(f"Monitoring memory for {duration} seconds...")
            interval = 30  # Take snapshot every 30 seconds
            elapsed = 0

            while elapsed < duration:
                await asyncio.sleep(interval)
                elapsed += interval

                snapshot = profiler.take_snapshot(f't_{elapsed}s')
                current, peak = tracemalloc.get_traced_memory()

                print(f"[{elapsed}s] RSS: {snapshot['rss_mb']:.2f} MB | "
                      f"Tracemalloc: {current / 1024 / 1024:.2f} MB (peak: {peak / 1024 / 1024:.2f} MB)")

                # Check for significant memory growth
                if profiler.baseline_memory:
                    increase = snapshot['rss_mb'] - profiler.baseline_memory['rss_mb']
                    if increase > 500:  # More than 500 MB growth
                        print(f"⚠️  WARNING: Memory increased by {increase:.2f} MB")

            # Cleanup
            await stop_channel_stream(chat_id)

        except Exception as e:
            print(f"Error during leak detection: {e}")

    tracemalloc.stop()

    # Analyze trends
    print("\n" + "="*60)
    print("Leak Detection Analysis")
    print("="*60)

    if len(profiler.snapshots) > 2:
        first = profiler.snapshots[1]  # After startup
        last = profiler.snapshots[-1]

        memory_growth = last['rss_mb'] - first['rss_mb']
        time_diff = (datetime.fromisoformat(last['timestamp']) -
                     datetime.fromisoformat(first['timestamp'])).total_seconds()

        growth_rate = memory_growth / (time_diff / 60) if time_diff > 0 else 0  # MB per minute

        print(f"Memory growth over {time_diff:.0f}s: {memory_growth:.2f} MB")
        print(f"Growth rate: {growth_rate:.2f} MB/min")

        if growth_rate > 10:  # More than 10 MB per minute
            print("⚠️  WARNING: Possible memory leak detected!")
        else:
            print("✓ No significant memory leak detected")

    profiler.save_results('memory_leak_detection.json')


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Profile memory and performance of AyuGram streamer'
    )
    parser.add_argument(
        '--single',
        action='store_true',
        help='Profile single channel'
    )
    parser.add_argument(
        '--multi',
        action='store_true',
        help='Profile multiple concurrent channels'
    )
    parser.add_argument(
        '--channels',
        type=int,
        default=2,
        help='Number of channels for multi-channel test (default: 2)'
    )
    parser.add_argument(
        '--leak-detect',
        action='store_true',
        help='Run memory leak detection'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=300,
        help='Duration for leak detection in seconds (default: 300)'
    )
    parser.add_argument(
        '--chat-id',
        type=int,
        default=123456,
        help='Chat ID for single channel test (default: 123456)'
    )

    args = parser.parse_args()

    # Check if at least one mode is selected
    if not any([args.single, args.multi, args.leak_detect]):
        parser.print_help()
        print("\nERROR: Please select at least one profiling mode (--single, --multi, or --leak-detect)")
        sys.exit(1)

    # Check AyuGram availability
    print(f"AyuGram available: {AYUGRAM_AVAILABLE}")
    if not AYUGRAM_AVAILABLE:
        print("WARNING: AyuGram adapter not available. Running in mock mode.")

    # Run selected profiling mode
    try:
        if args.single:
            await profile_single_channel(args.chat_id)

        if args.multi:
            await profile_multi_channel(args.channels)

        if args.leak_detect:
            await detect_memory_leaks(args.duration)

        print("\n✓ Profiling complete!")

    except KeyboardInterrupt:
        print("\nProfiling interrupted by user")
    except Exception as e:
        print(f"\nERROR: Profiling failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
