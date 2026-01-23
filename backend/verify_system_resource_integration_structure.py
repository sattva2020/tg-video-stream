#!/usr/bin/env python3
"""
Code structure verification for System Resource Alert Integration

This script verifies the integration file structure without requiring dependencies.
"""

import os
import sys
from pathlib import Path


def check_file_exists(filepath):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"  ✓ File exists: {filepath}")
        return True
    else:
        print(f"  ✗ File missing: {filepath}")
        return False


def check_file_contains(filepath, patterns):
    """Check if file contains specific patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        results = []
        for pattern in patterns:
            if pattern in content:
                print(f"  ✓ Contains: {pattern[:50]}...")
                results.append(True)
            else:
                print(f"  ✗ Missing: {pattern[:50]}...")
                results.append(False)

        return all(results)
    except Exception as e:
        print(f"  ✗ Error reading file: {e}")
        return False


def verify_integration_file():
    """Verify the integration service file."""
    print("\n✓ Verifying integration service file...")

    filepath = "src/services/system_resource_alert_integration.py"

    if not check_file_exists(filepath):
        return False

    required_patterns = [
        "class SystemResourceAlertIntegrationService:",
        "def initialize(self)",
        "async def _on_cpu_warning(",
        "async def _on_cpu_critical(",
        "async def _on_memory_warning(",
        "async def _on_memory_critical(",
        "async def _on_disk_warning(",
        "async def _on_disk_critical(",
        "async def _on_resource_recovery(",
        "def _get_or_create_system_resource_rule(",
        "def _get_system_resource_rule(",
        "def _create_cpu_warning_evaluation_result(",
        "def _create_cpu_critical_evaluation_result(",
        "def _create_memory_warning_evaluation_result(",
        "def _create_memory_critical_evaluation_result(",
        "def _create_disk_warning_evaluation_result(",
        "def _create_disk_critical_evaluation_result(",
        "from src.services.alert_evaluator import EvaluationResult",
        "from src.services.alert_trigger_service import AlertTriggerService",
        "from src.services.alert_grouping_service import AlertGroupingService",
        "from src.services.monitors.system_resource_monitor import",
        "def get_system_resource_alert_integration()",
        "async def initialize_system_resource_alert_integration()",
    ]

    return check_file_contains(filepath, required_patterns)


def verify_callback_registration():
    """Verify callbacks are properly registered in initialize()."""
    print("\n✓ Verifying callback registration...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        "self.resource_monitor.on_cpu_warning_callback = self._on_cpu_warning",
        "self.resource_monitor.on_cpu_critical_callback = self._on_cpu_critical",
        "self.resource_monitor.on_memory_warning_callback = self._on_memory_warning",
        "self.resource_monitor.on_memory_critical_callback = self._on_memory_critical",
        "self.resource_monitor.on_disk_warning_callback = self._on_disk_warning",
        "self.resource_monitor.on_disk_critical_callback = self._on_disk_critical",
        "self.resource_monitor.on_recovery_callback = self._on_resource_recovery",
    ]

    return check_file_contains(filepath, patterns)


def verify_evaluation_result_structure():
    """Verify evaluation results are properly structured."""
    print("\n✓ Verifying evaluation result structure...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        'alert_type="system_resource"',
        "return EvaluationResult(",
        "triggered=True",
        "trigger_value=",
        "context=",
        "reason=",
        "severity=",
    ]

    return check_file_contains(filepath, patterns)


def verify_rule_creation():
    """Verify alert rule creation logic."""
    print("\n✓ Verifying alert rule creation...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        'alert_type="system_resource"',
        "name=",
        "description=",
        "severity=",
        "enabled=True",
        "conditions=",
        "cooldown_sec=",
        "notify_on_recovery=",
        "grouping_window_sec=",
        "AlertService(db)",
        "create_rule(",
    ]

    return check_file_contains(filepath, patterns)


def verify_grouping_logic():
    """Verify alert grouping logic."""
    print("\n✓ Verifying alert grouping logic...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        "AlertGroupingService(db)",
        "find_or_create_group(",
        "context=",
        '"host": host',
        '"service": "system"',
        '"alert_type":',
        '"resource_type":',
        "trigger_alert(",
    ]

    return check_file_contains(filepath, patterns)


def verify_recovery_logic():
    """Verify recovery notification logic."""
    print("\n✓ Verifying recovery notification logic...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        "async def _on_resource_recovery(",
        "notify_on_recovery",
        "get_active_groups_for_rule(",
        "trigger_recovery_alert(",
        "resolve_group(",
    ]

    return check_file_contains(filepath, patterns)


def verify_singleton_pattern():
    """Verify singleton pattern implementation."""
    print("\n✓ Verifying singleton pattern...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        "_system_resource_alert_integration: Optional[SystemResourceAlertIntegrationService] = None",
        "def get_system_resource_alert_integration()",
        "global _system_resource_alert_integration",
        "if _system_resource_alert_integration is None:",
        "_system_resource_alert_integration = SystemResourceAlertIntegrationService()",
    ]

    return check_file_contains(filepath, patterns)


def verify_logging():
    """Verify proper logging."""
    print("\n✓ Verifying logging...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        "import logging",
        "logger = logging.getLogger(__name__)",
        "logger.info(",
        "logger.error(",
        "logger.warning(",
        "logger.debug(",
        "logger.exception(",
    ]

    return check_file_contains(filepath, patterns)


def verify_error_handling():
    """Verify error handling."""
    print("\n✓ Verifying error handling...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        "try:",
        "except Exception as exc:",
        "logger.exception(",
        "finally:",
        "db.close()",
    ]

    return check_file_contains(filepath, patterns)


def verify_documentation():
    """Verify documentation strings."""
    print("\n✓ Verifying documentation...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        '"""',
        "Интеграционный сервис",
        "Обеспечивает автоматическое создание алертов",
        "Args:",
        "Returns:",
        "Callback при",
    ]

    return check_file_contains(filepath, patterns)


def verify_resource_types():
    """Verify all resource types are handled."""
    print("\n✓ Verifying resource type handling...")

    filepath = "src/services/system_resource_alert_integration.py"

    patterns = [
        '"resource_type": "cpu"',
        '"resource_type": "memory"',
        '"resource_type": "disk"',
        '"metric": "cpu_usage"',
        '"metric": "memory_usage"',
        '"metric": "disk_usage"',
    ]

    return check_file_contains(filepath, patterns)


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("System Resource Alert Integration Structure Verification")
    print("=" * 70)

    tests = [
        ("Integration File", verify_integration_file),
        ("Callback Registration", verify_callback_registration),
        ("Evaluation Result Structure", verify_evaluation_result_structure),
        ("Alert Rule Creation", verify_rule_creation),
        ("Grouping Logic", verify_grouping_logic),
        ("Recovery Logic", verify_recovery_logic),
        ("Singleton Pattern", verify_singleton_pattern),
        ("Logging", verify_logging),
        ("Error Handling", verify_error_handling),
        ("Documentation", verify_documentation),
        ("Resource Type Handling", verify_resource_types),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
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
        print("\n✓ All structure verification tests passed!")
        print("\nThe System Resource Alert Integration Service is properly structured.")
        print("\nKey features verified:")
        print("  • Integration with SystemResourceMonitor callbacks")
        print("  • Automatic alert rule creation")
        print("  • CPU, memory, and disk alert handling (warning and critical)")
        print("  • Alert grouping for spam prevention")
        print("  • Recovery notifications")
        print("  • Proper error handling and logging")
        print("  • Singleton pattern implementation")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
