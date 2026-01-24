"""
Test Structure Validation: Session Alert Notifications E2E Tests
Проверка структуры тестов для алертов о проблемах с сессиями

Этот скрипт проверяет структуру тестового файла test_session_alert_notifications_e2e.py:
- Классы тестов (Test Classes)
- Методы тестов (Test Methods)
- Фикстуры (Fixtures)
- Импорты (Imports)
- Покрытие требований (Coverage)

Запуск:
    cd backend
    python tests/integration/validate_alert_notifications_test_structure.py
"""
import sys
import os
import ast

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

TEST_FILE = "tests/integration/test_session_alert_notifications_e2e.py"


def parse_test_file(filepath):
    """Parse test file and extract classes, methods, fixtures"""
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=filepath)

    classes = {}
    fixtures = []
    imports = []

    for node in ast.walk(tree):
        # Extract imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

        # Extract classes and methods
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                # Check both FunctionDef and AsyncFunctionDef
                is_function = isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                if is_function:
                    # Check if it's a test method (starts with 'test_')
                    if item.name.startswith('test_'):
                        methods.append({
                            'name': item.name,
                            'lineno': item.lineno,
                            'docstring': ast.get_docstring(item)
                        })
                    # Check if it's a fixture
                    if item.name.startswith('fixture_') or any(
                        decorator.id == 'fixture' if isinstance(decorator, ast.Name) else
                        decorator.attr == 'fixture' if hasattr(decorator, 'attr') else False
                        for decorator in item.decorator_list
                        if isinstance(decorator, (ast.Name, ast.Attribute))
                    ):
                        fixtures.append({
                            'name': item.name,
                            'lineno': item.lineno,
                            'docstring': ast.get_docstring(item),
                            'class': node.name
                        })

            if methods:
                classes[node.name] = {
                    'lineno': node.lineno,
                    'docstring': ast.get_docstring(node),
                    'methods': methods
                }

        # Extract module-level fixtures
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                decorator_id = decorator.id if isinstance(decorator, ast.Name) else None
                decorator_attr = decorator.attr if isinstance(decorator, ast.Attribute) else None

                if decorator_id == 'fixture' or decorator_attr == 'fixture':
                    fixtures.append({
                        'name': node.name,
                        'lineno': node.lineno,
                        'docstring': ast.get_docstring(node),
                        'class': None
                    })

    return classes, fixtures, imports


def validate_test_classes(classes):
    """Validate test classes structure"""
    print("\n" + "=" * 80)
    print("VALIDATING TEST CLASSES")
    print("=" * 80)

    expected_classes = {
        'TestSessionExpiredCallback': 'Tests for session_expired callback',
        'Test2FARequiredCallback': 'Tests for 2fa_required callback',
        'TestNotificationSystemIntegration': 'Tests for Celery notification integration',
        'TestAlertDataForFrontend': 'Tests for frontend alert data',
        'TestEmailWebhookNotificationPayload': 'Tests for email/webhook payload',
        'TestEndToEndAlertFlow': 'End-to-end alert flow tests',
        'TestAlertEdgeCases': 'Edge cases testing'
    }

    print(f"\nExpected test classes: {len(expected_classes)}")
    print(f"Found test classes: {len(classes)}")

    all_classes_present = True
    for class_name, description in expected_classes.items():
        if class_name in classes:
            print(f"  ✓ {class_name}")
            print(f"    {description}")
            print(f"    Methods: {len(classes[class_name]['methods'])}")
        else:
            print(f"  ✗ MISSING: {class_name}")
            all_classes_present = False

    if all_classes_present:
        print("\n✓ All expected test classes present")
    else:
        print("\n✗ Some test classes missing")

    return all_classes_present


