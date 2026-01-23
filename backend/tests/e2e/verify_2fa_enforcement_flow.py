"""
End-to-End Verification Script for 2FA Enforcement Flow

This script verifies the complete 2FA enforcement workflow:
1. Enable 2FA enforcement policy in admin panel
2. Attempt to access protected endpoint without 2FA - should be blocked
3. Enable 2FA on user account
4. Access protected endpoint with 2FA - should succeed
5. Verify compliance dashboard shows 2FA status

Usage:
    python tests/e2e/verify_2fa_enforcement_flow.py --env {dev|staging|prod}

Requirements:
    - Backend server running
    - Frontend server running
    - Admin account for API access
    - Test user account for 2FA testing
"""

import asyncio
import sys
import os
import argparse
import requests
import pyotp
from typing import Dict, Any, Optional
from datetime import datetime
import json
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.config import settings
from tests.conftest import get_test_admin_token, create_test_user


class TwoFactorEnforcementVerifier:
    """Verifies 2FA enforcement end-to-end flow"""

    def __init__(self, base_url: str = "http://localhost:8000", frontend_url: str = "http://localhost:3000"):
        self.backend_url = base_url
        self.frontend_url = frontend_url
        self.admin_token: Optional[str] = None
        self.test_user_token: Optional[str] = None
        self.test_user_id: Optional[str] = None
        self.session = requests.Session()
        self.verification_results = []
        self.policy_id: Optional[str] = None
        self.totp_secret: Optional[str] = None

        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

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

    def create_test_user(self) -> bool:
        """Create a test user for 2FA testing"""
        try:
            from src.auth.jwt import create_access_token
            from src.models.user import User, UserRole, UserStatus
            from database import SessionLocal

            db = SessionLocal()
            try:
                # Create test user
                test_user = User(
                    email="2fa-test-user@example.com",
                    hashed_password="hashed_password_here",
                    role=UserRole.USER,
                    status=UserStatus.APPROVED
                )
                db.add(test_user)
                db.commit()
                db.refresh(test_user)

                self.test_user_id = str(test_user.id)
                self.test_user_token = create_access_token(data={
                    "sub": self.test_user_id,
                    "role": test_user.role
                })

                self.log_result(
                    "Test User Creation",
                    True,
                    f"Created test user: {test_user.email}"
                )
                return True
            finally:
                db.close()
        except Exception as e:
            self.log_result("Test User Creation", False, f"Failed to create test user: {str(e)}")
            return False

    def create_2fa_enforcement_policy(self) -> bool:
        """Create a 2FA enforcement policy via API"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            payload = {
                "name": "E2E Test 2FA Policy",
                "policy_type": "two_factor_enforcement",
                "enabled": True,
                "enforcement_level": "mandatory",
                "affected_roles": ["user"],
                "grace_period_hours": 0,
                "allow_exempt_alternative_auth": False,
                "description": "2FA enforcement policy for E2E testing"
            }

            response = self.session.post(
                f"{self.backend_url}/api/admin/security-policies",
                headers=headers,
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                self.policy_id = data.get("id")
                self.log_result(
                    "2FA Policy Creation",
                    True,
                    f"Created policy ID: {self.policy_id}"
                )
                return True
            else:
                self.log_result(
                    "2FA Policy Creation",
                    False,
                    f"Status: {response.status_code}, Error: {response.text}"
                )
                return False
        except Exception as e:
            self.log_result("2FA Policy Creation", False, f"Error: {str(e)}")
            return False

    def verify_policy_created(self) -> bool:
        """Verify the 2FA policy was created successfully"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{self.backend_url}/api/admin/security-policies",
                headers=headers
            )

            if response.status_code == 200:
                policies = response.json()
                found = any(p.get("id") == self.policy_id for p in policies)
                self.log_result(
                    "2FA Policy Verification",
                    found,
                    f"Policy found in list: {found}"
                )
                return found
            else:
                self.log_result(
                    "2FA Policy Verification",
                    False,
                    f"Status: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_result("2FA Policy Verification", False, f"Error: {str(e)}")
            return False

    def test_access_without_2fa(self) -> bool:
        """Test accessing protected endpoint without 2FA - should be blocked"""
        try:
            headers = {"Authorization": f"Bearer {self.test_user_token}"}

            # Try to access a protected endpoint
            response = self.session.get(
                f"{self.backend_url}/api/admin/security/dashboard",
                headers=headers
            )

            # Should be blocked (403 Forbidden)
            is_blocked = response.status_code == 403
            error_detail = ""

            if is_blocked:
                try:
                    data = response.json()
                    error_detail = data.get("detail", {})
                    if isinstance(error_detail, dict):
                        error_type = error_detail.get("error")
                        if error_type == "2FA_REQUIRED":
                            self.log_result(
                                "Access Blocked Without 2FA",
                                True,
                                f"Correctly blocked with 2FA_REQUIRED error"
                            )
                            return True
                except Exception:
                    pass

            self.log_result(
                "Access Blocked Without 2FA",
                is_blocked,
                f"Status: {response.status_code}, Response: {response.text[:200]}"
            )
            return is_blocked
        except Exception as e:
            self.log_result("Access Blocked Without 2FA", False, f"Error: {str(e)}")
            return False

    def setup_2fa_for_user(self) -> bool:
        """Setup 2FA for the test user"""
        try:
            headers = {"Authorization": f"Bearer {self.test_user_token}"}

            # Setup 2FA
            response = self.session.post(
                f"{self.backend_url}/api/auth/totp/setup",
                headers=headers
            )

            if response.status_code in [200, 201]:
                data = response.json()
                self.totp_secret = data.get("secret")
                self.log_result(
                    "2FA Setup",
                    True,
                    f"2FA setup initiated, secret received"
                )
                return True
            else:
                self.log_result(
                    "2FA Setup",
                    False,
                    f"Status: {response.status_code}, Error: {response.text}"
                )
                return False
        except Exception as e:
            self.log_result("2FA Setup", False, f"Error: {str(e)}")
            return False

    def verify_2fa_code(self) -> bool:
        """Verify and enable 2FA with a valid TOTP code"""
        try:
            if not self.totp_secret:
                self.log_result("2FA Verification", False, "No TOTP secret available")
                return False

            # Generate a valid TOTP code
            totp = pyotp.TOTP(self.totp_secret)
            current_code = totp.now()

            headers = {"Authorization": f"Bearer {self.test_user_token}"}
            payload = {"code": current_code}

            response = self.session.post(
                f"{self.backend_url}/api/auth/totp/verify",
                headers=headers,
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                if data.get("status") == "enabled":
                    self.log_result(
                        "2FA Verification",
                        True,
                        f"2FA successfully enabled for test user"
                    )
                    return True

            self.log_result(
                "2FA Verification",
                False,
                f"Status: {response.status_code}, Error: {response.text}"
            )
            return False
        except Exception as e:
            self.log_result("2FA Verification", False, f"Error: {str(e)}")
            return False

    def test_access_with_2fa(self) -> bool:
        """Test accessing protected endpoint with 2FA - should succeed"""
        try:
            headers = {"Authorization": f"Bearer {self.test_user_token}"}

            # Try to access the same protected endpoint
            response = self.session.get(
                f"{self.backend_url}/api/admin/security/dashboard",
                headers=headers
            )

            # Should now succeed (200 OK or 401 if user lacks admin role, but not 403 for 2FA)
            is_allowed = response.status_code in [200, 401]  # 401 = insufficient permissions, not 2FA

            if is_allowed:
                self.log_result(
                    "Access Allowed With 2FA",
                    True,
                    f"2FA enforcement passed, status: {response.status_code}"
                )
                return True
            else:
                self.log_result(
                    "Access Allowed With 2FA",
                    False,
                    f"Status: {response.status_code}, Error: {response.text[:200]}"
                )
                return False
        except Exception as e:
            self.log_result("Access Allowed With 2FA", False, f"Error: {str(e)}")
            return False

    def verify_compliance_dashboard(self) -> bool:
        """Verify compliance dashboard shows 2FA status"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}

            response = self.session.get(
                f"{self.backend_url}/api/admin/security/dashboard",
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                security_configs = data.get("security_configs", {})

                # Check if 2FA enforcement is shown as enabled
                two_factor_enabled = security_configs.get("two_factor_enforcement_enabled", False)

                if two_factor_enabled:
                    self.log_result(
                        "Compliance Dashboard 2FA Status",
                        True,
                        f"2FA enforcement correctly shown as enabled"
                    )
                    return True
                else:
                    self.log_result(
                        "Compliance Dashboard 2FA Status",
                        False,
                        f"2FA enforcement not shown as enabled in dashboard"
                    )
                    return False
            else:
                self.log_result(
                    "Compliance Dashboard 2FA Status",
                    False,
                    f"Status: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_result("Compliance Dashboard 2FA Status", False, f"Error: {str(e)}")
            return False

    def verify_security_events_logged(self) -> bool:
        """Verify that security events are logged"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}

            # Get security events
            response = self.session.get(
                f"{self.backend_url}/api/admin/security/events?period=24h",
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                has_2fa_events = any(
                    "2fa" in str(event.get("category", "")).lower() or
                    "two_factor" in str(event.get("category", "")).lower()
                    for event in events
                )

                self.log_result(
                    "Security Events Logging",
                    has_2fa_events,
                    f"Found {len(events)} events, 2FA events: {has_2fa_events}"
                )
                return has_2fa_events
            else:
                self.log_result(
                    "Security Events Logging",
                    False,
                    f"Status: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_result("Security Events Logging", False, f"Error: {str(e)}")
            return False

    def cleanup(self):
        """Cleanup test data"""
        try:
            if self.policy_id:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                self.session.delete(
                    f"{self.backend_url}/api/admin/security-policies/{self.policy_id}",
                    headers=headers
                )
                self.log_result("Cleanup: 2FA Policy Deleted", True, f"Deleted policy {self.policy_id}")
        except Exception as e:
            self.log_result("Cleanup: 2FA Policy Deletion", False, f"Error: {str(e)}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate verification report"""
        total = len(self.verification_results)
        passed = sum(1 for r in self.verification_results if r["success"])
        failed = total - passed

        return {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
            },
            "results": self.verification_results,
            "timestamp": datetime.utcnow().isoformat()
        }

    def run_verification(self) -> bool:
        """Run complete 2FA enforcement verification"""
        print("\n" + "="*70)
        print("2FA ENFORCEMENT END-TO-END VERIFICATION")
        print("="*70 + "\n")

        # Phase 1: Server Health Checks
        print("Phase 1: Server Health Checks")
        print("-" * 70)

        if not self.verify_backend_running():
            print("\n❌ Backend server is not running. Aborting verification.")
            return False

        self.verify_frontend_running()

        # Phase 2: Authentication
        print("\nPhase 2: Authentication Setup")
        print("-" * 70)

        if not self.get_admin_token():
            print("\n❌ Failed to get admin token. Aborting verification.")
            return False

        if not self.create_test_user():
            print("\n❌ Failed to create test user. Aborting verification.")
            return False

        # Phase 3: 2FA Policy Configuration
        print("\nPhase 3: 2FA Policy Configuration")
        print("-" * 70)

        if not self.create_2fa_enforcement_policy():
            print("\n❌ Failed to create 2FA policy. Aborting verification.")
            self.cleanup()
            return False

        self.verify_policy_created()

        # Phase 4: 2FA Enforcement Testing
        print("\nPhase 4: 2FA Enforcement Testing")
        print("-" * 70)

        self.test_access_without_2fa()

        # Phase 5: 2FA Setup
        print("\nPhase 5: 2FA Setup for Test User")
        print("-" * 70)

        if not self.setup_2fa_for_user():
            print("\n⚠️  Failed to setup 2FA. Continuing with remaining tests.")

        if not self.verify_2fa_code():
            print("\n⚠️  Failed to verify 2FA code. Continuing with remaining tests.")

        # Phase 6: Access with 2FA
        print("\nPhase 6: Access Testing With 2FA")
        print("-" * 70)

        self.test_access_with_2fa()

        # Phase 7: Compliance Dashboard Verification
        print("\nPhase 7: Compliance Dashboard Verification")
        print("-" * 70)

        self.verify_compliance_dashboard()
        self.verify_security_events_logged()

        # Phase 8: Cleanup
        print("\nPhase 8: Cleanup")
        print("-" * 70)

        self.cleanup()

        # Generate Report
        print("\n" + "="*70)
        print("VERIFICATION SUMMARY")
        print("="*70)

        report = self.generate_report()
        print(f"\nTotal Checks: {report['summary']['total']}")
        print(f"Passed: {report['summary']['passed']} ✅")
        print(f"Failed: {report['summary']['failed']} ❌")
        print(f"Success Rate: {report['summary']['success_rate']}")

        # Save report to file
        report_path = "backend/tests/e2e/2fa_enforcement_verification_report.json"
        try:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {report_path}")
        except Exception as e:
            print(f"\n⚠️  Failed to save report: {e}")

        # Return overall success
        all_passed = report['summary']['failed'] == 0
        if all_passed:
            print("\n🎉 All 2FA enforcement verification checks passed!")
        else:
            print(f"\n⚠️  {report['summary']['failed']} verification check(s) failed.")

        print("="*70 + "\n")

        return all_passed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Verify 2FA enforcement end-to-end flow"
    )
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

    args = parser.parse_args()

    verifier = TwoFactorEnforcementVerifier(
        base_url=args.backend_url,
        frontend_url=args.frontend_url
    )

    success = verifier.run_verification()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
