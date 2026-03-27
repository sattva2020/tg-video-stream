"""
Code Structure Verification: Viewer Count Alerting

This script verifies the code structure for viewer count alerting without requiring
a full database setup. It checks:
1. Integration service exists and is properly structured
2. ViewerCountMonitor exists and is properly structured
3. Services can be imported
4. Key methods exist

Usage:
    cd backend
    python verify_viewer_alerting_structure.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_integration_service():
    """Check ViewerAlertIntegrationService exists and is properly structured."""
    print("=" * 60)
    print("Checking ViewerAlertIntegrationService")
    print("=" * 60)

    try:
        from src.services.viewer_alert_integration import (
            ViewerAlertIntegrationService,
            get_viewer_alert_integration,
            initialize_viewer_alert_integration,
        )

        print("✓ ViewerAlertIntegrationService imported successfully")

        # Check singleton
        integration = get_viewer_alert_integration()
        print(f"✓ Singleton instance created: {type(integration).__name__}")

        # Check key methods exist
        methods = [
            "initialize",
            "_on_low_viewers",
            "_on_viewers_drop",
            "_on_viewers_recovery",
            "_get_or_create_viewer_count_rule",
            "_get_viewer_count_rule",
            "_create_low_viewers_evaluation_result",
            "_create_viewers_drop_evaluation_result",
        ]

        for method in methods:
            if hasattr(integration, method):
                print(f"  ✓ Method '{method}' exists")
            else:
                print(f"  ✗ Method '{method}' missing")
                return False

        print("\n✓ ViewerAlertIntegrationService structure verified")
        return True

    except ImportError as e:
        # Missing dependencies is OK for structure check
        if "No module named" in str(e):
            print(f"⚠ Import skipped (missing dependency: {e})")
            print("  This is expected in testing environment without all dependencies")
            # Try to verify structure by parsing the file instead
            return verify_integration_structure_by_parsing()
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_integration_structure_by_parsing():
    """Verify integration service structure by parsing the file."""
    try:
        with open("src/services/viewer_alert_integration.py", "r") as f:
            content = f.read()

        # Check for key class and methods (more flexible search)
        checks = [
            ("class ViewerAlertIntegrationService", "ViewerAlertIntegrationService class"),
            ("def initialize(self)", "initialize method"),
            ("async def _on_low_viewers", "_on_low_viewers callback"),
            ("async def _on_viewers_drop", "_on_viewers_drop callback"),
            ("async def _on_viewers_recovery", "_on_viewers_recovery callback"),
            ("def _get_or_create_viewer_count_rule", "_get_or_create_viewer_count_rule method"),
            ("def _get_viewer_count_rule", "_get_viewer_count_rule method"),
            ("def _create_low_viewers_evaluation_result", "_create_low_viewers_evaluation_result method"),
            ("def _create_viewers_drop_evaluation_result", "_create_viewers_drop_evaluation_result method"),
            ("def get_viewer_alert_integration()", "Singleton function"),
        ]

        all_found = True
        for check_str, description in checks:
            if check_str in content:
                print(f"  ✓ {description} found in source")
            else:
                print(f"  ✗ {description} NOT found in source")
                all_found = False

        return all_found

    except Exception as e:
        print(f"  ✗ Error parsing file: {e}")
        return False


def verify_monitor_structure_by_parsing():
    """Verify viewer monitor structure by parsing the file."""
    try:
        with open("src/services/monitors/viewer_count_monitor.py", "r") as f:
            content = f.read()

        # Check for key class and methods (more flexible search)
        checks = [
            ("class ViewerCountMonitor", "ViewerCountMonitor class"),
            ("def check_viewer_count", "check_viewer_count method"),
            ("def get_viewer_status", "get_viewer_status method"),
            ("def get_viewer_history", "get_viewer_history method"),
            ("def start_monitoring", "start_monitoring method"),
            ("def stop_monitoring", "stop_monitoring method"),
            ("def get_all_streams_below_threshold", "get_all_streams_below_threshold method"),
            ("def reset_viewer_status", "reset_viewer_status method"),
            ("def get_viewer_count_monitor()", "Singleton function"),
        ]

        all_found = True
        for check_str, description in checks:
            if check_str in content:
                print(f"  ✓ {description} found in source")
            else:
                print(f"  ✗ {description} NOT found in source")
                all_found = False

        return all_found

    except Exception as e:
        print(f"  ✗ Error parsing file: {e}")
        return False


def check_viewer_monitor():
    """Check ViewerCountMonitor exists and is properly structured."""
    print("\n" + "=" * 60)
    print("Checking ViewerCountMonitor")
    print("=" * 60)

    try:
        from src.services.monitors.viewer_count_monitor import (
            ViewerCountMonitor,
            ViewerCountMonitorError,
            ViewerCountStatus,
            ViewerCountConfig,
            get_viewer_count_monitor,
        )

        print("✓ ViewerCountMonitor imported successfully")

        # Check singleton
        monitor = get_viewer_count_monitor()
        print(f"✓ Singleton instance created: {type(monitor).__name__}")

        # Check key methods exist
        methods = [
            "check_viewer_count",
            "get_viewer_status",
            "get_viewer_history",
            "start_monitoring",
            "stop_monitoring",
            "get_all_streams_below_threshold",
            "reset_viewer_status",
        ]

        for method in methods:
            if hasattr(monitor, method):
                print(f"  ✓ Method '{method}' exists")
            else:
                print(f"  ✗ Method '{method}' missing")
                return False

        print("\n✓ ViewerCountMonitor structure verified")
        return True

    except ImportError as e:
        # Missing dependencies is OK for structure check
        if "No module named" in str(e):
            print(f"⚠ Import skipped (missing dependency: {e})")
            print("  This is expected in testing environment without all dependencies")
            # Try to verify structure by parsing the file instead
            return verify_monitor_structure_by_parsing()
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def check_services_module():
    """Check services module exports integration service."""
    print("\n" + "=" * 60)
    print("Checking Services Module Exports")
    print("=" * 60)

    try:
        import src.services as services

        exports = services.__all__
        print(f"✓ Services module has {len(exports)} exports")

        if "ViewerAlertIntegrationService" in exports:
            print("  ✓ ViewerAlertIntegrationService is exported")
        else:
            print("  ✗ ViewerAlertIntegrationService NOT exported")
            return False

        print("\n✓ Services module exports verified")
        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def check_file_structure():
    """Check required files exist."""
    print("\n" + "=" * 60)
    print("Checking File Structure")
    print("=" * 60)

    # Check relative to current directory
    required_files = [
        "src/services/viewer_alert_integration.py",
        "src/services/monitors/viewer_count_monitor.py",
        "src/services/alert_trigger_service.py",
        "src/services/alert_evaluator.py",
        "src/services/alert_grouping_service.py",
        "src/services/alert_service.py",
    ]

    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - MISSING")
            all_exist = False

    if all_exist:
        print("\n✓ All required files exist")
    else:
        print("\n✗ Some required files are missing")

    return all_exist


def main():
    """Run all verification checks."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 8 + "VIEWER ALERTING STRUCTURE VERIFICATION" + " " * 10 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = {
        "file_structure": check_file_structure(),
        "viewer_monitor": check_viewer_monitor(),
        "integration_service": check_integration_service(),
        "services_module": check_services_module(),
    }

    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test_name}: {status}")

    print()

    all_passed = all(results.values())
    if all_passed:
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 15 + "ALL CHECKS PASSED" + " " * 25 + "║")
        print("╚" + "=" * 58 + "╝")
        print()
        print("The viewer count alerting integration is properly structured.")
        print("For full end-to-end testing, run verify_viewer_count_alerting.py")
        print("in an environment with all dependencies installed.")
        return 0
    else:
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 12 + "SOME CHECKS FAILED" + " " * 26 + "║")
        print("╚" + "=" * 58 + "╝")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
