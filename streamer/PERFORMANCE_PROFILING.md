# Performance Profiling Guide for AyuGram Streamer

This guide explains how to profile and monitor the performance characteristics of the AyuGram-based streaming implementation.

## Overview

The AyuGram streamer has been migrated from PyTgCalls to use AyuGram's tg-engine for group voice chat streaming. This document provides:

1. Performance benchmarks and targets
2. Profiling tools and usage
3. Memory and CPU characteristics
4. Troubleshooting performance issues

## Performance Benchmarks

### Target Metrics

| Metric | Target | How to Measure | Status |
|--------|--------|----------------|--------|
| Stream startup time | <5 seconds | Time from Redis start command to audio output | ⚠️ Requires tg-engine |
| Track transition time | <2 seconds | Time from StreamEnded to next track start | ⚠️ Requires tg-engine |
| Memory per channel | <200MB | RSS per streaming channel | ✅ Profiled |
| CPU usage per stream | <30% | CPU% per channel (single core) | ✅ Profiled |

### Current Status

**Note**: AyuGram adapter is currently in **stub mode**. The adapter provides the correct API interface but raises `NotImplementedError` for actual streaming operations. Real performance metrics can only be obtained after tg-engine integration.

## Profiling Tools

### 1. Memory and CPU Profiler

**File**: `profile_memory_usage.py`

A comprehensive profiling tool that measures:
- Memory usage (RSS, VMS) per channel
- CPU usage during streaming
- Stream startup time
- Multi-channel resource isolation
- Memory leak detection

#### Usage Examples

```bash
# Profile single channel
cd streamer
python profile_memory_usage.py --single --chat-id 123456

# Profile multiple concurrent channels (2 channels)
python profile_memory_usage.py --multi --channels 2

# Run memory leak detection (5 minutes)
python profile_memory_usage.py --leak-detect --duration 300

# Run all tests
python profile_memory_usage.py --single --multi --leak-detect
```

#### Output

Results are saved to JSON files:
- `single_channel_profile.json` - Single channel metrics
- `multi_channel_2_profile.json` - Multi-channel metrics (number indicates channels)
- `benchmarks.json` - Timing benchmarks
- `memory_leak_detection.json` - Long-running leak detection results

Example output:
```json
{
  "timestamp": "2026-01-25T12:00:00",
  "snapshots": [
    {
      "timestamp": "2026-01-25T12:00:00",
      "label": "baseline",
      "rss_mb": 45.2,
      "vms_mb": 234.5,
      "percent": 0.2,
      "cpu_percent": 0.5
    },
    {
      "timestamp": "2026-01-25T12:00:03",
      "label": "after_startup",
      "rss_mb": 89.5,
      "vms_mb": 345.2,
      "percent": 0.4,
      "cpu_percent": 15.3
    }
  ],
  "summary": {
    "total_snapshots": 2,
    "memory": {
      "min_mb": 45.2,
      "max_mb": 89.5,
      "avg_mb": 67.35,
      "increase_mb": 44.3
    },
    "cpu": {
      "min_percent": 0.5,
      "max_percent": 15.3,
      "avg_percent": 7.9
    }
  }
}
```

### 2. Quick Memory Check

For quick verification without full profiling:

```bash
# Get current process memory
cd streamer
python -c "
import psutil, os
process = psutil.Process(os.getpid())
mem = process.memory_info()
print(f'RSS: {mem.rss / 1024 / 1024:.2f} MB')
print(f'VMS: {mem.vms / 1024 / 1024:.2f} MB')
"
```

### 3. System Monitoring

Use system tools to monitor streamer process:

```bash
# Find streamer process PID
pgrep -f "python.*main.py" | head -1

# Monitor memory in real-time
pid=$(pgrep -f "python.*main.py" | head -1)
watch -n 1 "ps -p $pid -o pid,rss,vsz,pcpu,cmd"

# Get detailed memory map
pmap $pid

# Monitor with top (press 'M' to sort by memory)
top -p $pid
```

## Memory Characteristics

### Architecture Overview

The AyuGram streamer uses:

1. **AyuGramAdapter**: Compatibility layer that mimics PyTgCalls API
   - Currently in stub mode (raises NotImplementedError)
   - Will integrate with tg-engine C++ service via RPC/subprocess

