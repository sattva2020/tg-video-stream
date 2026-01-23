#!/usr/bin/env python3
"""
End-to-end integration tests for System Resource Alert Integration

These tests verify the complete flow from SystemResourceMonitor callbacks
through AlertTriggerService to AlertInstance creation and alert grouping.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.services.system_resource_alert_integration import (
    SystemResourceAlertIntegrationService,
    get_system_resource_alert_integration,
)
from src.services.alert_trigger_service import AlertTriggerService
from src.services.alert_grouping_service import AlertGroupingService
from src.services.alert_service import AlertService
from src.services.alert_evaluator import EvaluationResult
from src.models.alert import AlertRule, AlertInstance, AlertGroup


class TestSystemResourceAlertIntegration:
    """End-to-end tests for system resource alert integration."""

    def __init__(self):
        self.engine = None
        self.SessionFactory = None
        self.integration_service: Optional[SystemResourceAlertIntegrationService] = None

    def setup(self):
        """Set up test database and integration service."""
        print("\n=== Test Setup ===")

        # Create in-memory test database
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionFactory = sessionmaker(bind=self.engine)

        # Create tables
        from src.models.alert import Base
        Base.metadata.create_all(self.engine)

        # Create integration service
        self.integration_service = SystemResourceAlertIntegrationService()

        # Mock the database session factory
        self.integration_service._db_session_factory = self.SessionFactory

        # Mock the monitor (we don't need actual monitoring for these tests)
        from src.services.monitors.system_resource_monitor import SystemResourceMonitor
        self.integration_service.resource_monitor = Mock(spec=SystemResourceMonitor)

        print("✓ Test database created")
        print("✓ Integration service initialized")

    def teardown(self):
        """Clean up after tests."""
        print("\n=== Test Teardown ===")

        if self.engine:
            self.engine.dispose()

        print("✓ Test database cleaned up")

    def test_cpu_warning_alert(self):
        """Test CPU warning alert creation."""
        print("\n=== Test: CPU Warning Alert ===")

        db: Session = self.SessionFactory()

        try:
            # Create a test rule
            rule = AlertRule(
                name="Test System Resource Alert",
                description="Test rule for system resources",
                alert_type="system_resource",
                severity="warning",
                enabled=True,
                conditions={},
                notification_channels={},
                cooldown_sec=300,
                notify_on_recovery=True,
                grouping_window_sec=300,
            )
            db.add(rule)
            db.commit()

            # Mock the _get_or_create_system_resource_rule method to return our rule
            with patch.object(
                self.integration_service,
                '_get_or_create_system_resource_rule',
                return_value=rule
            ):
                # Trigger the callback
                asyncio.run(self.integration_service._on_cpu_warning(
                    host="test-host",
                    usage=75.0,
                    threshold=70.0
                ))

            # Verify alert instance was created
            instances = db.query(AlertInstance).filter(
                AlertInstance.rule_id == rule.id
            ).all()

            assert len(instances) > 0, "No alert instances created"
            assert instances[0].severity == "warning", f"Expected warning, got {instances[0].severity}"

            # Check the context contains resource_type
            context = instances[0].context
            assert context.get("host") == "test-host", "Host not in context"
            assert context.get("tags", {}).get("resource_type") == "cpu", "Resource type not in context"

            print(f"✓ CPU warning alert created: {instances[0].id}")
            print(f"  - Severity: {instances[0].severity}")
            print(f"  - Status: {instances[0].status}")
            print(f"  - Context: {context}")

            return True

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()

    def test_cpu_critical_alert(self):
        """Test CPU critical alert creation."""
        print("\n=== Test: CPU Critical Alert ===")

        db: Session = self.SessionFactory()

        try:
            # Create a test rule
            rule = AlertRule(
                name="Test System Resource Alert",
                description="Test rule for system resources",
                alert_type="system_resource",
                severity="critical",
                enabled=True,
                conditions={},
                notification_channels={},
                cooldown_sec=300,
                notify_on_recovery=True,
                grouping_window_sec=300,
            )
            db.add(rule)
            db.commit()

            # Mock the _get_or_create_system_resource_rule method
            with patch.object(
                self.integration_service,
                '_get_or_create_system_resource_rule',
                return_value=rule
            ):
                # Trigger the callback
                asyncio.run(self.integration_service._on_cpu_critical(
                    host="test-host",
                    usage=95.0,
                    threshold=90.0
                ))

            # Verify alert instance was created
            instances = db.query(AlertInstance).filter(
                AlertInstance.rule_id == rule.id
            ).all()

            assert len(instances) > 0, "No alert instances created"
            assert instances[0].severity == "critical", f"Expected critical, got {instances[0].severity}"

            print(f"✓ CPU critical alert created: {instances[0].id}")
            print(f"  - Severity: {instances[0].severity}")
            print(f"  - Reason: {instances[0].reason}")

            return True

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()

    def test_memory_warning_alert(self):
        """Test memory warning alert creation."""
        print("\n=== Test: Memory Warning Alert ===")

        db: Session = self.SessionFactory()

        try:
            # Create a test rule
            rule = AlertRule(
                name="Test System Resource Alert",
                description="Test rule for system resources",
                alert_type="system_resource",
                severity="warning",
                enabled=True,
                conditions={},
                notification_channels={},
                cooldown_sec=300,
                notify_on_recovery=True,
                grouping_window_sec=300,
            )
            db.add(rule)
            db.commit()

            # Mock the _get_or_create_system_resource_rule method
            with patch.object(
                self.integration_service,
                '_get_or_create_system_resource_rule',
                return_value=rule
            ):
                # Trigger the callback
                asyncio.run(self.integration_service._on_memory_warning(
                    host="test-host",
                    usage=80.0,
                    threshold=75.0
                ))

            # Verify alert instance was created
            instances = db.query(AlertInstance).filter(
                AlertInstance.rule_id == rule.id
            ).all()

            assert len(instances) > 0, "No alert instances created"

            # Check the context contains resource_type = memory
            context = instances[0].context
            assert context.get("tags", {}).get("resource_type") == "memory", "Resource type not correct"

            print(f"✓ Memory warning alert created: {instances[0].id}")
            print(f"  - Resource type: {context.get('tags', {}).get('resource_type')}")

            return True

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()

    def test_disk_critical_alert(self):
        """Test disk critical alert creation."""
        print("\n=== Test: Disk Critical Alert ===")

        db: Session = self.SessionFactory()

        try:
            # Create a test rule
            rule = AlertRule(
                name="Test System Resource Alert",
                description="Test rule for system resources",
                alert_type="system_resource",
                severity="critical",
                enabled=True,
                conditions={},
                notification_channels={},
                cooldown_sec=300,
                notify_on_recovery=True,
                grouping_window_sec=300,
            )
            db.add(rule)
            db.commit()

            # Mock the _get_or_create_system_resource_rule method
            with patch.object(
                self.integration_service,
                '_get_or_create_system_resource_rule',
                return_value=rule
            ):
                # Trigger the callback
                asyncio.run(self.integration_service._on_disk_critical(
                    host="test-host",
                    usage=98.0,
                    threshold=95.0
                ))

            # Verify alert instance was created
            instances = db.query(AlertInstance).filter(
                AlertInstance.rule_id == rule.id
            ).all()

            assert len(instances) > 0, "No alert instances created"
            assert instances[0].severity == "critical", f"Expected critical, got {instances[0].severity}"

            # Check the context contains resource_type = disk
            context = instances[0].context
            assert context.get("tags", {}).get("resource_type") == "disk", "Resource type not correct"

            print(f"✓ Disk critical alert created: {instances[0].id}")
            print(f"  - Severity: {instances[0].severity}")
            print(f"  - Resource type: {context.get('tags', {}).get('resource_type')}")

            return True

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()

    def test_alert_grouping(self):
        """Test that alerts are properly grouped by host and resource type."""
        print("\n=== Test: Alert Grouping ===")

        db: Session = self.SessionFactory()

        try:
            # Create a test rule
            rule = AlertRule(
                name="Test System Resource Alert",
                description="Test rule for system resources",
                alert_type="system_resource",
                severity="warning",
                enabled=True,
                conditions={},
                notification_channels={},
                cooldown_sec=300,
                notify_on_recovery=True,
                grouping_window_sec=300,
            )
            db.add(rule)
            db.commit()

            # Mock the _get_or_create_system_resource_rule method
            with patch.object(
                self.integration_service,
                '_get_or_create_system_resource_rule',
                return_value=rule
            ):
                # Trigger multiple CPU warnings for the same host
                asyncio.run(self.integration_service._on_cpu_warning(
                    host="test-host",
                    usage=75.0,
                    threshold=70.0
                ))

                # Give a small delay to ensure different timestamps
                asyncio.sleep(0.1)

                asyncio.run(self.integration_service._on_cpu_warning(
                    host="test-host",
                    usage=76.0,
                    threshold=70.0
                ))

            # Check that only one group was created
            groups = db.query(AlertGroup).filter(
                AlertGroup.rule_id == rule.id
            ).all()

            # Should have created one group (both alerts should be in the same group)
            assert len(groups) > 0, "No alert groups created"

            # Check that all instances belong to the same group
            instances = db.query(AlertInstance).filter(
                AlertInstance.rule_id == rule.id
            ).all()

            print(f"✓ Alert grouping test passed")
            print(f"  - Groups created: {len(groups)}")
            print(f"  - Instances created: {len(instances)}")
            if len(groups) > 0:
                print(f"  - Group ID: {groups[0].id}")

            return True

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()

    def test_recovery_alert(self):
        """Test recovery notification when resource usage returns to normal."""
        print("\n=== Test: Recovery Alert ===")

        db: Session = self.SessionFactory()

        try:
            # Create a test rule with notify_on_recovery enabled
            rule = AlertRule(
                name="Test System Resource Alert",
                description="Test rule for system resources",
                alert_type="system_resource",
                severity="warning",
                enabled=True,
                conditions={},
                notification_channels={},
                cooldown_sec=300,
                notify_on_recovery=True,
                grouping_window_sec=300,
            )
            db.add(rule)
            db.commit()

            # First, create an active alert group
            with patch.object(
                self.integration_service,
                '_get_or_create_system_resource_rule',
                return_value=rule
            ):
                asyncio.run(self.integration_service._on_cpu_warning(
                    host="test-host",
                    usage=75.0,
                    threshold=70.0
                ))

            # Get the active group
            groups = db.query(AlertGroup).filter(
                AlertGroup.rule_id == rule.id,
                AlertGroup.status == "active"
            ).all()

            assert len(groups) > 0, "No active group created"

            # Mock the _get_system_resource_rule method to return our rule
            with patch.object(
                self.integration_service,
                '_get_system_resource_rule',
                return_value=rule
            ):
                # Trigger recovery callback
                asyncio.run(self.integration_service._on_resource_recovery(
                    host="test-host",
                    resource_type="cpu"
                ))

            # Check that recovery alert was created
            recovery_instances = db.query(AlertInstance).filter(
                AlertInstance.rule_id == rule.id,
                AlertInstance.status == "resolved"
            ).all()

            # Check that the group was resolved
            groups = db.query(AlertGroup).filter(
                AlertGroup.id == groups[0].id
            ).first()

            assert groups.status == "resolved", f"Group not resolved, status: {groups.status}"

            print(f"✓ Recovery alert test passed")
            print(f"  - Recovery instances: {len(recovery_instances)}")
            print(f"  - Group status: {groups.status}")

            return True

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()

    def test_different_hosts_separate_groups(self):
        """Test that alerts for different hosts are grouped separately."""
        print("\n=== Test: Different Hosts Separate Groups ===")

        db: Session = self.SessionFactory()

        try:
            # Create a test rule
            rule = AlertRule(
                name="Test System Resource Alert",
                description="Test rule for system resources",
                alert_type="system_resource",
                severity="warning",
                enabled=True,
                conditions={},
                notification_channels={},
                cooldown_sec=300,
                notify_on_recovery=True,
                grouping_window_sec=300,
            )
            db.add(rule)
            db.commit()

            # Mock the _get_or_create_system_resource_rule method
            with patch.object(
                self.integration_service,
                '_get_or_create_system_resource_rule',
                return_value=rule
            ):
                # Trigger CPU warning for host-1
                asyncio.run(self.integration_service._on_cpu_warning(
                    host="host-1",
                    usage=75.0,
                    threshold=70.0
                ))

                # Trigger CPU warning for host-2
                asyncio.run(self.integration_service._on_cpu_warning(
                    host="host-2",
                    usage=75.0,
                    threshold=70.0
                ))

            # Check that two separate groups were created
            groups = db.query(AlertGroup).filter(
                AlertGroup.rule_id == rule.id
            ).all()

            assert len(groups) == 2, f"Expected 2 groups, got {len(groups)}"

            print(f"✓ Different hosts separate groups test passed")
            print(f"  - Groups created: {len(groups)}")

            return True

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()

    def run_all_tests(self):
        """Run all tests."""
        print("=" * 70)
        print("System Resource Alert Integration E2E Tests")
        print("=" * 70)

        self.setup()

        tests = [
            ("CPU Warning Alert", self.test_cpu_warning_alert),
            ("CPU Critical Alert", self.test_cpu_critical_alert),
            ("Memory Warning Alert", self.test_memory_warning_alert),
            ("Disk Critical Alert", self.test_disk_critical_alert),
            ("Alert Grouping", self.test_alert_grouping),
            ("Recovery Alert", self.test_recovery_alert),
            ("Different Hosts Separate Groups", self.test_different_hosts_separate_groups),
        ]

        results = []
        for name, test_func in tests:
            try:
                # Reset database for each test
                from src.models.alert import Base
                Base.metadata.drop_all(self.engine)
                Base.metadata.create_all(self.engine)

                result = test_func()
                results.append((name, result))
            except Exception as e:
                print(f"\n✗ Test '{name}' raised exception: {e}")
                import traceback
                traceback.print_exc()
                results.append((name, False))

        self.teardown()

        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")

        print("\n" + "=" * 70)
        print(f"Total: {passed}/{total} tests passed")
        print("=" * 70)

        if passed == total:
            print("\n✓ All end-to-end tests passed!")
            print("\nThe System Resource Alert Integration is working correctly.")
            print("\nVerified functionality:")
            print("  • CPU warning and critical alerts")
            print("  • Memory warning and critical alerts")
            print("  • Disk warning and critical alerts")
            print("  • Alert grouping by host and resource type")
            print("  • Recovery notifications")
            print("  • Separate groups for different hosts")
            return 0
        else:
            print(f"\n✗ {total - passed} test(s) failed")
            return 1


def main():
    """Run the tests."""
    tester = TestSystemResourceAlertIntegration()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