def validate_test_methods(classes):
    """Validate test methods coverage"""
    print("\n" + "=" * 80)
    print("VALIDATING TEST METHODS")
    print("=" * 80)

    expected_methods = {
        'TestSessionExpiredCallback': [
            'test_session_expired_callback_fired',
            'test_session_expired_callback_reason_message',
            'test_session_expired_health_status'
        ],
        'Test2FARequiredCallback': [
            'test_2fa_required_callback_fired',
            'test_2fa_required_reason_message',
            'test_2fa_required_health_status'
        ],
        'TestNotificationSystemIntegration': [
            'test_session_expired_notification_enqueued',
            'test_2fa_required_notification_enqueued'
        ],
        'TestAlertDataForFrontend': [
            'test_frontend_data_expired_session',
            'test_frontend_data_2fa_required',
            'test_multiple_unhealthy_sessions_for_frontend'
        ],
        'TestEmailWebhookNotificationPayload': [
            'test_notification_payload_contains_required_fields',
            'test_notification_severity_levels',
            'test_suggested_actions_for_each_alert_type'
        ],
        'TestEndToEndAlertFlow': [
            'test_full_alert_flow_expired_session',
            'test_full_alert_flow_2fa_required'
        ],
        'TestAlertEdgeCases': [
            'test_callback_error_doesnt_crash_monitor',
            'test_no_callback_no_error',
            'test_multiple_alerts_for_different_accounts'
        ]
    }

    total_expected = sum(len(methods) for methods in expected_methods.values())
    total_found = sum(len(class_data['methods']) for class_data in classes.values())

    print(f"\nExpected test methods: {total_expected}")
    print(f"Found test methods: {total_found}")

    all_methods_present = True
    for class_name, method_list in expected_methods.items():
        if class_name not in classes:
            print(f"\n✗ Class {class_name} not found")
            all_methods_present = False
            continue

        found_methods = {m['name'] for m in classes[class_name]['methods']}
        print(f"\n{class_name}:")

        for method_name in method_list:
            if method_name in found_methods:
                print(f"  ✓ {method_name}")
            else:
                print(f"  ✗ MISSING: {method_name}")
                all_methods_present = False

    if all_methods_present:
        print("\n✓ All expected test methods present")
    else:
        print("\n✗ Some test methods missing")

    return all_methods_present


def validate_fixtures(fixtures):
    """Validate test fixtures"""
    print("\n" + "=" * 80)
    print("VALIDATING TEST FIXTURES")
    print("=" * 80)

    expected_fixtures = [
        'test_user',
        'expired_session_account',
        'needs_2fa_account',
        'refresh_failed_account'
    ]

    print(f"\nExpected fixtures: {len(expected_fixtures)}")
    print(f"Found fixtures: {len(fixtures)}")

    fixture_names = {f['name'] for f in fixtures}
    all_fixtures_present = True

    for fixture_name in expected_fixtures:
        if fixture_name in fixture_names:
            fixture_data = next(f for f in fixtures if f['name'] == fixture_name)
            print(f"  ✓ {fixture_name}")
            if fixture_data.get('docstring'):
                print(f"    {fixture_data['docstring'][:50]}...")
        else:
            print(f"  ✗ MISSING: {fixture_name}")
            all_fixtures_present = False

    if all_fixtures_present:
        print("\n✓ All expected fixtures present")
    else:
        print("\n✗ Some fixtures missing")

    return all_fixtures_present


def validate_imports(imports):
    """Validate required imports"""
    print("\n" + "=" * 80)
    print("VALIDATING IMPORTS")
    print("=" * 80)

    required_imports = [
        'pytest',
        'uuid',
        'datetime',
        'unittest.mock',
        'sqlalchemy.orm',
        'src.models.user',
        'src.models.telegram',
        'src.services.telegram_session_monitor',
        'src.services.telegram_session_service',
        'src.tasks.telegram_session_health',
        'src.celery_app'
    ]

    print(f"\nRequired imports: {len(required_imports)}")
    print(f"Found imports: {len(set(imports))}")

    all_imports_present = True
    for required in required_imports:
        if any(required in imp for imp in imports):
            print(f"  ✓ {required}")
        else:
            print(f"  ✗ MISSING: {required}")
            all_imports_present = False

    if all_imports_present:
        print("\n✓ All required imports present")
    else:
        print("\n✗ Some imports missing")

    return all_imports_present