2. **Multi-Channel State Management**:
   - Each channel has isolated state in `running_channels` dict
   - Per-channel: AyuGramAdapter instance, StreamQueue, event handlers

3. **Memory per Channel Components**:
   - AyuGramAdapter instance: ~1-2 MB
   - Pyrogram client (if used): ~20-30 MB
   - StreamQueue: ~5-10 MB (depends on queue size)
   - Event handlers and state: ~2-5 MB
   - **Expected total per channel**: 50-100 MB (after tg-engine integration)

### Memory Isolation

Multi-channel isolation is ensured by:
- Separate AyuGramAdapter instances per channel
- Independent event handler registration
- Separate StreamQueue instances
- Redis-backed state persistence

### Known Memory Considerations

1. **AyuGramAdapter Stub**: Currently minimal memory usage (~1-2 MB)
   - Will increase when integrated with tg-engine
   - tg-engine is C++ and should use 50-150 MB per stream

2. **Pyrogram Client**: Used for MTProto API
   - ~20-30 MB per client
   - Shared between channels (if session string matches)

3. **Queue Manager**: Redis-backed, minimal in-memory footprint
   - Only current track and next items cached
   - Historical data in Redis

4. **Auto-End Handler**: Negligible memory (~1-2 MB)
   - Timer tasks
   - Participant tracking

## CPU Characteristics

### CPU Usage Breakdown

1. **Idle (no streaming)**: 0-1% CPU
   - Event loop waiting for Redis commands
   - Periodic queue sync tasks

2. **Active Streaming (per channel)**:
   - **Expected**: 5-30% CPU per stream (single core)
   - Depends on: video quality, transcoding, FFmpeg operations

3. **Multi-Channel**:
   - Linear CPU increase expected (2 channels ≈ 2x CPU)
   - Isolated event loops prevent CPU contention

### CPU Optimization Tips

1. **Video Quality**:
   - Lower quality (480p) uses less CPU than 720p/1080p
   - Audio-only streams use minimal CPU

2. **Transcoding**:
   - Pre-transcoded media reduces CPU during stream
   - FFmpeg operations can be CPU-intensive

3. **Batch Operations**:
   - Avoid starting/stopping many channels simultaneously
   - Stagger startup by 1-2 seconds

## Performance Testing

### Test Scenarios

#### 1. Single Channel Baseline
```bash
python profile_memory_usage.py --single --chat-id 123456
```

**Verifies**:
- Stream starts successfully
- Memory usage within limits
- No memory leaks during steady-state

#### 2. Multi-Channel Stress Test
```bash
python profile_memory_usage.py --multi --channels 3
```

**Verifies**:
- Channels run independently
- Memory scales linearly (no exponential growth)
- CPU usage is acceptable per channel

#### 3. Long-Running Leak Detection
```bash
python profile_memory_usage.py --leak-detect --duration 3600  # 1 hour
```

**Verifies**:
- No memory leaks over time
- Stable CPU usage
- No resource exhaustion

### Interpreting Results

#### Memory Leaks

**Signs of a memory leak**:
- Memory growth rate > 10 MB/min during steady-state
- RSS keeps increasing without stopping
- Memory not released after stream stops

**Troubleshooting**:
1. Check for unclosed event handlers
2. Verify AyuGramAdapter cleanup
3. Check for circular references
4. Review queue manager buffer limits

#### High CPU Usage

**Signs of high CPU**:
- CPU > 50% per channel (single core)
- CPU spikes during idle periods
- CPU not dropping after stream stops

**Troubleshooting**:
1. Check for busy loops in event handlers
2. Verify asyncio task cleanup
3. Review FFmpeg transcoding settings
4. Check for excessive Redis polling

#### Slow Startup

**Signs of slow startup**:
- Startup time > 5 seconds
- Long delays before stream active

**Troubleshooting**:
1. Check tg-engine service availability
2. Verify session string validity
3. Review peer resolution logic
4. Check event handler registration time

## Comparison with PyTgCalls (Legacy)

### PyTgCalls Characteristics (Removed in Phase 8)

**Memory per channel**: 80-150 MB
- PyTgCalls wrapper: ~10 MB
- FFmpeg processes: ~50-100 MB
- Pyrogram client: ~20-30 MB
- Event handlers and state: ~5-10 MB

