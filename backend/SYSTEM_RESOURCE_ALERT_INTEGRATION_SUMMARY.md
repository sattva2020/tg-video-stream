# System Resource Alert Integration Summary

## Overview

The SystemResourceAlertIntegrationService wires together the SystemResourceMonitor with the AlertTriggerService to automatically create and send alerts when system resource thresholds (CPU, memory, disk) are exceeded.

## Files Created

1. **backend/src/services/system_resource_alert_integration.py** (630 lines)
   - Integration service for system resource monitoring
   - Connects SystemResourceMonitor callbacks to AlertTriggerService
   - Handles CPU, memory, and disk alerts (warning and critical)
   - Implements recovery notifications
   - Singleton pattern with get_system_resource_alert_integration()

2. **backend/verify_system_resource_integration_structure.py** (306 lines)
   - Code structure verification script
   - Tests file existence and required patterns
   - Validates callback registration
   - Checks evaluation result structure
   - Verifies grouping and recovery logic
   - 11/11 verification tests passed

3. **backend/tests/integration/test_system_resource_alert_integration.py** (431 lines)
   - End-to-end integration tests
   - 7 functional tests covering all resource types
   - Tests alert grouping by host and resource type
   - Tests recovery notifications
   - Tests separate groups for different hosts

## Integration Flow

### Alert Triggering Flow

1. **SystemResourceMonitor detects threshold breach**
   - CPU usage >= 70% (warning) or >= 90% (critical)
   - Memory usage >= 75% (warning) or >= 90% (critical)
   - Disk usage >= 80% (warning) or >= 95% (critical)
   - Consecutive trigger count >= 3

2. **Callback invocation**
   - `_on_cpu_warning(host, usage, threshold)` called
   - `_on_cpu_critical(host, usage, threshold)` called
   - `_on_memory_warning(host, usage, threshold)` called
   - `_on_memory_critical(host, usage, threshold)` called
   - `_on_disk_warning(host, usage, threshold)` called
   - `_on_disk_critical(host, usage, threshold)` called

3. **Alert processing**
   - Find or create AlertRule for system_resource
   - Create EvaluationResult with severity and context
   - Find or create AlertGroup (grouped by host and resource_type)
   - Trigger alert via AlertTriggerService
   - Create AlertInstance record

4. **Notification delivery**
   - AlertTriggerService prepares notification payload
   - Sends via NotificationRoutingService
   - Delivers to configured channels (email, Telegram, webhook, Slack)
   - Updates AlertInstance with notification status

### Recovery Flow

1. **SystemResourceMonitor detects recovery**
   - Resource usage drops below threshold
   - Consecutive trigger count resets to 0

2. **Callback invocation**
   - `_on_resource_recovery(host, resource_type)` called

3. **Recovery processing**
   - Find AlertRule for system_resource
   - Find active AlertGroup for this host and resource_type
   - Create recovery AlertInstance (status=resolved)
   - Resolve the AlertGroup
   - Send recovery notification if notify_on_recovery=True

## Alert Rule

### Default Rule Created

```python
AlertRule(
    name="System Resource Alert",
    description="Automatic alert triggered when system resource thresholds are exceeded",
    alert_type="system_resource",
    severity="warning",
    enabled=True,
    conditions={
        "metric": "system_resource_usage",
        "operator": "gte",
        "threshold": 70.0,
        "cpu_warning_threshold": 70.0,
        "cpu_critical_threshold": 90.0,
        "memory_warning_threshold": 75.0,
        "memory_critical_threshold": 90.0,
        "disk_warning_threshold": 80.0,
        "disk_critical_threshold": 95.0,
    },
    cooldown_sec=300,  # 5 minutes
    notify_on_recovery=True,
    grouping_window_sec=300,  # 5 minutes
)
```

### Rule Query

The integration queries for the most recent enabled rule of type `system_resource`:

```python
rule = (
    db.query(AlertRule)
    .filter(
        AlertRule.alert_type == "system_resource",
        AlertRule.enabled == True,
    )
    .order_by(AlertRule.created_at.desc())
    .first()
)
```

## Alert Grouping

### Group Key

Alerts are grouped by host and resource_type to prevent notification spam:

```python
context = {
    "host": host,  # e.g., "localhost", "server-1"
    "service": "system",
    "tags": {
        "alert_type": "cpu_warning",  # or "cpu_critical", "memory_warning", etc.
        "resource_type": "cpu",  # or "memory", "disk"
    },
}
```

### Grouping Behavior

- Same host + same resource_type → same group
- Different host → different group
- Different resource_type → different group
- Grouping window: 300 seconds (5 minutes)

### Example

```python
# All three alerts go into the SAME group:
_on_cpu_warning("host-1", 75.0, 70.0)  # Group A
_on_cpu_warning("host-1", 76.0, 70.0)  # Group A
_on_cpu_warning("host-1", 77.0, 70.0)  # Group A

# This alert goes into a DIFFERENT group:
_on_cpu_warning("host-2", 75.0, 70.0)  # Group B (different host)

# This alert goes into a DIFFERENT group:
_on_memory_warning("host-1", 80.0, 75.0)  # Group C (different resource_type)
```

## Verification Results

### Structure Verification (11/11 passed)

✓ Integration File
✓ Callback Registration
✓ Evaluation Result Structure
✓ Alert Rule Creation
✓ Grouping Logic
✓ Recovery Logic
✓ Singleton Pattern
✓ Logging
✓ Error Handling
✓ Documentation
✓ Resource Type Handling

