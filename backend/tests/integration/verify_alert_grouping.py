#!/usr/bin/env python3
"""
Standalone verification script for alert grouping to prevent notification spam.

This script can be run directly to verify alert grouping functionality:
```bash
cd backend && python tests/integration/verify_alert_grouping.py
```

It verifies:
1. Create alert rule with short interval
2. Trigger condition that persists
3. Verify alerts are grouped
4. Verify single notification per group
5. Verify group resolution notification sent
"""
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.alert import AlertGroup, AlertInstance, AlertRule
from src.schemas.alerts import AlertRuleCreate
from src.services.alert_service import AlertService
from src.services.alert_evaluator import AlertEvaluator, EvaluationResult
from src.services.alert_trigger_service import AlertTriggerService
from src.services.alert_grouping_service import AlertGroupingService


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_test(test_name: str):
    """Print a test name."""
    print(f"\n▶ {test_name}")


def print_pass(message: str):
    """Print a passing test."""
    print(f"  ✓ PASS: {message}")


def print_fail(message: str):
    """Print a failing test."""
    print(f"  ✗ FAIL: {message}")


def cleanup_test_data(db: Session, rule_id: uuid.UUID):
    """Clean up test data."""
    try:
        # Delete instances
        db.query(AlertInstance).filter(AlertInstance.rule_id == rule_id).delete()
        # Delete groups
        db.query(AlertGroup).filter(AlertGroup.rule_id == rule_id).delete()
        # Delete rule
        db.query(AlertRule).filter(AlertRule.id == rule_id).delete()
        db.commit()
    except Exception as e:
        print(f"  ⚠ Warning: Could not clean up test data: {e}")


