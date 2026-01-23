#!/usr/bin/env python3
"""
Code structure verification for alert grouping functionality.

This script verifies that all required files, classes, and methods
for alert grouping are present and correctly structured.

Run with: cd backend && python tests/integration/verify_alert_grouping_structure.py
"""
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set


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


def get_classes_from_file(filepath: Path) -> Dict[str, List[str]]:
    """Extract class names and their methods from a Python file."""
    if not filepath.exists():
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=str(filepath))
        except SyntaxError as e:
            print(f"  ⚠ Syntax error in {filepath}: {e}")
            return {}

    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                n.name for n in node.body
                if isinstance(n, ast.FunctionDef) or isinstance(n, ast.AsyncFunctionDef)
            ]
            classes[node.name] = methods

    return classes


def verify_file_exists(filepath: Path, description: str) -> bool:
    """Verify that a file exists."""
    if filepath.exists():
        print_pass(f"{description} exists: {filepath.name}")
        return True
    else:
        print_fail(f"{description} not found: {filepath}")
        return False


def verify_class_has_methods(
    filepath: Path,
    class_name: str,
    required_methods: List[str],
    description: str
) -> bool:
    """Verify that a class has all required methods."""
    classes = get_classes_from_file(filepath)

    if class_name not in classes:
        print_fail(f"Class '{class_name}' not found in {filepath.name}")
        return False

    methods = classes[class_name]
    missing_methods = set(required_methods) - set(methods)

    if not missing_methods:
        print_pass(f"{description} has all required methods: {', '.join(required_methods)}")
        return True
    else:
        print_fail(f"{description} missing methods: {', '.join(missing_methods)}")
        print(f"      Found: {', '.join(methods)}")
        return False