### End-to-End Tests (7/7 passed)

✓ CPU Warning Alert
✓ CPU Critical Alert
✓ Memory Warning Alert
✓ Disk Critical Alert
✓ Alert Grouping
✓ Recovery Alert
✓ Different Hosts Separate Groups

## Usage

### Initialization

```python
from src.services.system_resource_alert_integration import (
    get_system_resource_alert_integration,
    initialize_system_resource_alert_integration,
)

# Initialize at application startup
await initialize_system_resource_alert_integration()

# Or manually
integration = get_system_resource_alert_integration()
integration.initialize()
```

### Manual Testing

```python
import asyncio
from src.services.system_resource_alert_integration import (
    get_system_resource_alert_integration,
)

integration = get_system_resource_alert_integration()

# Trigger a CPU warning alert
asyncio.run(integration._on_cpu_warning(
    host="test-host",
    usage=75.0,
    threshold=70.0
))

# Trigger a memory critical alert
asyncio.run(integration._on_memory_critical(
    host="test-host",
    usage=95.0,
    threshold=90.0
))

# Trigger a disk warning alert
asyncio.run(integration._on_disk_warning(
    host="test-host",
    usage=85.0,
    threshold=80.0
))

# Trigger recovery
asyncio.run(integration._on_resource_recovery(
    host="test-host",
    resource_type="cpu"
))
```

## Callback Methods

### Resource Alert Callbacks

- `async def _on_cpu_warning(host, usage, threshold)`
- `async def _on_cpu_critical(host, usage, threshold)`
- `async def _on_memory_warning(host, usage, threshold)`
- `async def _on_memory_critical(host, usage, threshold)`
- `async def _on_disk_warning(host, usage, threshold)`
- `async def _on_disk_critical(host, usage, threshold)`

### Recovery Callback

- `async def _on_resource_recovery(host, resource_type)`
  - resource_type can be "cpu", "memory", or "disk"

## Evaluation Results

### CPU Warning

```python
EvaluationResult(
    triggered=True,
    alert_type="system_resource",
    severity="warning",
    trigger_value={
        "metric": "cpu_usage",
        "current_value": 75.0,
        "threshold": 70.0,
        "operator": "gte",
        "resource_type": "cpu",
    },
    context={
        "host": "localhost",
        "service": "system",
        "tags": {
            "alert_type": "cpu_warning",
            "resource_type": "cpu",
        },
    },
    reason="CPU usage at 75.0% (warning threshold: 70.0%)",
)
```

### Memory Critical

```python
EvaluationResult(
    triggered=True,
    alert_type="system_resource",
    severity="critical",
    trigger_value={
        "metric": "memory_usage",
        "current_value": 95.0,
        "threshold": 90.0,
        "operator": "gte",
        "resource_type": "memory",
    },
    context={
        "host": "localhost",
        "service": "system",
        "tags": {
            "alert_type": "memory_critical",
            "resource_type": "memory",
        },
    },
    reason="Memory usage at 95.0% - CRITICAL (threshold: 90.0%)",
)
```

## Integration with SystemResourceMonitor

The integration service sets the following callbacks on SystemResourceMonitor:

```python
self.resource_monitor.on_cpu_warning_callback = self._on_cpu_warning
self.resource_monitor.on_cpu_critical_callback = self._on_cpu_critical
self.resource_monitor.on_memory_warning_callback = self._on_memory_warning
self.resource_monitor.on_memory_critical_callback = self._on_memory_critical
self.resource_monitor.on_disk_warning_callback = self._on_disk_warning
self.resource_monitor.on_disk_critical_callback = self._on_disk_critical
self.resource_monitor.on_recovery_callback = self._on_resource_recovery
```

## Patterns Followed

This integration service follows the exact patterns from:

- `StreamAlertIntegrationService` (backend/src/services/stream_alert_integration.py)
- `ViewerAlertIntegrationService` (backend/src/services/viewer_alert_integration.py)
- `ApiRateLimitAlertIntegrationService` (backend/src/services/api_rate_limit_alert_integration.py)

Key patterns:
1. Singleton pattern with get_* function
2. Database session factory pattern
3. Callback-based integration
4. Automatic rule creation on first trigger
5. Alert grouping by context
6. Recovery notification support
7. Comprehensive error handling and logging
8. Russian documentation with code comments

## Next Steps

To complete the integration:

1. **Initialize at startup**
   - Add to app lifespan event handler in backend/src/frameworks/http/app.py
   - Call `initialize_system_resource_alert_integration()` during startup

2. **Configure notification channels**
   - Set up notification channels for the system_resource AlertRule
   - Configure email, Telegram, webhook, or Slack delivery

3. **Test with actual resource monitoring**
   - Start SystemResourceMonitor background monitoring
   - Trigger actual resource thresholds
   - Verify alerts are created and notifications sent

4. **Monitor and tune**
   - Adjust thresholds based on environment
   - Tune cooldown and grouping windows
   - Monitor alert frequency and effectiveness

## Summary

The SystemResourceAlertIntegrationService successfully integrates SystemResourceMonitor with the alerting system, providing automatic alert creation and notification delivery when system resource thresholds are exceeded. The integration follows established patterns, includes comprehensive error handling, and supports alert grouping to prevent notification spam.
