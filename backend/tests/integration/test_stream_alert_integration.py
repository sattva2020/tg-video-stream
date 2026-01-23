"""
End-to-end integration test for stream failure alerting.

Verifies that stream failures are properly detected and trigger alerts.
"""
import asyncio
import pytest
from datetime import datetime, timezone
from uuid import UUID

from src.database import SessionLocal
from src.services.stream_health_monitor import StreamHealthStatus, get_stream_health_monitor
from src.services.stream_failure_monitor import get_stream_failure_alert_monitor
from src.services.stream_alert_integration import get_stream_alert_integration
from src.services.alert_service import AlertService
from src.services.alert_grouping_service import AlertGroupingService
from src.models.alert import AlertRule, AlertInstance, AlertGroup


@pytest.mark.asyncio
async def test_stream_failure_creates_alert():
    """Test that stream failure detection creates an AlertInstance."""
    # Initialize integration
    integration = get_stream_alert_integration()
    integration.initialize()

    db = SessionLocal()
    try:
        # Simulate stream failure
        stream_id = "test-stream-123"

        # Create unhealthy stream status
        health_status = StreamHealthStatus(
            stream_id=stream_id,
            is_healthy=False,
            last_check=datetime.now(timezone.utc),
            consecutive_failures=5,  # Exceeds threshold of 3
            last_failure_type="network",
            last_failure_time=datetime.now(timezone.utc),
            last_error_message="Connection timeout",
            total_checks=10,
            failed_checks=5
        )

        # Save health status to Redis
        health_monitor = get_stream_health_monitor()
        r = await health_monitor._get_redis()
        key = health_monitor._get_health_key(stream_id)
        await r.hset(key, mapping=health_status.to_redis_dict())

        # Trigger failure check
        failure_monitor = get_stream_failure_alert_monitor()
        await failure_monitor.check_stream_failures(stream_id)

        # Give it a moment to process
        await asyncio.sleep(0.5)

        # Verify alert was created
        alert_service = AlertService(db)

        # Get the stream failure rule
        rule = (
            db.query(AlertRule)
            .filter(AlertRule.alert_type == "stream_failure")
            .first()
        )

        assert rule is not None, "Stream failure rule should be created"

        # Get alert instances for this rule
        instances = alert_service.list_instances(rule_id=rule.id, limit=10)

        assert len(instances) > 0, "At least one alert instance should be created"

        # Verify the instance has correct data
        instance = instances[0]
        assert instance.status == "firing"
        assert instance.alert_type == "stream_failure"
        assert instance.severity in ["critical", "warning"]
        assert instance.context.get("stream_id") == stream_id

        # Verify group was created
        grouping_service = AlertGroupingService(db)
        groups = grouping_service.get_active_groups_for_rule(rule_id=rule.id)

        assert len(groups) > 0, "Alert group should be created"

        group = groups[0]
        assert group.status == "active"
        assert group.alert_count >= 1

        print(f"✓ Alert instance created: {instance.id}")
        print(f"✓ Alert group created: {group.id}")
        print(f"✓ Stream ID: {stream_id}")
        print(f"✓ Failure type: {health_status.last_failure_type}")

        # Cleanup
        await r.delete(key)
        await failure_monitor.reset_failure_status(stream_id)

        # Delete test instances
        for inst in instances:
            alert_service.delete_instance(inst.id)
        for grp in groups:
            alert_service.delete_group(grp.id)
        db.delete(rule)
        db.commit()

    finally:
        db.close()


@pytest.mark.asyncio
async def test_stream_recovery_creates_resolved_alert():
    """Test that stream recovery creates a resolved alert."""
    # Initialize integration
    integration = get_stream_alert_integration()
    integration.initialize()

    db = SessionLocal()
    try:
        stream_id = "test-stream-456"

        # First, create a failure
        health_status_unhealthy = StreamHealthStatus(
            stream_id=stream_id,
            is_healthy=False,
            last_check=datetime.now(timezone.utc),
            consecutive_failures=5,
            last_failure_type="network",
            last_failure_time=datetime.now(timezone.utc),
            last_error_message="Connection timeout",
            total_checks=10,
            failed_checks=5
        )

        health_monitor = get_stream_health_monitor()
        r = await health_monitor._get_redis()
        key = health_monitor._get_health_key(stream_id)
        await r.hset(key, mapping=health_status_unhealthy.to_redis_dict())

        failure_monitor = get_stream_failure_alert_monitor()
        await failure_monitor.check_stream_failures(stream_id)
        await asyncio.sleep(0.5)

        # Now simulate recovery
        health_status_healthy = StreamHealthStatus(
            stream_id=stream_id,
            is_healthy=True,
            last_check=datetime.now(timezone.utc),
            consecutive_failures=0,
            total_checks=11,
            failed_checks=5
        )

        await r.hset(key, mapping=health_status_healthy.to_redis_dict())
        await failure_monitor.check_stream_failures(stream_id)
        await asyncio.sleep(0.5)

        # Verify recovery alert was created
        alert_service = AlertService(db)
        rule = (
            db.query(AlertRule)
            .filter(AlertRule.alert_type == "stream_failure")
            .first()
        )

        assert rule is not None, "Stream failure rule should exist"

        # Get all instances (including resolved)
        instances = alert_service.list_instances(rule_id=rule.id, limit=20)

        # Should have at least 2: one firing, one resolved
        assert len(instances) >= 2, f"Should have at least 2 instances, got {len(instances)}"

        # Find the resolved instance
        resolved_instances = [i for i in instances if i.status == "resolved"]
        assert len(resolved_instances) > 0, "Should have at least one resolved instance"

        resolved_instance = resolved_instances[0]
        assert resolved_instance.status == "resolved"
        assert resolved_instance.context.get("stream_id") == stream_id

        # Verify group was resolved
        grouping_service = AlertGroupingService(db)
        groups = grouping_service.get_active_groups_for_rule(rule_id=rule.id)

        # All groups should be resolved (no active groups)
        active_groups = [g for g in groups if g.status == "active"]
        assert len(active_groups) == 0, "All groups should be resolved after recovery"

        print(f"✓ Recovery alert created: {resolved_instance.id}")
        print(f"✓ Alert group resolved")
        print(f"✓ Stream ID: {stream_id}")

        # Cleanup
        await r.delete(key)
        await failure_monitor.reset_failure_status(stream_id)

        for inst in instances:
            alert_service.delete_instance(inst.id)
        for grp in groups:
            alert_service.delete_group(grp.id)
        db.delete(rule)
        db.commit()

    finally:
        db.close()


def test_stream_alert_integration_initialization():
    """Test that the stream alert integration can be initialized."""
    integration = get_stream_alert_integration()
    assert integration is not None

    integration.initialize()
    assert integration._initialized is True
    assert integration.failure_monitor is not None

    print("✓ Stream alert integration initialized successfully")


if __name__ == "__main__":
    # Run quick verification
    print("\n=== Stream Alert Integration Verification ===\n")

    print("1. Testing integration initialization...")
    test_stream_alert_integration_initialization()
    print()

    print("2. Testing stream failure detection...")
    asyncio.run(test_stream_failure_creates_alert())
    print()

    print("3. Testing stream recovery...")
    asyncio.run(test_stream_recovery_creates_resolved_alert())
    print()

    print("=== All verification tests passed! ===\n")
