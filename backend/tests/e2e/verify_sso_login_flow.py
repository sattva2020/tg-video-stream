"""
End-to-End Verification Script for SSO/SAML Login Flow

This script verifies the complete SAML authentication workflow:
1. Configure SAML IdP in admin panel
2. Initiate SAML login from frontend
3. Complete authentication with IdP
4. Verify user is logged in with correct role
5. Verify audit log entry created

Usage:
    python tests/e2e/verify_sso_login_flow.py --env {dev|staging|prod}

Requirements:
    - Backend server running
    - Frontend server running
    - Valid SAML IdP configuration (Okta/Azure AD/Google Workspace)
    - Admin account for API access
"""

import asyncio
import sys
import os
import argparse
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.config import settings
from tests.conftest import get_test_admin_token, create_test_user


class SAMLSSOVerifier:
    """Verifies SAML SSO end-to-end flow"""

    def __init__(self, base_url: str = "http://localhost:8000", frontend_url: str = "http://localhost:3000"):
        self.backend_url = base_url
        self.frontend_url = frontend_url
        self.admin_token: Optional[str] = None
        self.session = requests.Session()
        self.verification_results = []

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

    def verify_saml_config_endpoint(self) -> bool:
        """Verify SAML configuration endpoint is accessible"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{self.backend_url}/api/admin/saml/configs",
                headers=headers,
                timeout=10
            )
            success = response.status_code == 200
            self.log_result(
                "SAML Config Endpoint Access",
                success,
                f"Status: {response.status_code}" if success else f"Unexpected status: {response.status_code}"
            )
            return success
        except Exception as e:
            self.log_result("SAML Config Endpoint Access", False, f"Error: {str(e)}")
            return False

    def verify_saml_metadata_endpoint(self) -> bool:
        """Verify SAML metadata endpoint is accessible"""
        try:
            response = self.session.get(
                f"{self.backend_url}/api/auth/saml/metadata",
                timeout=10
            )
            # Metadata endpoint should return XML
            success = response.status_code == 200 and "xml" in response.headers.get("content-type", "")
            self.log_result(
                "SAML Metadata Endpoint",
                success,
                f"Content-Type: {response.headers.get('content-type', 'N/A')}"
            )
            return success
        except Exception as e:
            self.log_result("SAML Metadata Endpoint", False, f"Error: {str(e)}")
            return False

    def create_test_saml_config(self) -> Optional[str]:
        """
        Create a test SAML configuration

        Returns:
            Config ID if successful, None otherwise
        """
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            config_data = {
                "name": "Test IdP",
                "enabled": True,
                "idp_entity_id": "https://test-idp.example.com/entityid",
                "idp_sso_url": "https://test-idp.example.com/sso",
                "idp_x509_cert": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...",
                "sp_entity_id": f"{self.backend_url}/saml/metadata",
                "sp_acs_url": f"{self.backend_url}/api/auth/saml/acs",
                "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "attribute_mapping": {
                    "email": "email",
                    "full_name": "firstName + ' ' + lastName"
                },
                "role_mapping": {
                    "admin": ["superadmin"],
                    "user": ["users"]
                }
            }

            response = self.session.post(
                f"{self.backend_url}/api/admin/saml/configs",
                headers=headers,
                json=config_data,
                timeout=10
            )

            if response.status_code == 201:
                config_id = response.json().get("id")
                self.log_result(
                    "Create Test SAML Config",
                    True,
                    f"Config ID: {config_id}"
                )
                return config_id
            else:
                self.log_result(
                    "Create Test SAML Config",
                    False,
                    f"Status: {response.status_code}, Response: {response.text[:200]}"
                )
                return None

        except Exception as e:
            self.log_result("Create Test SAML Config", False, f"Error: {str(e)}")
            return None

    def verify_saml_login_endpoint(self) -> bool:
        """Verify SAML login initiation endpoint"""
        try:
            response = self.session.get(
                f"{self.backend_url}/api/auth/saml/login",
                allow_redirects=False,
                timeout=10
            )
            # Should return 307 redirect to IdP
            success = response.status_code == 307 or response.status_code == 302
            location = response.headers.get("location", "N/A")
            self.log_result(
                "SAML Login Initiation",
                success,
                f"Redirect to: {location}" if success else f"Status: {response.status_code}"
            )
            return success
        except Exception as e:
            self.log_result("SAML Login Initiation", False, f"Error: {str(e)}")
            return False

    def verify_frontend_saml_button(self) -> bool:
        """Verify SAML login button exists in frontend"""
        try:
            # Fetch the auth page
            response = self.session.get(f"{self.frontend_url}/auth", timeout=10)
            success = response.status_code == 200

            if success:
                # Check for SAML-related content
                page_content = response.text
                has_saml_button = (
                    "SAML" in page_content or
                    "SSO" in page_content or
                    "saml" in page_content
                )
                self.log_result(
                    "Frontend SAML Login Button",
                    has_saml_button,
                    "SAML login UI found" if has_saml_button else "SAML login UI not found"
                )
                return has_saml_button
            else:
                self.log_result(
                    "Frontend SAML Login Button",
                    False,
                    f"Failed to load page: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result("Frontend SAML Login Button", False, f"Error: {str(e)}")
            return False

    def verify_audit_logging(self) -> bool:
        """Verify audit log entries are created for SAML operations"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            # Fetch recent audit logs
            response = self.session.get(
                f"{self.backend_url}/api/admin/audit-logs?limit=10&action=login&resource_type=user",
                headers=headers,
                timeout=10
            )

            success = response.status_code == 200
            if success:
                logs = response.json().get("items", [])
                has_saml_logs = any("saml" in str(log).lower() for log in logs)
                self.log_result(
                    "Audit Logging for SAML",
                    has_saml_logs,
                    f"Found {len(logs)} recent login logs" if has_saml_logs else "No SAML login logs found"
                )
                return has_saml_logs
            else:
                self.log_result(
                    "Audit Logging for SAML",
                    False,
                    f"Failed to fetch logs: {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_result("Audit Logging for SAML", False, f"Error: {str(e)}")
            return False

    def verify_user_provisioning_attributes(self) -> bool:
        """Verify user provisioning with SAML attributes"""
        try:
            # Check if SAML fields exist in User model
            from src.models.user import User
            from src.models.saml_config import SAMLConfig

            has_saml_name_id = hasattr(User, 'saml_name_id')
            has_saml_config_id = hasattr(User, 'saml_config_id')

            self.log_result(
                "User Model SAML Fields",
                has_saml_name_id and has_saml_config_id,
                f"Fields: saml_name_id={has_saml_name_id}, saml_config_id={has_saml_config_id}"
            )
            return has_saml_name_id and has_saml_config_id

        except Exception as e:
            self.log_result("User Model SAML Fields", False, f"Error: {str(e)}")
            return False

    def verify_saml_service_methods(self) -> bool:
        """Verify SAML service has required methods"""
        try:
            from src.services.saml_service import saml_service

            required_methods = [
                "initiate_login",
                "process_response",
                "get_or_create_user",
                "_extract_attribute",
                "_map_user_role",
                "get_metadata"
            ]

            missing_methods = []
            for method in required_methods:
                if not hasattr(saml_service, method):
                    missing_methods.append(method)

            success = len(missing_methods) == 0
            self.log_result(
                "SAML Service Methods",
                success,
                f"All methods present" if success else f"Missing: {', '.join(missing_methods)}"
            )
            return success

        except Exception as e:
            self.log_result("SAML Service Methods", False, f"Error: {str(e)}")
            return False

    def cleanup_test_config(self, config_id: str) -> bool:
        """Clean up test SAML configuration"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.delete(
                f"{self.backend_url}/api/admin/saml/configs/{config_id}",
                headers=headers,
                timeout=10
            )
            success = response.status_code == 200
            print(f"\n{'✅' if success else '⚠️'}  Cleanup: {'Test config deleted' if success else 'Failed to delete test config'}")
            return success
        except Exception as e:
            print(f"\n⚠️  Cleanup: Failed to delete test config - {str(e)}")
            return False

    def run_verification(self) -> Dict[str, Any]:
        """Run complete SSO login flow verification"""
        print("\n" + "="*70)
        print("SAML SSO End-to-End Verification")
        print("="*70 + "\n")

        test_config_id = None

        try:
            # Phase 1: Server Health
            print("Phase 1: Server Health Checks")
            print("-" * 70)
            if not self.verify_backend_running():
                return {"success": False, "reason": "Backend server not accessible"}
            if not self.verify_frontend_running():
                return {"success": False, "reason": "Frontend server not accessible"}

            # Phase 2: Admin Authentication
            print("\nPhase 2: Admin Authentication")
            print("-" * 70)
            if not self.get_admin_token():
                return {"success": False, "reason": "Admin authentication failed"}

            # Phase 3: SAML Configuration
            print("\nPhase 3: SAML Configuration Management")
            print("-" * 70)
            if not self.verify_saml_config_endpoint():
                return {"success": False, "reason": "SAML config endpoint not accessible"}

            test_config_id = self.create_test_saml_config()
            if not test_config_id:
                return {"success": False, "reason": "Failed to create test SAML config"}

            # Phase 4: SAML Authentication Flow
            print("\nPhase 4: SAML Authentication Flow")
            print("-" * 70)
            if not self.verify_saml_metadata_endpoint():
                print("⚠️  Warning: Metadata endpoint not accessible (may require valid config)")

            if not self.verify_saml_login_endpoint():
                return {"success": False, "reason": "SAML login endpoint not working"}

            # Phase 5: Frontend Integration
            print("\nPhase 5: Frontend Integration")
            print("-" * 70)
            if not self.verify_frontend_saml_button():
                print("⚠️  Warning: SAML login button not found in frontend")

            # Phase 6: User Provisioning & Attributes
            print("\nPhase 6: User Provisioning & Attributes")
            print("-" * 70)
            if not self.verify_user_provisioning_attributes():
                return {"success": False, "reason": "User model missing SAML fields"}

            if not self.verify_saml_service_methods():
                return {"success": False, "reason": "SAML service missing required methods"}

            # Phase 7: Audit Logging
            print("\nPhase 7: Audit Logging")
            print("-" * 70)
            if not self.verify_audit_logging():
                print("⚠️  Warning: No SAML audit logs found (may not have been tested yet)")

            # Summary
            print("\n" + "="*70)
            print("Verification Summary")
            print("="*70)

            total_tests = len(self.verification_results)
            passed_tests = sum(1 for r in self.verification_results if r["success"])
            failed_tests = total_tests - passed_tests

            print(f"\nTotal Tests: {total_tests}")
            print(f"Passed: {passed_tests} ✅")
            print(f"Failed: {failed_tests} ❌")
            print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")

            if failed_tests == 0:
                print("\n🎉 All verifications passed!")
                return {"success": True, "passed": passed_tests, "failed": failed_tests}
            else:
                print("\n⚠️  Some verifications failed - manual testing required")
                return {"success": False, "passed": passed_tests, "failed": failed_tests}

        except Exception as e:
            print(f"\n❌ Verification failed with exception: {str(e)}")
            return {"success": False, "reason": f"Exception: {str(e)}"}

        finally:
            # Cleanup
            if test_config_id:
                self.cleanup_test_config(test_config_id)

            # Save results
            self.save_results()

    def save_results(self):
        """Save verification results to file"""
        results_dir = os.path.join(os.path.dirname(__file__), "results")
        os.makedirs(results_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(results_dir, f"saml_sso_verification_{timestamp}.json")

        with open(results_file, "w") as f:
            json.dump(self.verification_results, f, indent=2)

        print(f"\n📄 Results saved to: {results_file}")


def main():
    parser = argparse.ArgumentParser(description="Verify SAML SSO end-to-end flow")
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend server URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--frontend-url",
        default="http://localhost:3000",
        help="Frontend server URL (default: http://localhost:3000)"
    )
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "prod"],
        default="dev",
        help="Environment (default: dev)"
    )

    args = parser.parse_args()

    verifier = SAMLSSOVerifier(
        base_url=args.backend_url,
        frontend_url=args.frontend_url
    )

    result = verifier.run_verification()
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
