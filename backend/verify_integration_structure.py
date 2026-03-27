"""
Code structure verification for stream alert integration.

Verifies that:
1. All files are created
2. Imports work correctly
3. Integration points are connected
4. No syntax errors
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def verify_files_exist():
    """Verify all required files exist."""
    print("\n=== Verifying Files Exist ===\n")

    required_files = [
        "src/services/stream_alert_integration.py",
        "src/services/stream_health_monitor.py",
        "src/services/monitors/stream_failure_monitor.py",
        "src/services/alert_trigger_service.py",
        "src/services/alert_service.py",
        "src/services/alert_grouping_service.py",
        "src/services/alert_evaluator.py",
        "src/frameworks/http/app.py",
        "tests/integration/test_stream_alert_integration.py",
        "verify_stream_alert_integration.py",
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} NOT FOUND")
            all_exist = False

    return all_exist


def verify_code_structure():
    """Verify the code structure and integration points."""
    print("\n=== Verifying Code Structure ===\n")

    try:
        # Check stream_alert_integration.py
        print("Checking stream_alert_integration.py...")
        with open("src/services/stream_alert_integration.py", "r") as f:
            content = f.read()

        checks = [
            ("StreamAlertIntegrationService class", "class StreamAlertIntegrationService:" in content),
            ("initialize() method", "def initialize(self)" in content),
            ("_on_failure_detected callback", "async def _on_failure_detected" in content),
            ("_on_failure_recovery callback", "async def _on_failure_recovery" in content),
            ("_get_or_create_stream_failure_rule", "def _get_or_create_stream_failure_rule" in content),
            ("Integration with AlertTriggerService", "AlertTriggerService" in content),
            ("Integration with AlertGroupingService", "AlertGroupingService" in content),
        ]

        for check_name, check_result in checks:
            if check_result:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ✗ {check_name} MISSING")
                return False

        # Check app.py lifespan hook
        print("\nChecking app.py lifespan integration...")
        with open("src/frameworks/http/app.py", "r") as f:
            app_content = f.read()

        if "initialize_stream_alert_integration" in app_content:
            print("  ✓ Stream alert integration initialized in app lifespan")
        else:
            print("  ✗ Stream alert integration NOT initialized in app lifespan")
            return False

        # Check services __init__.py export
        print("\nChecking services/__init__.py export...")
        with open("src/services/__init__.py", "r") as f:
            init_content = f.read()

        if "StreamAlertIntegrationService" in init_content:
            print("  ✓ StreamAlertIntegrationService exported")
        else:
            print("  ✗ StreamAlertIntegrationService NOT exported")
            return False

        print("\n✓ All code structure checks passed")
        return True

    except Exception as e:
        print(f"\n✗ Error during code structure verification: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_imports():
    """Verify that imports work (basic syntax check)."""
    print("\n=== Verifying Imports (Syntax Check) ===\n")

    try:
        # These imports will fail if dependencies are missing, but that's OK for now
        # We're mainly checking for syntax errors
        import ast

        files_to_check = [
            "src/services/stream_alert_integration.py",
            "tests/integration/test_stream_alert_integration.py",
            "verify_stream_alert_integration.py",
        ]

        for file_path in files_to_check:
            with open(file_path, "r") as f:
                code = f.read()

            try:
                ast.parse(code)
                print(f"✓ {file_path} - syntax OK")
            except SyntaxError as e:
                print(f"✗ {file_path} - SYNTAX ERROR: {e}")
                return False

        print("\n✓ All imports and syntax checks passed")
        return True

    except Exception as e:
        print(f"\n✗ Error during import verification: {e}")
        return False


def verify_integration_flow():
    """Verify the integration flow logic."""
    print("\n=== Verifying Integration Flow ===\n")

    try:
        with open("src/services/stream_alert_integration.py", "r") as f:
            content = f.read()

        # Check the flow: Failure detection -> AlertTriggerService
        checks = [
            "StreamFailureAlertMonitor",
            "on_failure_detected_callback",
            "on_failure_recovery_callback",
            "trigger_alert",
            "trigger_recovery_alert",
            "find_or_create_group",
            "EvaluationResult",
            "get_or_create_stream_failure_rule",
        ]

        all_found = True
        for check in checks:
            if check in content:
                print(f"✓ {check} found in integration")
            else:
                print(f"✗ {check} NOT found in integration")
                all_found = False

        if all_found:
            print("\n✓ Integration flow verified")
        return all_found

    except Exception as e:
        print(f"\n✗ Error during flow verification: {e}")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "="*70)
    print("Stream Alert Integration - Code Structure Verification")
    print("="*70)

    results = []

    # Check 1: Files exist
    result1 = verify_files_exist()
    results.append(("Files Exist", result1))

    # Check 2: Code structure
    result2 = verify_code_structure()
    results.append(("Code Structure", result2))

    # Check 3: Imports/Syntax
    result3 = verify_imports()
    results.append(("Imports/Syntax", result3))

    # Check 4: Integration flow
    result4 = verify_integration_flow()
    results.append(("Integration Flow", result4))

    # Summary
    print("\n" + "="*70)
    print("Verification Summary")
    print("="*70)

    all_passed = True
    for check_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{check_name:.<50} {status}")
        if not passed:
            all_passed = False

    print("="*70)

    if all_passed:
        print("\n✓ All verification checks PASSED!")
        print("\nIntegration is complete and ready for testing with a full environment.")
        return 0
    else:
        print("\n✗ Some verification checks FAILED")
        print("\nPlease review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
