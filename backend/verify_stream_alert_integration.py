"""
Simple verification script for stream failure alerting integration.

This script verifies that:
1. Stream failures are detected
2. Alert rules are created/triggered
3. Alert instances are created
4. Alert groups are created
5. Recovery alerts work
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone
from src.database import SessionLocal
from src.services.stream_health_monitor import StreamHealthStatus, get_stream_health_monitor
from src.services.stream_failure_monitor import get_stream_failure_alert_monitor
from src.services.stream_alert_integration import get_stream_alert_integration
from src.services.alert_service import AlertService
from src.services.alert_grouping_service import AlertGroupingService
from src.models.alert import AlertRule


async def verify_stream_failure():
    """Verify stream failure creates an alert."""
    print("\n=== Verifying Stream Failure Detection ===\n")

    # Initialize integration
    integration = get_stream_alert_integration()
    integration.initialize()
    print("✓ Integration initialized")

    db = SessionLocal()
    try:
        stream_id = "test-stream-123"

        # Create unhealthy stream status
        health_status = StreamHealthStatus(
            stream_id=stream_id,
            is_healthy=False,
            last_check=datetime.now(timezone.utc),
            consecutive_failures=5,  # Exceeds threshold
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
        print(f"✓ Unhealthy stream status saved for {stream_id}")

        # Trigger failure check
        failure_monitor = get_stream_failure_alert_monitor()
        await failure_monitor.check_stream_failures(stream_id)
        print("✓ Failure check triggered")

        # Give it a moment to process
        await asyncio.sleep(0.5)

        # Verify alert was created
        alert_service = AlertService(db)
        rule = (
            db.query(AlertRule)
            .filter(AlertRule.alert_type == "stream_failure")
            .first()
        )

        if not rule:
            print("✗ Alert rule was not created")
            return False

        print(f"✓ Alert rule created: {rule.id}")

        # Get alert instances
        instances = alert_service.list_instances(rule_id=rule.id, limit=10)

        if len(instances) == 0:
            print("✗ No alert instances created")
            return False

        print(f"✓ Alert instances created: {len(instances)}")

        # Verify the instance
        instance = instances[0]
        print(f"  - Instance ID: {instance.id}")
        print(f"  - Status: {instance.status}")
        print(f"  - Type: {instance.alert_type}")
        print(f"  - Severity: {instance.severity}")
        print(f"  - Stream ID: {instance.context.get('stream_id')}")

        # Verify group was created
        grouping_service = AlertGroupingService(db)
        groups = grouping_service.get_active_groups_for_rule(rule_id=rule.id)

        if len(groups) == 0:
            print("✗ No alert groups created")
            return False

        print(f"✓ Alert groups created: {len(groups)}")

        group = groups[0]
        print(f"  - Group ID: {group.id}")
        print(f"  - Group status: {group.status}")
        print(f"  - Alert count: {group.alert_count}")

        # Cleanup
        print("\nCleaning up test data...")
        await r.delete(key)
        await failure_monitor.reset_failure_status(stream_id)

        for inst in instances:
            alert_service.delete_instance(inst.id)
        for grp in groups:
            alert_service.delete_group(grp.id)
        db.delete(rule)
        db.commit()
        print("✓ Cleanup complete")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def verify_stream_recovery():
    """Verify stream recovery creates a resolved alert."""
    print("\n=== Verifying Stream Recovery Detection ===\n")

    db = SessionLocal()
    try:
        stream_id = "test-stream-456"

        # First create a failure
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
        print(f"✓ Unhealthy status saved for {stream_id}")

        failure_monitor = get_stream_failure_alert_monitor()
        await failure_monitor.check_stream_failures(stream_id)
        await asyncio.sleep(0.5)
        print("✓ Failure detected")

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
        print("✓ Recovery detected")

        # Verify recovery alert
        alert_service = AlertService(db)
        rule = (
            db.query(AlertRule)
            .filter(AlertRule.alert_type == "stream_failure")
            .first()
        )

        if not rule:
            print("✗ Alert rule not found")
            return False

        instances = alert_service.list_instances(rule_id=rule.id, limit=20)

        if len(instances) < 2:
            print(f"✗ Expected at least 2 instances, got {len(instances)}")
            return False

        # Find resolved instances
        resolved_instances = [i for i in instances if i.status == "resolved"]

        if len(resolved_instances) == 0:
            print("✗ No resolved instances found")
            return False

        print(f"✓ Resolved instances created: {len(resolved_instances)}")

        resolved_instance = resolved_instances[0]
        print(f"  - Instance ID: {resolved_instance.id}")
        print(f"  - Status: {resolved_instance.status}")

        # Verify groups resolved
        grouping_service = AlertGroupingService(db)
        groups = grouping_service.get_active_groups_for_rule(rule_id=rule.id)
        active_groups = [g for g in groups if g.status == "active"]

        if len(active_groups) > 0:
            print("✗ Groups should be resolved after recovery")
            return False

        print("✓ All groups resolved after recovery")

        # Cleanup
        print("\nCleaning up test data...")
        await r.delete(key)
        await failure_monitor.reset_failure_status(stream_id)

        for inst in instances:
            alert_service.delete_instance(inst.id)
        for grp in groups:
            alert_service.delete_group(grp.id)
        db.delete(rule)
        db.commit()
        print("✓ Cleanup complete")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("Stream Alert Integration Verification")
    print("="*60)

    # Test 1: Stream failure
    result1 = await verify_stream_failure()

    if not result1:
        print("\n✗ Stream failure verification FAILED")
        return 1

    print("\n✓ Stream failure verification PASSED")

    # Test 2: Stream recovery
    result2 = await verify_stream_recovery()

    if not result2:
        print("\n✗ Stream recovery verification FAILED")
        return 1

    print("\n✓ Stream recovery verification PASSED")

    print("\n" + "="*60)
    print("All verification tests PASSED!")
    print("="*60 + "\n")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
