"""
End-to-end verification test for alert grouping to prevent notification spam.

This test verifies:
1. Alert grouping works correctly
2. Single notification per group (no spam)
3. Group resolution notifications are sent
"""
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List

import pytest
from sqlalchemy.orm import Session

from src.models.alert import AlertGroup, AlertInstance, AlertRule
from src.schemas.alerts import AlertRuleCreate
from src.services.alert_service import AlertService
from src.services.alert_evaluator import AlertEvaluator, EvaluationResult
from src.services.alert_trigger_service import AlertTriggerService
from src.services.alert_grouping_service import AlertGroupingService


class TestAlertGroupingVerification:
    """End-to-end verification tests for alert grouping."""

    @pytest.fixture
    def alert_service(self, db: Session):
        """Create alert service instance."""
        return AlertService(db)

    @pytest.fixture
    def alert_evaluator(self, db: Session):
        """Create alert evaluator instance."""
        return AlertEvaluator(db)

    @pytest.fixture
    def alert_trigger_service(self, db: Session):
        """Create alert trigger service instance."""
        return AlertTriggerService(db)

    @pytest.fixture
    def alert_grouping_service(self, db: Session):
        """Create alert grouping service instance."""
        return AlertGroupingService(db)

    def test_alert_grouping_prevents_notification_spam(
        self,
        db: Session,
        alert_service: AlertService,
        alert_evaluator: AlertEvaluator,
        alert_trigger_service: AlertTriggerService,
        alert_grouping_service: AlertGroupingService,
    ):
        """
        E2E Test: Verify alert grouping prevents notification spam.

        Steps:
        1. Create alert rule with short interval
        2. Trigger condition that persists (5 times)
        3. Verify alerts are grouped (same group_id)
        4. Verify single notification per group
        5. Verify group resolution notification sent
        """
        # Step 1: Create alert rule with short interval
        rule_data = AlertRuleCreate(
            name="High CPU Usage Test",
            description="Test rule for alert grouping verification",
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
            cooldown_sec=60,  # Short cooldown for testing
            notification_channels={
                "telegram": [123456789],
            },
            notify_on_recovery=True,
            auto_resolve=False,
            escalation_enabled=False,
            alert_grouping_window_sec=300,  # 5 minute grouping window
        )

        rule = alert_service.create_rule(rule_data)
        assert rule is not None
        assert rule.enabled is True

        # Step 2: Trigger condition that persists (5 times)
        alert_context = {
            "host": "test-server-1",
            "service": "api",
            "tags": {
                "environment": "testing",
                "region": "us-east-1",
            },
        }

        triggered_instances: List[AlertInstance] = []
        group_ids: List[uuid.UUID] = []

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

            assert group is not None, f"Failed to create/find group for iteration {i}"

            # Track group_id
            group_ids.append(group.id)

            # Check if notification should be sent
            should_notify = alert_grouping_service.should_send_notification(
                group=group,
                is_new_group=is_new_group,
                notification_interval_sec=300,  # 5 minute interval
            )

            # Trigger alert
            instance = alert_trigger_service.trigger_alert(
                result=result,
                group_id=group.id,
            )

            assert instance is not None, f"Failed to trigger alert for iteration {i}"
            assert instance.group_id == group.id, f"Instance not linked to group in iteration {i}"

            # Add alert to group
            alert_grouping_service.add_alert_to_group(
                instance=instance,
                group=group,
                send_notification=should_notify,
            )

            # Mark notification as sent if needed
            if should_notify:
                alert_grouping_service.mark_notification_sent(group)

            triggered_instances.append(instance)

            # Small delay to simulate time passing
            time.sleep(0.1)

        # Step 3: Verify alerts are grouped (same group_id)
        unique_group_ids = set(group_ids)
        assert len(unique_group_ids) == 1, f"Expected 1 unique group, got {len(unique_group_ids)}"
        assert group_ids[0] == group_ids[-1], "All alerts should be in the same group"

        # Verify all instances have the same group_id
        for instance in triggered_instances:
            assert instance.group_id == group_ids[0], f"Instance {instance.id} has wrong group_id"

        # Step 4: Verify single notification per group
        group = alert_service.get_group(group_ids[0])
        assert group is not None, "Group not found"

        # Group should have 5 alerts
        assert group.alert_count == 5, f"Expected 5 alerts in group, got {group.alert_count}"

        # Should have only 1 notification (first alert in group)
        assert group.notification_count == 1, f"Expected 1 notification, got {group.notification_count}"
        assert group.notification_sent is True, "Notification should be marked as sent"

        # Verify all instances are linked to the group
        group_instances = alert_service.list_instances(group_id=group.id)
        assert len(group_instances) == 5, f"Expected 5 instances in group, got {len(group_instances)}"

        # Step 5: Verify group resolution notification sent
        # Trigger recovery alert
        recovery_instance = alert_trigger_service.trigger_recovery_alert(
            rule=rule,
            group_id=group.id,
            context={**alert_context, "recovery_reason": "CPU usage normalized"},
        )

        assert recovery_instance is not None, "Failed to trigger recovery alert"
        assert recovery_instance.status == "resolved", "Recovery instance should be resolved"

        # Resolve the group
        resolved_group = alert_grouping_service.resolve_group(group)
        assert resolved_group.status == "resolved", "Group should be resolved"
        assert resolved_group.resolved_at is not None, "Group should have resolved_at timestamp"

        # Verify final state
        final_group = alert_service.get_group(group.id)
        assert final_group.status == "resolved", "Group status should be resolved in DB"

        # Verify we have 6 instances total (5 firing + 1 recovery)
        all_instances = alert_service.list_instances(group_id=group.id)
        assert len(all_instances) == 6, f"Expected 6 instances total, got {len(all_instances)}"

        # Count by status
        firing_count = sum(1 for i in all_instances if i.status == "firing")
        resolved_count = sum(1 for i in all_instances if i.status == "resolved")

        assert firing_count == 5, f"Expected 5 firing instances, got {firing_count}"
        assert resolved_count == 1, f"Expected 1 resolved instance, got {resolved_count}"

    def test_multiple_groups_for_different_contexts(
        self,
        db: Session,
        alert_service: AlertService,
        alert_evaluator: AlertEvaluator,
        alert_trigger_service: AlertTriggerService,
        alert_grouping_service: AlertGroupingService,
    ):
        """
        Test that different contexts create different groups.

        Verifies that alerts with different hosts/services are grouped separately.
        """
        # Create rule
        rule_data = AlertRuleCreate(
            name="High Memory Usage Test",
            description="Test rule for multiple groups",
            alert_type="system_resource",
            severity="warning",
            enabled=True,
            conditions={
                "metric": "memory_usage",
                "operator": "gt",
                "threshold": 80,
            },
            cooldown_sec=60,
            notification_channels={"telegram": [123456789]},
            notify_on_recovery=False,
        )

        rule = alert_service.create_rule(rule_data)

        # Trigger alerts for different hosts
        hosts = ["server-1", "server-2", "server-3"]
        group_ids = []

        for host in hosts:
            context = {
                "host": host,
                "service": "api",
                "tags": {"environment": "testing"},
            }

            result = EvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                alert_type=rule.alert_type,
                severity=rule.severity,
                triggered=True,
                reason=f"Memory usage is 85% on {host}",
                trigger_value={
                    "metric": "memory_usage",
                    "current_value": 85,
                    "threshold": 80,
                    "operator": "gt",
                },
                context=context,
            )

            group, _ = alert_grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type=rule.alert_type,
                severity=rule.severity,
            )

            group_ids.append(group.id)

            instance = alert_trigger_service.trigger_alert(result=result, group_id=group.id)
            alert_grouping_service.add_alert_to_group(instance, group)

        # Verify we have 3 different groups (one per host)
        unique_group_ids = set(group_ids)
        assert len(unique_group_ids) == 3, f"Expected 3 unique groups, got {len(unique_group_ids)}"

        # Verify each group has 1 alert
        for group_id in unique_group_ids:
            group = alert_service.get_group(group_id)
            assert group.alert_count == 1, f"Group {group_id} should have 1 alert"
            assert group.notification_count == 1, f"Group {group_id} should have 1 notification"

    def test_severity_escalation_triggers_notification(
        self,
        db: Session,
        alert_service: AlertService,
        alert_trigger_service: AlertTriggerService,
        alert_grouping_service: AlertGroupingService,
    ):
        """
        Test that severity escalation triggers new notification.

        Verifies that warning -> critical escalation sends new notification.
        """
        # Create rule
        rule_data = AlertRuleCreate(
            name="Disk Usage Escalation Test",
            description="Test rule for severity escalation",
            alert_type="system_resource",
            severity="warning",
            enabled=True,
            conditions={
                "metric": "disk_usage",
                "operator": "gt",
                "threshold": 80,
            },
            cooldown_sec=60,
            notification_channels={"telegram": [123456789]},
            notify_on_recovery=False,
        )

        rule = alert_service.create_rule(rule_data)

        context = {
            "host": "server-1",
            "service": "storage",
        }

        # First alert: warning severity (85% disk usage)
        warning_result = EvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type=rule.alert_type,
            severity="warning",
            triggered=True,
            reason="Disk usage is 85%",
            trigger_value={
                "metric": "disk_usage",
                "current_value": 85,
                "threshold": 80,
                "operator": "gt",
            },
            context=context,
        )

        group, is_new_group = alert_grouping_service.find_or_create_group(
            rule=rule,
            context=context,
            alert_type=rule.alert_type,
            severity="warning",
        )

        warning_instance = alert_trigger_service.trigger_alert(
            result=warning_result,
            group_id=group.id,
        )

        should_notify_warning = alert_grouping_service.should_send_notification(
            group=group,
            is_new_group=is_new_group,
        )
        alert_grouping_service.add_alert_to_group(warning_instance, group)

        if should_notify_warning:
            alert_grouping_service.mark_notification_sent(group)

        # Verify first notification sent
        group = alert_service.get_group(group.id)
        assert group.notification_count == 1, "Should have 1 notification after warning"
        assert group.severity == "warning", "Group severity should be warning"

        # Second alert: critical severity (95% disk usage)
        critical_result = EvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type=rule.alert_type,
            severity="critical",
            triggered=True,
            reason="Disk usage is 95% - CRITICAL",
            trigger_value={
                "metric": "disk_usage",
                "current_value": 95,
                "threshold": 90,
                "operator": "gt",
            },
            context=context,
        )

        critical_instance = alert_trigger_service.trigger_alert(
            result=critical_result,
            group_id=group.id,
        )

        # Add critical alert to group (should escalate severity)
        alert_grouping_service.add_alert_to_group(critical_instance, group)

        # Check if escalation triggers notification
        should_notify_critical = alert_grouping_service.should_send_notification(
            group=group,
            is_new_group=False,
        )

        assert should_notify_critical is True, "Severity escalation should trigger notification"

        if should_notify_critical:
            alert_grouping_service.mark_notification_sent(group)

        # Verify escalation and second notification
        group = alert_service.get_group(group.id)
        assert group.severity == "critical", "Group severity should escalate to critical"
        assert group.notification_count == 2, "Should have 2 notifications after escalation"
        assert group.alert_count == 2, "Should have 2 alerts in group"

    def test_notification_interval_prevents_spam(
        self,
        db: Session,
        alert_service: AlertService,
        alert_trigger_service: AlertTriggerService,
        alert_grouping_service: AlertGroupingService,
    ):
        """
        Test that notification interval prevents spam.

        Verifies that even with multiple alerts, notifications respect the interval.
        """
        # Create rule with 10 second notification interval
        rule_data = AlertRuleCreate(
            name="High Network Traffic Test",
            description="Test rule for notification interval",
            alert_type="system_resource",
            severity="warning",
            enabled=True,
            conditions={
                "metric": "network_traffic",
                "operator": "gt",
                "threshold": 1000,
            },
            cooldown_sec=10,  # Short cooldown
            notification_channels={"telegram": [123456789]},
            notify_on_recovery=False,
        )

        rule = alert_service.create_rule(rule_data)

        context = {
            "host": "server-1",
            "service": "network",
        }

        group = None
        notification_count = 0
        notification_interval_sec = 10

        # Trigger 5 alerts with short delay
        for i in range(5):
            result = EvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                alert_type=rule.alert_type,
                severity="warning",
                triggered=True,
                reason=f"Network traffic is {1500 + i * 100} Mbps",
                trigger_value={
                    "metric": "network_traffic",
                    "current_value": 1500 + i * 100,
                    "threshold": 1000,
                    "operator": "gt",
                },
                context=context,
            )

            if group is None:
                group, is_new_group = alert_grouping_service.find_or_create_group(
                    rule=rule,
                    context=context,
                    alert_type=rule.alert_type,
                    severity="warning",
                )
            else:
                # Find existing group
                group, is_new_group = alert_grouping_service.find_or_create_group(
                    rule=rule,
                    context=context,
                    alert_type=rule.alert_type,
                    severity="warning",
                )

            instance = alert_trigger_service.trigger_alert(result=result, group_id=group.id)

            # Check if notification should be sent
            should_notify = alert_grouping_service.should_send_notification(
                group=group,
                is_new_group=is_new_group,
                notification_interval_sec=notification_interval_sec,
            )

            alert_grouping_service.add_alert_to_group(instance, group)

            if should_notify:
                alert_grouping_service.mark_notification_sent(group)
                notification_count += 1

            # Small delay (less than notification interval)
            time.sleep(0.5)

        # Verify limited notifications despite 5 alerts
        group = alert_service.get_group(group.id)
        assert group.alert_count == 5, "Should have 5 alerts in group"
        assert notification_count == 1, f"Should have only 1 notification, got {notification_count}"
        assert group.notification_count == 1, "Group should show 1 notification sent"
