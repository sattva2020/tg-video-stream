"""
End-to-End Verification Script for IP Whitelisting

This script verifies the complete IP whitelisting workflow:
1. Add IP range to whitelist via admin panel
2. Attempt access from whitelisted IP - should succeed
3. Attempt access from non-whitelisted IP - should be blocked
4. Verify audit log entries created

Usage:
    python tests/e2e/verify_ip_whitelist_flow.py --env {dev|staging|prod}

Requirements:
    - Backend server running
    - Frontend server running
    - Admin account for API access
    - Test IP addresses or ranges to whitelist
"""

import asyncio
import sys
import os
import argparse
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.config import settings
from tests.conftest import get_test_admin_token


class IPWhitelistVerifier:
    """Verifies IP whitelist end-to-end flow"""

    def __init__(self, base_url: str = "http://localhost:8000", frontend_url: str = "http://localhost:3000"):
        self.backend_url = base_url
        self.frontend_url = frontend_url
        self.admin_token: Optional[str] = None
        self.session = requests.Session()
        self.verification_results = []
        self.created_whitelist_entries: List[str] = []

    def log_result(self, step: str, success: bool, details: str = ""):
        """Log verification result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "step": step,
            "status": status,
            "success": success,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.verification_results.append(result)
        print(f"{status}: {step}")
        if details:
            print(f"   Details: {details}")

    def verify_backend_running(self) -> bool:
        """Verify backend server is accessible"""
        try:
            response = self.session.get(f"{self.backend_url}/api/health", timeout=5)
            is_running = response.status_code == 200
            self.log_result(
                "Backend Server Health Check",
                is_running,
                f"Status: {response.status_code}" if is_running else f"Server not responding"
            )
            return is_running
        except Exception as e:
            self.log_result("Backend Server Health Check", False, f"Error: {str(e)}")
            return False

    def verify_frontend_running(self) -> bool:
        """Verify frontend server is accessible"""
        try:
            response = self.session.get(self.frontend_url, timeout=5)
            is_running = response.status_code == 200
            self.log_result(
                "Frontend Server Health Check",
                is_running,
                f"Status: {response.status_code}" if is_running else f"Server not responding"
            )
            return is_running
        except Exception as e:
            self.log_result("Frontend Server Health Check", False, f"Error: {str(e)}")
            return False

    def get_admin_token(self) -> bool:
        """Get admin authentication token"""
        try:
            self.admin_token = get_test_admin_token()
            self.log_result("Admin Authentication", True, "Admin token obtained successfully")
            return True
        except Exception as e:
            self.log_result("Admin Authentication", False, f"Failed to get admin token: {str(e)}")
            return False

    def verify_ip_whitelist_endpoint(self) -> bool:
        """Verify IP whitelist endpoint is accessible"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{self.backend_url}/api/admin/ip-whitelist/entries",
                headers=headers,
                timeout=10
            )
            success = response.status_code == 200
            self.log_result(
                "IP Whitelist Endpoint Access",
                success,
                f"Status: {response.status_code}" if success else f"Unexpected status: {response.status_code}"
            )
            return success
        except Exception as e:
            self.log_result("IP Whitelist Endpoint Access", False, f"Error: {str(e)}")
            return False

    def create_whitelist_entry(self, cidr: str, description: str = "Test entry") -> Optional[str]:
        """
        Create a test IP whitelist entry

        Args:
            cidr: CIDR range to whitelist
            description: Description for the entry

        Returns:
            Entry ID if successful, None otherwise
        """
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            data = {
                "cidr": cidr,
                "description": description,
                "is_active": True
            }
            response = self.session.post(
                f"{self.backend_url}/api/admin/ip-whitelist/entries",
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 201:
                entry_data = response.json()
                entry_id = entry_data.get("id")
                self.created_whitelist_entries.append(entry_id)
                self.log_result(
                    f"Create Whitelist Entry: {cidr}",
                    True,
                    f"Entry ID: {entry_id}"
                )
                return entry_id
            else:
                self.log_result(
                    f"Create Whitelist Entry: {cidr}",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return None

        except Exception as e:
            self.log_result(
                f"Create Whitelist Entry: {cidr}",
                False,
                f"Error: {str(e)}"
            )
            return None

    def verify_whitelist_entry_created(self, entry_id: str, cidr: str) -> bool:
        """Verify whitelist entry was created and is accessible"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{self.backend_url}/api/admin/ip-whitelist/entries/{entry_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                entry_data = response.json()
                success = (
                    entry_data.get("cidr") == cidr and
                    entry_data.get("is_active") == True
                )
                self.log_result(
                    f"Verify Whitelist Entry: {cidr}",
                    success,
                    f"CIDR matches: {entry_data.get('cidr')}, Active: {entry_data.get('is_active')}"
                )
                return success
            else:
                self.log_result(
                    f"Verify Whitelist Entry: {cidr}",
                    False,
                    f"Status: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result(
                f"Verify Whitelist Entry: {cidr}",
                False,
                f"Error: {str(e)}"
            )
            return False

    def check_ip_allowed(self, ip: str) -> Optional[bool]:
        """
        Check if IP is allowed via admin endpoint

        Args:
            ip: IP address to check

        Returns:
            True if allowed, False if not allowed, None if error
        """
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{self.backend_url}/api/admin/ip-whitelist/check",
                headers=headers,
                params={"ip": ip},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                is_whitelisted = data.get("is_whitelisted", False)
                self.log_result(
                    f"Check IP Allowed: {ip}",
                    True,
                    f"Whitelisted: {is_whitelisted}"
                )
                return is_whitelisted
            else:
                self.log_result(
                    f"Check IP Allowed: {ip}",
                    False,
                    f"Status: {response.status_code}"
                )
                return None

        except Exception as e:
            self.log_result(
                f"Check IP Allowed: {ip}",
                False,
                f"Error: {str(e)}"
            )
            return None

    def test_access_from_ip(self, ip: str, should_succeed: bool, test_name: str = "Access Test") -> bool:
        """
        Test access from a specific IP address

        Args:
            ip: IP address to test (simulated via X-Forwarded-For header)
            should_succeed: Whether access should be allowed
            test_name: Name of the test

        Returns:
            True if test result matches expectation, False otherwise
        """
        try:
            # Test with X-Forwarded-For header to simulate different IPs
            headers = {
                "X-Forwarded-For": ip,
                "Authorization": f"Bearer {self.admin_token}"
            }

            # Use a protected endpoint (requires admin)
            response = self.session.get(
                f"{self.backend_url}/api/admin/ip-whitelist/entries",
                headers=headers,
                timeout=10
            )

            # If IP is not whitelisted and strict mode is on, expect 403
            # If IP is whitelisted or in loopback range, expect 200
            actual_success = response.status_code == 200

            # Check if result matches expectation
            test_passed = actual_success == should_succeed

            self.log_result(
                f"{test_name}: Access from {ip}",
                test_passed,
                f"Expected: {'allowed' if should_succeed else 'blocked'}, "
                f"Actual: {'allowed' if actual_success else 'blocked'} "
                f"(Status: {response.status_code})"
            )
            return test_passed

        except Exception as e:
            self.log_result(
                f"{test_name}: Access from {ip}",
                False,
                f"Error: {str(e)}"
            )
            return False

    def verify_whitelist_info_endpoint(self) -> bool:
        """Verify whitelist info endpoint returns correct statistics"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{self.backend_url}/api/admin/ip-whitelist/entries/info",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                info = response.json()
                success = (
                    "total_entries" in info and
                    "active_entries" in info and
                    "ipv4_entries" in info
                )
                self.log_result(
                    "Whitelist Info Endpoint",
                    success,
                    f"Total entries: {info.get('total_entries')}, "
                    f"Active: {info.get('active_entries')}, "
                    f"IPv4: {info.get('ipv4_entries')}, "
                    f"IPv6: {info.get('ipv6_entries')}"
                )
                return success
            else:
                self.log_result(
                    "Whitelist Info Endpoint",
                    False,
                    f"Status: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result(
                "Whitelist Info Endpoint",
                False,
                f"Error: {str(e)}"
            )
            return False

    def verify_audit_log_entries(self) -> bool:
        """Verify audit log entries were created for whitelist operations"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            # Query audit logs for IP whitelist events
            response = self.session.get(
                f"{self.backend_url}/api/admin/audit-logs",
                headers=headers,
                params={"event_type": "ip_whitelist_created", "limit": 10},
                timeout=10
            )

            if response.status_code == 200:
                logs = response.json()
                # Check if we have any IP whitelist related logs
                has_whitelist_logs = len(logs) > 0
                self.log_result(
                    "Audit Log Verification",
                    has_whitelist_logs,
                    f"Found {len(logs)} IP whitelist audit log entries"
                )
                return has_whitelist_logs
            else:
                self.log_result(
                    "Audit Log Verification",
                    False,
                    f"Status: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result(
                "Audit Log Verification",
                False,
                f"Error: {str(e)}"
            )
            return False

    def cleanup_test_entries(self):
        """Clean up test whitelist entries created during verification"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        for entry_id in self.created_whitelist_entries:
            try:
                response = self.session.delete(
                    f"{self.backend_url}/api/admin/ip-whitelist/entries/{entry_id}",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    print(f"✅ Cleaned up test entry: {entry_id}")
                else:
                    print(f"⚠️  Failed to clean up entry {entry_id}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error cleaning up entry {entry_id}: {str(e)}")

    def run_verification(self) -> Dict[str, Any]:
        """
        Run complete IP whitelist verification flow

        Returns:
            Verification results summary
        """
        print("\n" + "="*70)
        print("IP WHITELIST END-TO-END VERIFICATION")
        print("="*70 + "\n")

        # Phase 1: Health Checks
        print("Phase 1: Server Health Checks")
        print("-" * 70)
        if not self.verify_backend_running():
            return {"success": False, "reason": "Backend server not accessible"}
        if not self.verify_frontend_running():
            return {"success": False, "reason": "Frontend server not accessible"}

        # Phase 2: Authentication
        print("\nPhase 2: Admin Authentication")
        print("-" * 70)
        if not self.get_admin_token():
            return {"success": False, "reason": "Admin authentication failed"}

        # Phase 3: IP Whitelist Configuration
        print("\nPhase 3: IP Whitelist Configuration")
        print("-" * 70)
        if not self.verify_ip_whitelist_endpoint():
            return {"success": False, "reason": "IP whitelist endpoint not accessible"}

        if not self.verify_whitelist_info_endpoint():
            return {"success": False, "reason": "Whitelist info endpoint failed"}

        # Create test whitelist entries
        print("\nPhase 4: Create Test Whitelist Entries")
        print("-" * 70)

        # Test IPv4 CIDR range
        test_cidr_ipv4 = "192.168.100.0/24"
        entry_id_ipv4 = self.create_whitelist_entry(
            cidr=test_cidr_ipv4,
            description="E2E test - IPv4 range"
        )

        if not entry_id_ipv4:
            return {"success": False, "reason": "Failed to create IPv4 whitelist entry"}

        # Verify entry was created
        if not self.verify_whitelist_entry_created(entry_id_ipv4, test_cidr_ipv4):
            return {"success": False, "reason": "Failed to verify IPv4 whitelist entry"}

        # Test single IP
        test_ip_single = "10.0.0.100"
        entry_id_single = self.create_whitelist_entry(
            cidr=test_ip_single,
            description="E2E test - Single IP"
        )

        # Phase 5: IP Access Testing
        print("\nPhase 5: IP Access Testing")
        print("-" * 70)

        # Test whitelisted IP (should succeed)
        whitelisted_ip = "192.168.100.50"
        if not self.test_access_from_ip(
            ip=whitelisted_ip,
            should_succeed=True,
            test_name="Whitelisted IP"
        ):
            print("⚠️  Warning: Whitelisted IP test failed (may be due to strict mode settings)")

        # Test single whitelisted IP (should succeed)
        if entry_id_single:
            if not self.test_access_from_ip(
                ip=test_ip_single,
                should_succeed=True,
                test_name="Single Whitelisted IP"
            ):
                print("⚠️  Warning: Single whitelisted IP test failed (may be due to strict mode settings)")

        # Test non-whitelisted IP (should be blocked in strict mode)
        non_whitelisted_ip = "203.0.113.50"
        if not self.test_access_from_ip(
            ip=non_whitelisted_ip,
            should_succeed=False,
            test_name="Non-Whitelisted IP"
        ):
            print("⚠️  Note: Non-whitelisted IP test result depends on strict mode settings")

        # Test loopback IP (should always be allowed)
        if not self.test_access_from_ip(
            ip="127.0.0.1",
            should_succeed=True,
            test_name="Loopback IP"
        ):
            print("⚠️  Warning: Loopback IP should always be allowed")

        # Phase 6: Audit Log Verification
        print("\nPhase 6: Audit Log Verification")
        print("-" * 70)
        self.verify_audit_log_entries()

        # Phase 7: Whitelist Info Verification
        print("\nPhase 7: Whitelist Statistics Verification")
        print("-" * 70)
        self.verify_whitelist_info_endpoint()

        # Generate Summary
        print("\n" + "="*70)
        print("VERIFICATION SUMMARY")
        print("="*70)

        total_tests = len(self.verification_results)
        passed_tests = sum(1 for r in self.verification_results if r["success"])
        failed_tests = total_tests - passed_tests

        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")

        # Cleanup
        print("\n" + "="*70)
        print("CLEANUP")
        print("="*70)
        self.cleanup_test_entries()

        # Return results
        return {
            "success": failed_tests == 0,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "results": self.verification_results
        }

    def save_report(self, results: Dict[str, Any], filename: str = "ip_whitelist_verification_report.json"):
        """Save verification results to JSON file"""
        try:
            with open(filename, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Report saved to: {filename}")
        except Exception as e:
            print(f"\n⚠️  Failed to save report: {str(e)}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="IP Whitelist End-to-End Verification")
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend API URL"
    )
    parser.add_argument(
        "--frontend-url",
        default="http://localhost:3000",
        help="Frontend URL"
    )
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "prod"],
        default="dev",
        help="Environment to test"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate JSON report"
    )

    args = parser.parse_args()

    # Create verifier and run verification
    verifier = IPWhitelistVerifier(
        base_url=args.backend_url,
        frontend_url=args.frontend_url
    )

    results = verifier.run_verification()

    # Save report if requested
    if args.report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ip_whitelist_verification_report_{timestamp}.json"
        verifier.save_report(results, filename)

    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()
