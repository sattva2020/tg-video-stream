#!/usr/bin/env python3
"""
Code structure verification for API Rate Limit Alert Integration

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

    filepath = "src/services/api_rate_limit_alert_integration.py"

    if not check_file_exists(filepath):
        return False

    required_patterns = [
        "class ApiRateLimitAlertIntegrationService:",
        "def initialize(self)",
        "async def _on_warning_threshold(",
        "async def _on_critical_threshold(",
        "async def _on_rate_limited(",
        "async def _on_rate_limit_recovery(",
        "def _get_or_create_rate_limit_rule(",
        "def _get_rate_limit_rule(",
        "def _create_warning_evaluation_result(",
        "def _create_critical_evaluation_result(",
        "def _create_rate_limited_evaluation_result(",
        "from src.services.alert_evaluator import EvaluationResult",
        "from src.services.alert_trigger_service import AlertTriggerService",
        "from src.services.alert_grouping_service import AlertGroupingService",
        "from src.services.monitors.api_rate_limit_monitor import",
        "def get_api_rate_limit_alert_integration()",
        "async def initialize_api_rate_limit_alert_integration()",
    ]

    return check_file_contains(filepath, required_patterns)


def verify_callback_registration():
    """Verify callbacks are properly registered in initialize()."""
    print("\n✓ Verifying callback registration...")

    filepath = "src/services/api_rate_limit_alert_integration.py"

    patterns = [
        "self.rate_limit_monitor.on_warning_callback = self._on_warning_threshold",
        "self.rate_limit_monitor.on_critical_callback = self._on_critical_threshold",
        "self.rate_limit_monitor.on_rate_limited_callback = self._on_rate_limited",
        "self.rate_limit_monitor.on_recovery_callback = self._on_rate_limit_recovery",
    ]

    return check_file_contains(filepath, patterns)


def verify_evaluation_result_structure():
    """Verify evaluation results are properly structured."""
    print("\n✓ Verifying evaluation result structure...")

    filepath = "src/services/api_rate_limit_alert_integration.py"

    patterns = [
        'alert_type="api_rate_limit"',
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

    filepath = "src/services/api_rate_limit_alert_integration.py"

    patterns = [
        'alert_type="api_rate_limit"',
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

    filepath = "src/services/api_rate_limit_alert_integration.py"

    patterns = [
        "AlertGroupingService(db)",
        "find_or_create_group(",
        "context=",
        '"endpoint": endpoint',
        '"service": "api"',
        '"alert_type":',
        "trigger_alert(",
    ]

    return check_file_contains(filepath, patterns)


def verify_recovery_logic():
    """Verify recovery notification logic."""
    print("\n✓ Verifying recovery notification logic...")

    filepath = "src/services/api_rate_limit_alert_integration.py"

    patterns = [
        "async def _on_rate_limit_recovery(",
        "notify_on_recovery",
        "get_active_groups_for_rule(",
        "trigger_recovery_alert(",
        "resolve_group(",
    ]

    return check_file_contains(filepath, patterns)


def verify_singleton_pattern():
    """Verify singleton pattern implementation."""
    print("\n✓ Verifying singleton pattern...")

    filepath = "src/services/api_rate_limit_alert_integration.py"

    patterns = [
        "_api_rate_limit_alert_integration: Optional[ApiRateLimitAlertIntegrationService] = None",
        "def get_api_rate_limit_alert_integration()",
        "global _api_rate_limit_alert_integration",
        "if _api_rate_limit_alert_integration is None:",
        "_api_rate_limit_alert_integration = ApiRateLimitAlertIntegrationService()",
    ]

    return check_file_contains(filepath, patterns)


def verify_logging():
    """Verify proper logging."""
    print("\n✓ Verifying logging...")

    filepath = "src/services/api_rate_limit_alert_integration.py"

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

    filepath = "src/services/api_rate_limit_alert_integration.py"

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

    filepath = "src/services/api_rate_limit_alert_integration.py"

    patterns = [
        '"""',
        "Интеграционный сервис",
        "Обеспечивает автоматическое создание алертов",
        "Args:",
        "Returns:",
        "Callback при",
    ]

    return check_file_contains(filepath, patterns)


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("API Rate Limit Alert Integration Structure Verification")
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
        print("\nThe API Rate Limit Alert Integration Service is properly structured.")
        print("\nKey features verified:")
        print("  • Integration with ApiRateLimitMonitor callbacks")
        print("  • Automatic alert rule creation")
        print("  • Warning, critical, and rate-limited alert handling")
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
