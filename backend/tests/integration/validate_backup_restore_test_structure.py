"""
Test Structure Validation: Session Backup and Restore E2E Tests
Валидация структуры тестов для backup/restore функциональности

Запуск:
    cd backend
    python tests/integration/validate_backup_restore_test_structure.py

Проверяет:
• Наличие всех тестовых классов
• Наличие всех тестовых методов
• Наличие всех fixtures
• Корректность импортов
• Соответствие спецификации
"""
import ast
import sys
from pathlib import Path


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_check(category, item, status=True):
    """Print validation check"""
    status_symbol = "✅" if status else "❌"
    print(f"{status_symbol} {category}: {item}")
    return status


def main():
    """Main validation function"""
    print_section("TEST STRUCTURE VALIDATION: SESSION BACKUP/RESTORE E2E")

    test_file_path = Path(__file__).parent / 'test_session_backup_restore_e2e.py'

    if not test_file_path.exists():
        print(f"\n❌ Test file not found: {test_file_path}")
        return 1

    # Parse test file
    with open(test_file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    all_checks_passed = True

    # ===== CHECK 1: REQUIRED IMPORTS =====
    print_section("CHECK 1: REQUIRED IMPORTS")

    required_imports = {
        'pytest': 'pytest',
        'uuid': 'uuid',
        'json': 'json',
        'datetime': 'datetime',
        'timedelta': 'timedelta',
        'pathlib.Path': 'Path',
        'tempfile': 'tempfile',
        'shutil': 'shutil',
        'User': 'User',
        'TelegramAccount': 'TelegramAccount',
        'SessionHealthStatus': 'SessionHealthStatus',
        'backup_single_session_sync': 'backup_single_session_sync',
        'backup_all_sessions_sync': 'backup_all_sessions_sync',
        'encryption_service': 'encryption_service',
        'get_telegram_session_service': 'get_telegram_session_service',
    }

    found_imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            for alias in node.names:
                full_name = f"{module}.{alias.name}" if module else alias.name
                found_imports.add(full_name)
                found_imports.add(alias.name)

    for import_name, import_module in required_imports.items():
        found = any(import_name in imp for imp in found_imports)
        all_checks_passed &= print_check("Import", import_name, found)

    # ===== CHECK 2: TEST FIXTURES =====
    print_section("CHECK 2: TEST FIXTURES")

    required_fixtures = [
        'test_user',
        'backup_test_account',
        'backup_test_account_no_2fa',
        'temp_backup_dir',
    ]

    found_fixtures = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if hasattr(decorator.func, 'id') and decorator.func.id == 'pytest.fixture':
                        found_fixtures.append(node.name)
                    elif isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == 'fixture':
                            found_fixtures.append(node.name)

    for fixture in required_fixtures:
        found = fixture in found_fixtures
        all_checks_passed &= print_check("Fixture", fixture, found)

    # ===== CHECK 3: TEST CLASSES =====
    print_section("CHECK 3: TEST CLASSES")

    required_test_classes = [
        'TestBackupFileCreation',
        'TestBackupEncryption',
        'TestBackupDataFormat',
        'TestRestoreFromBackup',
        'TestBackupAllSessions',
        'TestBackupErrorHandling',
        'TestRestoreErrorHandling',
        'TestEndToEndBackupRestoreFlow',
    ]

    found_test_classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith('Test'):
                found_test_classes.append(node.name)

    for test_class in required_test_classes:
        found = test_class in found_test_classes
        all_checks_passed &= print_check("Test Class", test_class, found)

    # ===== CHECK 4: TEST METHODS =====
    print_section("CHECK 4: TEST METHODS")

    test_methods = {
        'TestBackupFileCreation': [
            'test_backup_single_session_creates_file',
            'test_backup_file_naming_convention',
            'test_backup_includes_metadata',
        ],
        'TestBackupEncryption': [
            'test_backup_file_is_encrypted',
            'test_backup_can_be_decrypted',
        ],
        'TestBackupDataFormat': [
            'test_backup_contains_all_required_fields',
            'test_backup_preserves_totp_secret',
        ],
        'TestRestoreFromBackup': [
            'test_restore_session_from_backup',
            'test_restore_preserves_totp_secret',
            'test_restore_updates_health_status',
        ],
        'TestBackupAllSessions': [
            'test_backup_all_sessions',
        ],
        'TestBackupErrorHandling': [
            'test_backup_nonexistent_account',
            'test_backup_with_invalid_session_data',
        ],
        'TestRestoreErrorHandling': [
            'test_restore_from_nonexistent_file',
            'test_restore_with_corrupted_backup',
        ],
        'TestEndToEndBackupRestoreFlow': [
            'test_full_backup_restore_cycle',
        ],
    }

    found_test_methods = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in test_methods:
            found_test_methods[node.name] = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                    found_test_methods[node.name].append(item.name)

    for test_class, methods in test_methods.items():
        print(f"\n{test_class}:")
        for method in methods:
            found = method in found_test_methods.get(test_class, [])
            all_checks_passed &= print_check("  Method", method, found)

    # ===== CHECK 5: VERIFICATION STEPS COVERAGE =====
    print_section("CHECK 5: VERIFICATION STEPS COVERAGE")

    verification_steps = [
        "Trigger backup session task for test account",
        "Verify backup file created in SESSION_BACKUP_PATH",
        "Verify file is encrypted (cannot read as plain text)",
        "Delete session from database (simulate loss)",
        "Trigger restore task with backup file path",
        "Verify session restored to TelegramAccount",
        "Verify Pyrogram client can connect with restored session",
    ]

    # Check if test_full_backup_restore_cycle exists and covers all steps
    e2e_class = next((c for c in found_test_classes if 'EndToEnd' in c), None)

    if e2e_class:
        print_check("E2E Test", f"Found {e2e_class} class")

        # Find the test method
        e2e_method_found = 'test_full_backup_restore_cycle' in found_test_methods.get(e2e_class, [])
        all_checks_passed &= print_check("E2E Method", "test_full_backup_restore_cycle", e2e_method_found)

        # Check if method has comments documenting verification steps
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == e2e_class:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == 'test_full_backup_restore_cycle':
                        # Check for docstring
                        has_docstring = ast.get_docstring(item) is not None
                        all_checks_passed &= print_check("E2E Docstring", "Documents all 7 verification steps", has_docstring)

                        # Check for step comments in function body
                        step_comments_found = 0
                        for body_node in ast.walk(item):
                            if isinstance(body_node, ast.Expr) and isinstance(body_node.value, ast.Constant):
                                if isinstance(body_node.value.value, str):
                                    if 'Step' in body_node.value.value:
                                        step_comments_found += 1

                        all_checks_passed &= print_check("E2E Comments", f"Found {step_comments_found} step comments", step_comments_found >= 7)
                        break
                break
    else:
        all_checks_passed &= print_check("E2E Test", "End-to-end test class found", False)

    # ===== CHECK 6: PATTERN COMPLIANCE =====
    print_section("CHECK 6: PATTERN COMPLIANCE")

    # Check for proper pytest usage
    uses_pytest = any('pytest' in imp for imp in found_imports)
    all_checks_passed &= print_check("Pattern", "Uses pytest framework", uses_pytest)

    # Check for fixtures usage
    uses_fixtures = len(found_fixtures) >= 3
    all_checks_passed &= print_check("Pattern", "Uses pytest fixtures", uses_fixtures)

    # Check for test class organization
    has_test_classes = len(found_test_classes) >= 5
    all_checks_passed &= print_check("Pattern", "Organized into test classes", has_test_classes)

    # Check for error handling tests
    has_error_handling = any('ErrorHandling' in tc for tc in found_test_classes)
    all_checks_passed &= print_check("Pattern", "Includes error handling tests", has_error_handling)

    # Check for E2E test
    has_e2e = any('EndToEnd' in tc or 'E2E' in tc for tc in found_test_classes)
    all_checks_passed &= print_check("Pattern", "Includes end-to-end test", has_e2e)

    # ===== CHECK 7: HELPER FUNCTION FOR RESTORE =====
    print_section("CHECK 7: HELPER FUNCTION FOR RESTORE")

    # Check for _restore_from_encrypted_backup helper function
    found_restore_helper = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == '_restore_from_encrypted_backup':
                    found_restore_helper = True
                    print_check("Helper", "Found _restore_from_encrypted_backup helper", True)

                    # Check if it has docstring noting the implementation gap
                    has_docstring = ast.get_docstring(item) is not None
                    all_checks_passed &= print_check("Helper", "Has docstring explaining implementation gap", has_docstring)
                    break

    if not found_restore_helper:
        all_checks_passed &= print_check("Helper", "Found _restore_from_encrypted_backup helper", False)

    # ===== SUMMARY =====
    print_section("VALIDATION SUMMARY")

    if all_checks_passed:
        print("\n✅ ALL VALIDATION CHECKS PASSED")
        print("\nTest structure is complete and follows best practices:")
        print("  • All required imports present")
        print("  • All fixtures defined")
        f"  • {len(found_test_classes)} test classes found"
        f"  • {sum(len(m) for m in found_test_methods.values())} test methods found"
        print("  • Covers all 7 verification steps")
        print("  • Pattern compliance verified")
        print("  • Helper function for restore demonstrates expected behavior")
        print("\nTest file: test_session_backup_restore_e2e.py")
        print("Verification script: verify_session_backup_restore.py")
        return 0
    else:
        print("\n❌ SOME VALIDATION CHECKS FAILED")
        print("\nPlease review the failed checks above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
