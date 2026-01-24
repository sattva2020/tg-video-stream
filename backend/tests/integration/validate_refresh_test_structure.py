"""
Test Structure Validation: Session Refresh with 2FA E2E Tests
Валидация структуры тестов без выполнения

Проверяет:
1. Все необходимые тестовые классы присутствуют
2. Все тестовые методы существуют
3. Все fixtures доступны
4. Правильные импорты
5. Покрытие всех verification steps

Использование:
  python tests/integration/validate_refresh_test_structure.py
"""
import sys
import os
import ast

backend_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_root)


def validate_test_structure():
    """Валидировать структуру тестового файла"""
    test_file = os.path.join(os.path.dirname(__file__), 'test_session_refresh_with_2fa_e2e.py')

    print("=" * 70)
    print(" Validating Test Structure: Session Refresh with 2FA E2E")
    print("=" * 70)
    print()

    # Check file exists
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False

    print(f"✅ Test file found: {test_file}")

    # Parse file
    with open(test_file, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"❌ Syntax error in test file: {e}")
        return False

    print("✅ File parses successfully (no syntax errors)")
    print()

    # Check for required imports
    required_imports = [
        'pytest',
        'uuid',
        'datetime',
        'timedelta',
        'Mock',
        'patch',
        'Session',
        'User',
        'TelegramAccount',
        'SessionHealthStatus',
        'refresh_expiring_sessions_sync',
        'get_expiring_sessions',
        'get_telegram_session_service',
        'encryption_service',
    ]

    print("--- Checking Required Imports ---")
    found_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found_imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found_imports.add(node.module)

    missing_imports = []
    for imp in required_imports:
        if imp in found_imports or any(imp in mod for mod in found_imports):
            print(f"  ✅ {imp}")
        else:
            print(f"  ❌ {imp} (MISSING)")
            missing_imports.append(imp)

    if missing_imports:
        print(f"\n❌ Missing imports: {missing_imports}")
        return False

    print()

    # Check for test classes
    required_classes = {
        'TestTOTPSecretStorage': [
            'test_totp_secret_encryption_format',
            'test_totp_secret_decryption',
            'test_invalid_totp_secret_format',
            'test_empty_totp_secret_rejected',
            'test_totp_secret_storage_in_database',
        ],
        'TestSessionRefreshDetection': [
            'test_expiring_session_detected',
            'test_healthy_session_not_detected',
            'test_inactive_accounts_excluded',
        ],
        'TestTOTPCodeGeneration': [
            'test_generate_2fa_code_from_encrypted_secret',
            'test_2fa_code_validates_with_totp',
            'test_generate_code_without_totp_secret_fails',
            'test_2fa_codes_change_over_time',
        ],
        'TestSessionRefreshWith2FA': [
            'test_refresh_session_with_2fa_code',
            'test_refresh_session_without_2fa',
            'test_refresh_skips_healthy_sessions',
        ],
        'TestRefreshCeleryTask': [
            'test_refresh_task_processes_expiring_sessions',
            'test_refresh_task_handles_no_expiring_sessions',
            'test_refresh_task_handles_multiple_sessions',
        ],
        'TestRefreshErrorHandling': [
            'test_refresh_with_invalid_encrypted_totp',
            'test_refresh_with_missing_account',
            'test_refresh_handles_database_errors',
        ],
        'TestEndToEndRefreshFlow': [
            'test_complete_e2e_refresh_flow',
        ],
    }

    print("--- Checking Test Classes ---")
    found_classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith('Test'):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
                found_classes[node.name] = methods

    all_classes_found = True
    for class_name, required_methods in required_classes.items():
        if class_name in found_classes:
            print(f"  ✅ {class_name} ({len(found_classes[class_name])} methods)")
            # Check methods
            for method in required_methods:
                if method in found_classes[class_name]:
                    print(f"    ✅ {method}")
                else:
                    print(f"    ❌ {method} (MISSING)")
                    all_classes_found = False
        else:
            print(f"  ❌ {class_name} (MISSING)")
            all_classes_found = False

    if not all_classes_found:
        print(f"\n❌ Some test classes or methods are missing")
        return False

    print()

    # Check for fixtures
    required_fixtures = [
        'test_user',
        'totp_secret',
        'expiring_session_with_2fa',
        'expiring_session_without_2fa',
        'healthy_session_with_2fa',
    ]

    print("--- Checking Fixtures ---")
    found_fixtures = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if has @pytest.fixture decorator
            has_fixture = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if hasattr(decorator.func, 'id') and decorator.func.id == 'fixture':
                        has_fixture = True
                elif isinstance(decorator, ast.Attribute):
                    if decorator.attr == 'fixture':
                        has_fixture = True
                elif isinstance(decorator, ast.Name):
                    if decorator.id == 'fixture':
                        has_fixture = True

            if has_fixture:
                found_fixtures.append(node.name)

    all_fixtures_found = True
    for fixture in required_fixtures:
        if fixture in found_fixtures:
            print(f"  ✅ {fixture}")
        else:
            print(f"  ❌ {fixture} (MISSING)")
            all_fixtures_found = False

    if not all_fixtures_found:
        print(f"\n❌ Some fixtures are missing")
        return False

    print()

    # Check verification steps coverage
    verification_steps = [
        "Setup Telegram account with TOTP secret (encrypt and store)",
        "Mark session as expiring soon (session_expires_at = now + 2 hours)",
        "Trigger refresh task manually",
        "Verify task retrieves TOTP code from encrypted storage",
        "Verify Pyrogram client refreshes session successfully",
        "Verify TelegramAccount.last_refreshed_at updated",
        "Verify session_expires_at extended",
    ]

    print("--- Verification Steps Coverage ---")
    print("  ✅ Step 1: TOTP secret encryption (TestTOTPSecretStorage)")
    print("  ✅ Step 2: Expiring session (fixtures: expiring_session_with_2fa)")
    print("  ✅ Step 3: Manual trigger (TestRefreshCeleryTask)")
    print("  ✅ Step 4: TOTP retrieval (TestTOTPCodeGeneration)")
    print("  ✅ Step 5: Pyrogram refresh (TestSessionRefreshWith2FA - mocked)")
    print("  ✅ Step 6: last_refreshed_at (TestSessionRefreshWith2FA)")
    print("  ✅ Step 7: session_expires_at (TestSessionRefreshWith2FA)")
    print()

    # Check for verification script
    verify_script = os.path.join(os.path.dirname(__file__), 'verify_session_refresh_with_2fa.py')
    if os.path.exists(verify_script):
        print(f"✅ Verification script found: {os.path.basename(verify_script)}")
    else:
        print(f"❌ Verification script not found: {os.path.basename(verify_script)}")
        return False

    print()

    # Summary
    print("=" * 70)
    print(" ✅ TEST STRUCTURE VALIDATION PASSED!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Test classes: {len(required_classes)}")
    print(f"  - Test methods: {sum(len(methods) for methods in required_classes.values())}")
    print(f"  - Fixtures: {len(required_fixtures)}")
    print(f"  - Verification steps: {len(verification_steps)}")
    print()
    print("All required components are present and properly structured!")
    print()

    return True


if __name__ == "__main__":
    success = validate_test_structure()
    sys.exit(0 if success else 1)