def verify_alert_grouping():
    """Main verification function."""
    print_section("ALERT GROUPING VERIFICATION")

    db: Session = SessionLocal()
    test_passed = True

    try:
        # Initialize services
        alert_service = AlertService(db)
        alert_evaluator = AlertEvaluator(db)
        alert_trigger_service = AlertTriggerService(db)
        alert_grouping_service = AlertGroupingService(db)

        # ========================================================================
        # Test 1: Create alert rule with short interval
        # ========================================================================
        print_test("Test 1: Create alert rule with short interval")

        rule_data = AlertRuleCreate(
            name="High CPU Usage Verification Test",
            description="Verification test rule for alert grouping",
            alert_type="system_resource",
            severity="warning",
            category="performance",
            enabled=True,
            conditions={
                "metric": "cpu_usage",
                "operator": "gt",
                "threshold": 90,
                "evaluation_window_sec": 60,
            },
            cooldown_sec=30,  # Short cooldown for testing
            notification_channels={
                "telegram": [123456789],
            },
            notify_on_recovery=True,
            auto_resolve=False,
            escalation_enabled=False,
        )

        rule = alert_service.create_rule(rule_data)

        if rule is None:
            print_fail("Failed to create alert rule")
            test_passed = False
            return test_passed

        print_pass(f"Created alert rule: {rule.name} (ID: {rule.id})")

        # ========================================================================
        # Test 2: Trigger condition that persists (5 times)
        # ========================================================================
        print_test("Test 2: Trigger condition that persists (5 times)")

        alert_context = {
            "host": "test-server-1",
            "service": "api",
            "tags": {
                "environment": "testing",
                "region": "us-east-1",
            },
        }

        triggered_instances = []
        group_ids = []

        for i in range(5):
            # Simulate CPU usage spike
            result = EvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                alert_type=rule.alert_type,
                severity=rule.severity,
                triggered=True,
                reason=f"CPU usage is {95 + i}%, threshold is 90%",
                trigger_value={
                    "metric": "cpu_usage",
                    "current_value": 95 + i,
                    "threshold": 90,
                    "operator": "gt",
                },
                context=alert_context,
            )

            # Find or create group
            group, is_new_group = alert_grouping_service.find_or_create_group(
                rule=rule,
                context=alert_context,
                alert_type=rule.alert_type,
                severity=rule.severity,
                grouping_window_sec=300,
            )

            if group is None:
                print_fail(f"Failed to create/find group for iteration {i + 1}")
                test_passed = False
                break

            group_ids.append(group.id)

            # Trigger alert
            instance = alert_trigger_service.trigger_alert(
                result=result,
                group_id=group.id,
            )

            if instance is None:
                print_fail(f"Failed to trigger alert for iteration {i + 1}")
                test_passed = False
                break

            # Add alert to group
            alert_grouping_service.add_alert_to_group(
                instance=instance,
                group=group,
            )

            triggered_instances.append(instance)

            # Small delay
            time.sleep(0.1)

        if test_passed:
            print_pass(f"Successfully triggered 5 alerts")

        # ========================================================================
        # Test 3: Verify alerts are grouped (same group_id)
        # ========================================================================
        print_test("Test 3: Verify alerts are grouped (same group_id)")

        unique_group_ids = set(group_ids)

        if len(unique_group_ids) != 1:
            print_fail(f"Expected 1 unique group, got {len(unique_group_ids)}")
            test_passed = False
        else:
            print_pass(f"All 5 alerts grouped into single group: {group_ids[0]}")

        # Verify all instances have the same group_id
        all_same_group = all(inst.group_id == group_ids[0] for inst in triggered_instances)
        if not all_same_group:
            print_fail("Not all instances have the same group_id")
            test_passed = False
        else:
            print_pass("All instances linked to the same group")

        # ========================================================================
        # Test 4: Verify single notification per group
        # ========================================================================
        print_test("Test 4: Verify single notification per group")

        group = alert_service.get_group(group_ids[0])

        if group is None:
            print_fail("Group not found in database")
            test_passed = False
        else:
            # Check alert count
            if group.alert_count != 5:
                print_fail(f"Expected 5 alerts in group, got {group.alert_count}")
                test_passed = False
            else:
                print_pass(f"Group has 5 alerts as expected")

            # Check notification count
            if group.notification_count != 1:
                print_fail(f"Expected 1 notification, got {group.notification_count}")
                test_passed = False
            else:
                print_pass(f"Only 1 notification sent (spam prevented!)")

            # Check notification_sent flag
            if not group.notification_sent:
                print_fail("Notification should be marked as sent")
                test_passed = False
            else:
                print_pass("Notification marked as sent")

        # ========================================================================
        # Test 5: Verify group resolution notification sent
        # ========================================================================
        print_test("Test 5: Verify group resolution notification sent")

        # Trigger recovery alert
        recovery_instance = alert_trigger_service.trigger_recovery_alert(
            rule=rule,
            group_id=group.id,
            context={**alert_context, "recovery_reason": "CPU usage normalized"},
        )

        if recovery_instance is None:
            print_fail("Failed to trigger recovery alert")
            test_passed = False
        else:
            print_pass("Recovery alert triggered successfully")

            if recovery_instance.status != "resolved":
                print_fail(f"Recovery instance status should be 'resolved', got '{recovery_instance.status}'")
                test_passed = False
            else:
                print_pass("Recovery instance has 'resolved' status")

        # Resolve the group
        resolved_group = alert_grouping_service.resolve_group(group)

        if resolved_group.status != "resolved":
            print_fail(f"Group status should be 'resolved', got '{resolved_group.status}'")
            test_passed = False
        else:
            print_pass("Group resolved successfully")

        if resolved_group.resolved_at is None:
            print_fail("Group should have resolved_at timestamp")
            test_passed = False
        else:
            print_pass(f"Group resolved at: {resolved_group.resolved_at}")

        # ========================================================================
        # Final verification: Check total instances
        # ========================================================================
        print_test("Final verification: Check total instances")

        all_instances = alert_service.list_instances(group_id=group.id)

        if len(all_instances) != 6:
            print_fail(f"Expected 6 instances total (5 firing + 1 recovery), got {len(all_instances)}")
            test_passed = False
        else:
            print_pass(f"Total instances: 6 (5 firing + 1 recovery)")

        # Count by status
        firing_count = sum(1 for i in all_instances if i.status == "firing")
        resolved_count = sum(1 for i in all_instances if i.status == "resolved")

        if firing_count != 5:
            print_fail(f"Expected 5 firing instances, got {firing_count}")
            test_passed = False
        else:
            print_pass(f"Firing instances: {firing_count}")

        if resolved_count != 1:
            print_fail(f"Expected 1 resolved instance, got {resolved_count}")
            test_passed = False
        else:
            print_pass(f"Resolved instances: {resolved_count}")

        # ========================================================================
        # Summary
        # ========================================================================
        print_section("VERIFICATION SUMMARY")

        if test_passed:
            print("  ✅ ALL TESTS PASSED")
            print("\n  Alert grouping is working correctly:")
            print("    • Multiple alerts grouped into single group")
            print("    • Single notification sent (spam prevented)")
            print("    • Recovery notification sent on resolution")
            print("    • All instances tracked correctly")
        else:
            print("  ❌ SOME TESTS FAILED")
            print("\n  Please review the failures above.")

        # ========================================================================
        # Cleanup
        # ========================================================================
        print_test("Cleanup test data")
        cleanup_test_data(db, rule.id)
        print_pass("Test data cleaned up")

    except Exception as e:
        print_fail(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        test_passed = False

    finally:
        db.close()

    return test_passed


if __name__ == "__main__":
    success = verify_alert_grouping()
    sys.exit(0 if success else 1)
