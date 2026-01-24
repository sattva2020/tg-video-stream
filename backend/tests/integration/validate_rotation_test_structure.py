"""
Test Structure Validation: Multi-Account Session Rotation E2E Tests

Этот скрипт валидирует структуру test_session_rotation_e2e.py
проверяя наличие всех классов, методов и фикстур.

Запуск:
    python tests/integration/validate_rotation_test_structure.py
"""
import ast
import sys
from pathlib import Path


def validate_test_structure():
    """Валидировать структуру тестового файла"""
    test_file = Path(__file__).parent / "test_session_rotation_e2e.py"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    print(f"🔍 Validating test structure: {test_file.name}")
    print("=" * 80)

    # Parse the test file
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(test_file))
    except SyntaxError as e:
        print(f"❌ Syntax error in test file: {e}")
        return False

    # Expected structure
    expected_classes = {
        'TestRotationSelection': 4,  # 4 test methods
        'TestMultiAccountRotation': 4,
        'TestRotationCircuitBreaker': 2,
        'TestRotationEventLogging': 3,
        'TestEndToEndRotationFlow': 3,
        'TestRotationEdgeCases': 5,
    }

    expected_methods = {
        'test_get_account_for_rotation_selects_lru',
        'test_get_account_respects_rotation_order_priority',
        'test_get_account_skips_non_participating_accounts',
        'test_get_account_filters_by_health_status',
        'test_rotate_sessions_refreshes_multiple_accounts',
        'test_rotate_sessions_respects_max_accounts_limit',
        'test_rotate_sessions_load_balances_across_orders',
        'test_rotate_sessions_continues_on_individual_failures',
        'test_rotation_checks_circuit_breaker_state',
        'test_no_rate_limiting_with_rotation',
        'test_rotation_updates_last_refreshed_at',
        'test_rotation_preserves_rotation_order',
        'test_rotation_updates_health_status',
        'test_full_rotation_workflow',
        'test_rotation_with_realistic_scenario',
        'test_rotation_respects_user_isolation',
        'test_rotation_with_no_accounts',
        'test_rotation_with_all_accounts_disabled',
        'test_rotation_with_inactive_accounts',
        'test_rotation_with_auto_refresh_disabled_accounts',
        'test_rotation_order_zero_treated_as_disabled',
    }

    expected_fixtures = {
        'test_user',
        'rotation_accounts',
        'service',
    }

    # Validate structure
    found_classes = {}
    found_methods = set()
    found_fixtures = set()

    for node in ast.walk(tree):
        # Check for test classes
        if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
            methods = [
                n.name for n in node.body
                if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))) and n.name.startswith('test_')
            ]
            found_classes[node.name] = len(methods)
            found_methods.update(methods)

        # Check for fixtures
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in expected_fixtures:
            # Check if it has pytest.fixture decorator
            has_fixture = any(
                (isinstance(decorator, ast.Call) and
                 hasattr(decorator.func, 'id') and
                 decorator.func.id == 'fixture') or
                (isinstance(decorator, ast.Name) and
                 decorator.id == 'fixture')
                for decorator in node.decorator_list
            )
            if has_fixture:
                found_fixtures.add(node.name)

    # Validation results
    all_passed = True

    # Check classes
    print("\n📋 Test Classes:")
    for class_name, expected_count in expected_classes.items():
        if class_name in found_classes:
            actual_count = found_classes[class_name]
            status = "✅" if actual_count == expected_count else "⚠️ "
            print(f"   {status} {class_name}: {actual_count}/{expected_count} methods")
            if actual_count != expected_count:
                print(f"      Expected {expected_count} methods, found {actual_count}")
                all_passed = False
        else:
            print(f"   ❌ {class_name}: NOT FOUND")
            all_passed = False

    # Check for unexpected classes
    for class_name in found_classes:
        if class_name not in expected_classes:
            print(f"   ⚠️  {class_name}: UNEXPECTED (found {found_classes[class_name]} methods)")

    # Check methods
    print("\n🧪 Test Methods:")
    for method_name in expected_methods:
        if method_name in found_methods:
            print(f"   ✅ {method_name}")
        else:
            print(f"   ❌ {method_name}: NOT FOUND")
            all_passed = False

    # Check for unexpected methods
    for method_name in found_methods:
        if method_name not in expected_methods:
            print(f"   ⚠️  {method_name}: UNEXPECTED")

    # Check fixtures
    print("\n🔧 Pytest Fixtures:")
    for fixture_name in expected_fixtures:
        if fixture_name in found_fixtures:
            print(f"   ✅ {fixture_name}")
        else:
            print(f"   ⚠️  {fixture_name}: NOT FOUND (might be in conftest.py)")

    # Check imports
    print("\n📦 Imports:")
    expected_imports = {
        'pytest',
        'uuid',
        'datetime',
        'sqlalchemy',
        'src.models.user',
        'src.models.telegram',
        'src.services.telegram_session_service',
        'src.services.telegram_session_monitor',
        'src.services.circuit_breaker',
    }

    found_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found_imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found_imports.add(node.module)

    for imp in expected_imports:
        if imp in found_imports or any(imp in s for s in found_imports):
            print(f"   ✅ {imp}")
        else:
            print(f"   ⚠️  {imp}: NOT FOUND")

    # Summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ TEST STRUCTURE VALIDATION PASSED")
        print(f"   Found {len(found_classes)} test classes")
        print(f"   Found {len(found_methods)} test methods")
        print(f"   Found {len(found_fixtures)} fixtures")
        return True
    else:
        print("❌ TEST STRUCTURE VALIDATION FAILED")
        print("   Some expected classes, methods, or fixtures are missing")
        return False


def main():
    """Main entry point"""
    try:
        success = validate_test_structure()
        return 0 if success else 1
    except Exception as e:
        print(f"\n💥 Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