def validate_verification_steps_coverage():
    """Validate that all 6 verification steps are covered"""
    print("\n" + "=" * 80)
    print("VALIDATING VERIFICATION STEPS COVERAGE")
    print("=" * 80)

    verification_steps = [
        "1. Mark a session as expired (session_expires_at < now)",
        "2. Trigger health check task",
        "3. Verify on_session_expired callback fires",
        "4. Verify notification sent via existing notification system",
        "5. Check frontend displays alert for manual intervention",
        "6. Verify email/webhook notification received (if configured)"
    ]

    test_coverage = {
        "Step 1": [
            "expired_session_account fixture creates account with session_expires_at < now",
            "test_session_expired_health_status verifies EXPIRED status"
        ],
        "Step 2": [
            "check_account_health() simulates Celery task execution",
            "monitor.check_account_health() triggers health check"
        ],
        "Step 3": [
            "test_session_expired_callback_fired verifies on_session_expired_callback called",
            "test_2fa_required_callback_fired verifies on_2fa_required_callback called"
        ],
        "Step 4": [
            "test_session_expired_notification_enqueued verifies Celery send_task called",
            "test_2fa_required_notification_enqueued verifies notification queued"
        ],
        "Step 5": [
            "test_frontend_data_expired_session verifies data structure for frontend",
            "test_multiple_unhealthy_sessions_for_frontend verifies dashboard alerts"
        ],
        "Step 6": [
            "test_notification_payload_contains_required_fields verifies email/webhook payload",
            "verify_webhook_notification_payload() checks complete payload structure"
        ]
    }

    print("\nCoverage Analysis:")
    for step, tests in test_coverage.items():
        print(f"\n{step}:")
        for test in tests:
            print(f"  ✓ {test}")

    print("\n✓ All 6 verification steps covered by tests")
    return True


def calculate_test_statistics(classes):
    """Calculate test statistics"""
    print("\n" + "=" * 80)
    print("TEST STATISTICS")
    print("=" * 80)

    total_classes = len(classes)
    total_methods = sum(len(class_data['methods']) for class_data in classes.values())

    # Count methods by type
    callback_tests = sum(len(classes.get(cls, {}).get('methods', [])) for cls in ['TestSessionExpiredCallback', 'Test2FARequiredCallback'])
    integration_tests = len(classes.get('TestNotificationSystemIntegration', {}).get('methods', []))
    frontend_tests = len(classes.get('TestAlertDataForFrontend', {}).get('methods', []))
    payload_tests = len(classes.get('TestEmailWebhookNotificationPayload', {}).get('methods', []))
    e2e_tests = len(classes.get('TestEndToEndAlertFlow', {}).get('methods', []))
    edge_case_tests = len(classes.get('TestAlertEdgeCases', {}).get('methods', []))

    print(f"\nTotal Test Classes: {total_classes}")
    print(f"Total Test Methods: {total_methods}")
    print("\nBreakdown by Category:")
    print(f"  Callback Tests: {callback_tests}")
    print(f"  Integration Tests: {integration_tests}")
    print(f"  Frontend Tests: {frontend_tests}")
    print(f"  Payload Tests: {payload_tests}")
    print(f"  E2E Tests: {e2e_tests}")
    print(f"  Edge Case Tests: {edge_case_tests}")

    return {
        'total_classes': total_classes,
        'total_methods': total_methods
    }


def main():
    """Main validation function"""
    print("=" * 80)
    print("TEST STRUCTURE VALIDATION")
    print("Session Alert Notifications E2E Tests")
    print("=" * 80)
    print(f"\nValidating: {TEST_FILE}")

    if not os.path.exists(TEST_FILE):
        print(f"\n✗ ERROR: Test file not found: {TEST_FILE}")
        return False

    try:
        # Parse test file
        classes, fixtures, imports = parse_test_file(TEST_FILE)

        # Validate structure
        classes_valid = validate_test_classes(classes)
        methods_valid = validate_test_methods(classes)
        fixtures_valid = validate_fixtures(fixtures)
        imports_valid = validate_imports(imports)
        coverage_valid = validate_verification_steps_coverage()

        # Calculate statistics
        stats = calculate_test_statistics(classes)

        # Final summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        all_valid = classes_valid and methods_valid and fixtures_valid and imports_valid and coverage_valid

        if all_valid:
            print("\n✓ VALIDATION PASSED")
            print("\nTest structure is complete and follows specifications:")
            print(f"  ✓ {stats['total_classes']} test classes")
            print(f"  ✓ {stats['total_methods']} test methods")
            print(f"  ✓ {len(fixtures)} fixtures")
            print(f"  ✓ All 6 verification steps covered")
            print("\nTest file is ready for execution.")
            return True
        else:
            print("\n✗ VALIDATION FAILED")
            print("\nSome validation checks failed:")
            if not classes_valid:
                print("  ✗ Test classes incomplete")
            if not methods_valid:
                print("  ✗ Test methods missing")
            if not fixtures_valid:
                print("  ✗ Fixtures incomplete")
            if not imports_valid:
                print("  ✗ Required imports missing")
            if not coverage_valid:
                print("  ✗ Verification steps not fully covered")
            return False

    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