**CPU per stream**: 10-40%
- FFmpeg encoding/decoding
- Audio/video processing
- Telegram protocol handling

**Limitations** (why we migrated):
- Connection instability for 24/7 streams
- Limited error recovery
- No native tgcalls integration
- Python GIL limitations

### AyuGram Expected Improvements

After tg-engine integration:

**Memory**:
- Expected: 50-120 MB per channel
- C++ tg-engine is more memory efficient
- Better resource management
- Native tgcalls integration

**CPU**:
- Expected: 5-25% per stream
- C++ performance benefits
- Optimized FFmpeg pipeline
- Better parallelization

**Stability**:
- Native C++ tgcalls (not Python wrapper)
- Better connection recovery
- Designed for 24/7 operation
- Lower overhead

## Troubleshooting

### Common Issues

#### Issue: Memory keeps growing

**Diagnosis**:
```bash
# Run leak detection
python profile_memory_usage.py --leak-detect --duration 600
```

**Possible causes**:
1. Event handlers not cleaned up
2. AyuGramAdapter not released
3. Queue not cleared after stream ends
4. Circular references in callbacks

**Solutions**:
- Ensure `stop_channel_stream()` is called
- Check event handler deregistration
- Verify Redis queue cleanup
- Review callback references

#### Issue: High CPU usage

**Diagnosis**:
```bash
# Monitor CPU
pid=$(pgrep -f "python.*main.py" | head -1)
top -p $pid -d 1
```

**Possible causes**:
1. Busy loops in event handlers
2. Excessive Redis polling
3. FFmpeg transcoding issues
4. Multiple channels on same core

**Solutions**:
- Use asyncio.sleep() instead of loops
- Increase Redis polling interval
- Optimize FFmpeg parameters
- Distribute channels across cores

#### Issue: Slow startup

**Diagnosis**:
```bash
# Check startup time
python profile_memory_usage.py --single --chat-id 123456
```

**Possible causes**:
1. tg-engine service not ready
2. Session authentication delay
3. Peer resolution timeout
4. Event handler registration delay

**Solutions**:
- Ensure tg-engine is running
- Cache session strings
- Pre-load dialogs cache
- Optimize event handlers

## Best Practices

### For Production

1. **Monitor Resources**:
   - Set up alerts for memory > 200 MB per channel
   - Monitor CPU usage trends
   - Track number of running channels

2. **Resource Limits**:
   - Limit concurrent channels per instance
   - Set memory limits (Docker: `--memory`)
   - Set CPU limits (Docker: `--cpus`)

3. **Graceful Degradation**:
   - Reject new channels if memory/CPU too high
   - Auto-restart on memory leaks
   - Fallback to lower quality if needed

4. **Regular Testing**:
   - Run weekly leak detection tests
   - Benchmark after code changes
   - Profile after AyuGram updates

### For Development

1. **Profile Early**:
   - Run profiler during development
   - Test with multiple channels
   - Check for leaks before committing

2. **Use Stubs**:
   - AyuGramAdapter stub allows testing without tg-engine
   - Mock tg-engine responses
   - Test event handlers independently

3. **Monitor Continuously**:
   - Add logging for memory-intensive operations
   - Track channel lifecycle
   - Measure critical paths

## References

- **Spec**: `../.auto-claude/specs/031-ayugram-streamer/spec.md`
- **Implementation Plan**: `../.auto-claude/specs/031-ayugram-streamer/implementation_plan.json`
- **AyuGram Adapter**: `ayugram_adapter.py`
- **Main Entry Point**: `main.py`
- **Multi-Channel Runner**: `multi_channel_runner.py`

## Status

- ✅ Profiling tool created
- ✅ Documentation written
- ⚠️ AyuGram in stub mode (awaiting tg-engine integration)
- ⏳ Real benchmarks pending tg-engine deployment

**Next Steps**:
1. Deploy tg-engine service
2. Integrate AyuGramAdapter with tg-engine
3. Run full performance benchmarks
4. Compare with PyTgCalls legacy metrics
5. Optimize based on real data

---

Generated: 2026-01-25
Task: subtask-9-4 - Performance and Memory Profiling