def verify_model_fields(filepath: Path, class_name: str, required_fields: List[str]) -> bool:
    """Verify that a model has required fields (by checking Column assignments)."""
    if not filepath.exists():
        print_fail(f"File not found: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    missing_fields = []
    for field in required_fields:
        # Check if field is defined as Column
        if f"{field} = Column" not in content:
            missing_fields.append(field)

    if not missing_fields:
        print_pass(f"Model '{class_name}' has all required fields")
        return True
    else:
        print_fail(f"Model '{class_name}' missing fields: {', '.join(missing_fields)}")
        return False


def main():
    """Main verification function."""
    print_section("ALERT GROUPING CODE STRUCTURE VERIFICATION")

    backend_dir = Path(__file__).parent.parent.parent
    tests_passed = 0
    tests_failed = 0

    # ========================================================================
    # Verify Files Exist
    # ========================================================================
    print_test("Verify Required Files Exist")

    files_to_check = {
        backend_dir / "src" / "services" / "alert_grouping_service.py": "AlertGroupingService",
        backend_dir / "src" / "services" / "alert_trigger_service.py": "AlertTriggerService",
        backend_dir / "src" / "services" / "alert_service.py": "AlertService",
        backend_dir / "src" / "models" / "alert.py": "Alert models",
        backend_dir / "src" / "schemas" / "alerts.py": "Alert schemas",
        backend_dir / "src" / "api" / "routes" / "alerts_groups.py": "Alert groups API",
        backend_dir / "tests" / "integration" / "test_alert_grouping_verification.py": "Integration tests",
        backend_dir / "tests" / "integration" / "verify_alert_grouping.py": "Verification script",
    }

    for filepath, description in files_to_check.items():
        if verify_file_exists(filepath, description):
            tests_passed += 1
        else:
            tests_failed += 1

    # ========================================================================
    # Verify AlertGroupingService
    # ========================================================================
    print_test("Verify AlertGroupingService Methods")

    grouping_service_path = backend_dir / "src" / "services" / "alert_grouping_service.py"
    required_grouping_methods = [
        "find_or_create_group",
        "add_alert_to_group",
        "should_send_notification",
        "mark_notification_sent",
        "resolve_group",
        "get_group_statistics",
        "_generate_group_key",
        "_generate_group_name",
        "_find_active_group",
    ]

    if verify_class_has_methods(
        grouping_service_path,
        "AlertGroupingService",
        required_grouping_methods,
        "AlertGroupingService"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # ========================================================================
    # Verify AlertTriggerService
    # ========================================================================
    print_test("Verify AlertTriggerService Methods")

    trigger_service_path = backend_dir / "src" / "services" / "alert_trigger_service.py"
    required_trigger_methods = [
        "trigger_alert",
        "trigger_recovery_alert",
        "_send_notifications",
        "_send_recovery_notification",
        "_format_subject",
        "_format_body",
    ]

    if verify_class_has_methods(
        trigger_service_path,
        "AlertTriggerService",
        required_trigger_methods,
        "AlertTriggerService"
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # ========================================================================
    # Verify AlertGroup Model
    # ========================================================================
    print_test("Verify AlertGroup Model Fields")

    model_path = backend_dir / "src" / "models" / "alert.py"
    required_group_fields = [
        "rule_id",
        "group_key",
        "name",
        "status",
        "alert_count",
        "first_alert_at",
        "last_alert_at",
        "notification_sent",
        "last_notification_at",
        "notification_count",
        "severity",
    ]

    if verify_model_fields(model_path, "AlertGroup", required_group_fields):
        tests_passed += 1
    else:
        tests_failed += 1

    # ========================================================================
    # Verify AlertInstance Model
    # ========================================================================
    print_test("Verify AlertInstance Model Fields")

    required_instance_fields = [
        "rule_id",
        "alert_type",
        "severity",
        "status",
        "trigger_value",
        "context",
        "notification_sent",
        "group_id",
        "fired_at",
    ]

    if verify_model_fields(model_path, "AlertInstance", required_instance_fields):
        tests_passed += 1
    else:
        tests_failed += 1

    # ========================================================================
    # Verify API Endpoints
    # ========================================================================
    print_test("Verify Alert Groups API Endpoints")

    api_path = backend_dir / "src" / "api" / "routes" / "alerts_groups.py"
    if not api_path.exists():
        print_fail("Alert groups API file not found")
        tests_failed += 1
    else:
        with open(api_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # API routes use prefix="/api/alerts/groups"
        # The detail endpoint includes instances in response
        required_endpoints = [
            '@router.get("",',  # List groups (GET /api/alerts/groups)
            '@router.get("/{group_id}",',  # Get group with instances (GET /api/alerts/groups/{id})
            '@router.patch("/{group_id}/resolve",',  # Resolve group (PATCH /api/alerts/groups/{id}/resolve)
            '@router.get("/statistics",',  # Get statistics (GET /api/alerts/groups/statistics)
        ]

        missing_endpoints = []
        for endpoint in required_endpoints:
            if endpoint not in content:
                missing_endpoints.append(endpoint)

        if not missing_endpoints:
            print_pass("All required API endpoints present")
            tests_passed += 1
        else:
            print_fail(f"Missing API endpoints: {', '.join(missing_endpoints)}")
            tests_failed += 1

    # ========================================================================
    # Verify Integration Tests
    # ========================================================================
    print_test("Verify Integration Test Structure")

    test_path = backend_dir / "tests" / "integration" / "test_alert_grouping_verification.py"
    if not test_path.exists():
        print_fail("Integration test file not found")
        tests_failed += 1
    else:
        with open(test_path, 'r', encoding='utf-8') as f:
            content = f.read()

        required_tests = [
            "test_alert_grouping_prevents_notification_spam",
            "test_multiple_groups_for_different_contexts",
            "test_severity_escalation_triggers_notification",
            "test_notification_interval_prevents_spam",
        ]

        missing_tests = []
        for test in required_tests:
            if f"def {test}" not in content:
                missing_tests.append(test)

        if not missing_tests:
            print_pass("All required integration tests present")
            tests_passed += 1
        else:
            print_fail(f"Missing integration tests: {', '.join(missing_tests)}")
            tests_failed += 1

    # ========================================================================
    # Summary
    # ========================================================================
    print_section("VERIFICATION SUMMARY")

    total_tests = tests_passed + tests_failed
    pass_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"\n  Total Tests: {total_tests}")
    print(f"  Passed: {tests_passed}")
    print(f"  Failed: {tests_failed}")
    print(f"  Pass Rate: {pass_rate:.1f}%")

    if tests_failed == 0:
        print("\n  ✅ ALL STRUCTURE TESTS PASSED")
        print("\n  Alert grouping code structure is complete:")
        print("    • All required files present")
        print("    • All required methods implemented")
        print("    • All required model fields defined")
        print("    • All required API endpoints created")
        print("    • All required tests written")
        print("\n  Next steps:")
        print("    1. Run functional tests: python tests/integration/verify_alert_grouping.py")
        print("    2. Run pytest: pytest tests/integration/test_alert_grouping_verification.py -v")
        print("    3. Test manually via API endpoints")
        return True
    else:
        print("\n  ❌ SOME STRUCTURE TESTS FAILED")
        print("\n  Please review the failures above and ensure all")
        print("  required components are implemented.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
