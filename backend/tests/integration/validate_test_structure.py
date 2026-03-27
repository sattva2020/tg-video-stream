"""
Test Structure Validation Script
==================================

Validates that the E2E test file follows correct patterns and structure
without requiring all dependencies to be installed.
"""
import ast
import sys


def validate_test_file(filepath):
    """Validate test file structure and patterns"""
    print(f"Validating: {filepath}\n")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse the file
    try:
        tree = ast.parse(content, filepath)
        print("✓ File parses successfully (valid Python syntax)")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        return False

    # Check for required imports
    imports_found = {
        'pytest': False,
        'datetime': False,
        'uuid': False,
        'TelegramAccount': False,
        'SessionHealthStatus': False,
        'check_all_telegram_sessions_health_task': False,
        'check_session_health_sync': False,
        'TelegramSessionMonitor': False,
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('pytest'):
                    imports_found['pytest'] = True
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if 'datetime' in node.module:
                    imports_found['datetime'] = True
                if 'uuid' in node.module:
                    imports_found['uuid'] = True
                if 'telegram' in node.module:
                    for alias in node.names:
                        if alias.name == 'TelegramAccount':
                            imports_found['TelegramAccount'] = True
                        if alias.name == 'SessionHealthStatus':
                            imports_found['SessionHealthStatus'] = True
                if 'telegram_session_health' in node.module:
                    for alias in node.names:
                        if alias.name == 'check_all_telegram_sessions_health_task':
                            imports_found['check_all_telegram_sessions_health_task'] = True
                        if alias.name == 'check_session_health_sync':
                            imports_found['check_session_health_sync'] = True
                if 'telegram_session_monitor' in node.module:
                    for alias in node.names:
                        if alias.name == 'TelegramSessionMonitor':
                            imports_found['TelegramSessionMonitor'] = True

    print("\nRequired imports check:")
    all_imports_ok = True
    for name, found in imports_found.items():
        status = "✓" if found else "✗"
        print(f"  {status} {name}")
        if not found:
            all_imports_ok = False

    # Count test classes and test methods
    test_classes = []
    test_methods = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith('Test'):
                test_classes.append(node.name)
                # Count test methods in this class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                        test_methods.append(f"{node.name}.{item.name}")

    print(f"\nTest structure:")
    print(f"  ✓ Found {len(test_classes)} test classes")
    print(f"  ✓ Found {len(test_methods)} test methods")

    # Display test classes
    print(f"\nTest classes:")
    for cls in test_classes:
        print(f"  - {cls}")

    # Check for specific test fixtures
    fixtures = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == 'fixture':
                    fixtures.append(node.name)
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == 'fixture':
                    fixtures.append(node.name)

    print(f"\n✓ Found {len(fixtures)} fixtures")
    for fixture in fixtures:
        print(f"  - {fixture}")

    # Check for required test classes
    required_classes = [
        'TestHealthCheckCeleryTask',
        'TestDatabaseHealthUpdates',
        'TestRedisHealthStorage',
        'TestAPIHealthEndpoint',
        'TestEndToEndHealthMonitoringFlow',
        'TestHealthMonitoringEdgeCases',
    ]

    print(f"\nRequired test classes:")
    all_classes_ok = True
    for required in required_classes:
        found = required in test_classes
        status = "✓" if found else "✗"
        print(f"  {status} {required}")
        if not found:
            all_classes_ok = False

    # Check for test coverage of verification steps
    verification_steps = [
        ('TestHealthCheckCeleryTask', 'Celery task execution'),
        ('TestDatabaseHealthUpdates', 'Database health status updates'),
        ('TestRedisHealthStorage', 'Redis health data storage'),
        ('TestAPIHealthEndpoint', 'API health status endpoint'),
        ('TestEndToEndHealthMonitoringFlow', 'End-to-end flow'),
    ]

    print(f"\nVerification steps coverage:")
    for cls, description in verification_steps:
        found = cls in test_classes
        status = "✓" if found else "✗"
        print(f"  {status} {description}")

    # Final validation
    print("\n" + "="*70)
    if all_imports_ok and all_classes_ok:
        print("✓ VALIDATION PASSED - Test file structure is correct")
        print("="*70)
        return True
    else:
        print("✗ VALIDATION FAILED - Some issues detected")
        print("="*70)
        return False


def main():
    filepath = 'test_session_health_monitoring_e2e.py'

    # Try to find the file
    import os
    possible_paths = [
        filepath,
        f'tests/integration/{filepath}',
        f'backend/tests/integration/{filepath}',
    ]

    actual_path = None
    for path in possible_paths:
        if os.path.exists(path):
            actual_path = path
            break

    if not actual_path:
        print(f"✗ Could not find test file: {filepath}")
        print(f"  Searched in: {possible_paths}")
        return False

    return validate_test_file(actual_path)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
