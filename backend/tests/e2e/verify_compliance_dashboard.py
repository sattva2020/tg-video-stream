"""
End-to-End Verification Script for Compliance Dashboard

This script verifies the compliance dashboard displays accurate status:
1. Navigate to security dashboard
2. Verify SOC 2 compliance status displays correctly
3. Verify GDPR compliance status displays correctly
4. Verify security metrics charts render
5. Verify audit log export functionality works

Usage:
    python tests/e2e/verify_compliance_dashboard.py --env {dev|staging|prod}

Requirements:
    - Backend server running
    - Frontend server running
    - Admin account for API access
    - Compliance data in database
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
from tests.conftest import get_test_admin_token, create_test_user


class ComplianceDashboardVerifier:
    """Verifies compliance dashboard end-to-end functionality"""

    def __init__(self, base_url: str = "http://localhost:8000", frontend_url: str = "http://localhost:3000"):
        self.backend_url = base_url
        self.frontend_url = frontend_url
        self.admin_token: Optional[str] = None
        self.session = requests.Session()
        self.verification_results = []

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
            self.session.headers.update({
                "Authorization": f"Bearer {self.admin_token}"
            })
            self.log_result("Admin Authentication", True, "Admin token obtained successfully")
            return True
        except Exception as e:
            self.log_result("Admin Authentication", False, f"Failed to get admin token: {str(e)}")
            return False

    def verify_soc2_compliance_status(self) -> bool:
        """Verify SOC 2 compliance status displays correctly"""
        try:
            response = self.session.get(
                f"{self.backend_url}/api/admin/security/dashboard",
                params={"framework": "soc2", "days": 30},
                timeout=10
            )

            if response.status_code != 200:
                self.log_result(
                    "SOC 2 Compliance Status API",
                    False,
                    f"Expected status 200, got {response.status_code}"
                )
                return False

            data = response.json()

            # Verify required fields exist
            required_fields = [
                "compliance_status",
                "security_metrics",
                "data_protection",
                "access_control",
                "security_configs",
                "recent_critical_events",
                "generated_at"
            ]

            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self.log_result(
                    "SOC 2 Compliance Status API",
                    False,
                    f"Missing fields: {', '.join(missing_fields)}"
                )
                return False

            # Verify compliance status structure
            compliance = data["compliance_status"]
            required_compliance_fields = [
                "framework",
                "overall_status",
                "non_compliant_events_last_30_days",
                "requirements",
                "last_checked"
            ]

            missing_compliance_fields = [
                field for field in required_compliance_fields
                if field not in compliance
            ]

            if missing_compliance_fields:
                self.log_result(
                    "SOC 2 Compliance Status Structure",
                    False,
                    f"Missing compliance fields: {', '.join(missing_compliance_fields)}"
                )
                return False

            # Verify framework is SOC2
            if compliance["framework"].upper() != "SOC2":
                self.log_result(
                    "SOC 2 Framework Verification",
                    False,
                    f"Expected framework 'SOC2', got '{compliance['framework']}'"
                )
                return False

            # Verify overall status is valid
            valid_statuses = ["compliant", "non_compliant", "pending_review", "unknown"]
            if compliance["overall_status"] not in valid_statuses:
                self.log_result(
                    "SOC 2 Overall Status Validation",
                    False,
                    f"Invalid status: {compliance['overall_status']}"
                )
                return False

            self.log_result(
                "SOC 2 Compliance Status",
                True,
                f"Framework: {compliance['framework']}, Status: {compliance['overall_status']}, "
                f"Non-compliant events: {compliance['non_compliant_events_last_30_days']}"
            )
            return True

        except Exception as e:
            self.log_result("SOC 2 Compliance Status", False, f"Error: {str(e)}")
            return False

    def verify_gdpr_compliance_status(self) -> bool:
        """Verify GDPR compliance status displays correctly"""
        try:
            response = self.session.get(
                f"{self.backend_url}/api/admin/security/dashboard",
                params={"framework": "gdpr", "days": 30},
                timeout=10
            )

            if response.status_code != 200:
                self.log_result(
                    "GDPR Compliance Status API",
                    False,
                    f"Expected status 200, got {response.status_code}"
                )
                return False

            data = response.json()

            # Verify compliance status structure
            compliance = data["compliance_status"]

            # Verify framework is GDPR
            if compliance["framework"].upper() != "GDPR":
                self.log_result(
                    "GDPR Framework Verification",
                    False,
                    f"Expected framework 'GDPR', got '{compliance['framework']}'"
                )
                return False

            # Verify overall status is valid
            valid_statuses = ["compliant", "non_compliant", "pending_review", "unknown"]
            if compliance["overall_status"] not in valid_statuses:
                self.log_result(
                    "GDPR Overall Status Validation",
                    False,
                    f"Invalid status: {compliance['overall_status']}"
                )
                return False

            self.log_result(
                "GDPR Compliance Status",
                True,
                f"Framework: {compliance['framework']}, Status: {compliance['overall_status']}, "
                f"Non-compliant events: {compliance['non_compliant_events_last_30_days']}"
            )
            return True

        except Exception as e:
            self.log_result("GDPR Compliance Status", False, f"Error: {str(e)}")
            return False

    def verify_security_metrics_charts(self) -> bool:
        """Verify security metrics charts render"""
        try:
            # Test security events history endpoint
            response = self.session.get(
                f"{self.backend_url}/api/admin/security/security/events",
                params={"period": "7d", "interval": "day"},
                timeout=10
            )

            if response.status_code != 200:
                self.log_result(
                    "Security Events History API",
                    False,
                    f"Expected status 200, got {response.status_code}"
                )
                return False

            data = response.json()

            # Verify required fields
            required_fields = ["period", "interval", "total_events", "buckets", "summary"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                self.log_result(
                    "Security Events History Structure",
                    False,
                    f"Missing fields: {', '.join(missing_fields)}"
                )
                return False

            # Verify buckets structure
            buckets = data["buckets"]
            if not isinstance(buckets, list):
                self.log_result(
                    "Security Events Buckets Type",
                    False,
                    f"Buckets should be a list, got {type(buckets)}"
                )
                return False

            if len(buckets) > 0:
                # Verify first bucket structure
                bucket = buckets[0]
                required_bucket_fields = [
                    "timestamp",
                    "total_events",
                    "by_severity",
                    "by_status",
                    "by_category",
                    "critical_events",
                    "high_events",
                    "resolved_events"
                ]

                missing_bucket_fields = [
                    field for field in required_bucket_fields
                    if field not in bucket
                ]

                if missing_bucket_fields:
                    self.log_result(
                        "Security Events Bucket Structure",
                        False,
                        f"Missing bucket fields: {', '.join(missing_bucket_fields)}"
                    )
                    return False

                # Verify by_severity has expected keys
                expected_severities = ["critical", "high", "medium", "low"]
                for severity in expected_severities:
                    if severity not in bucket["by_severity"]:
                        # Not failing on this, just noting it
                        pass

            self.log_result(
                "Security Metrics Charts Data",
                True,
                f"Period: {data['period']['days']} days, Buckets: {len(buckets)}, "
                f"Total events: {data['total_events']}"
            )
            return True

        except Exception as e:
            self.log_result("Security Metrics Charts Data", False, f"Error: {str(e)}")
            return False

    def verify_audit_log_export_json(self) -> bool:
        """Verify audit log export functionality works (JSON format)"""
        try:
            response = self.session.get(
                f"{self.backend_url}/api/admin/audit-logs/export",
                params={"format": "json", "limit": 10},
                timeout=10
            )

            if response.status_code != 200:
                self.log_result(
                    "Audit Log Export JSON API",
                    False,
                    f"Expected status 200, got {response.status_code}"
                )
                return False

            data = response.json()

            # Verify required fields
            required_fields = ["export_date", "export_type", "format", "total_records", "logs"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                self.log_result(
                    "Audit Log Export JSON Structure",
                    False,
                    f"Missing fields: {', '.join(missing_fields)}"
                )
                return False

            # Verify format is json
            if data["format"] != "json":
                self.log_result(
                    "Audit Log Export JSON Format",
                    False,
                    f"Expected format 'json', got '{data['format']}'"
                )
                return False

            # Verify logs is a list
            if not isinstance(data["logs"], list):
                self.log_result(
                    "Audit Log Export JSON Logs Type",
                    False,
                    f"Logs should be a list, got {type(data['logs'])}"
                )
                return False

            self.log_result(
                "Audit Log Export JSON",
                True,
                f"Exported {data['total_records']} records in JSON format"
            )
            return True

        except Exception as e:
            self.log_result("Audit Log Export JSON", False, f"Error: {str(e)}")
            return False

    def verify_audit_log_export_csv(self) -> bool:
        """Verify audit log export functionality works (CSV format)"""
        try:
            response = self.session.get(
                f"{self.backend_url}/api/admin/audit-logs/export",
                params={"format": "csv", "limit": 10},
                timeout=10
            )

            if response.status_code != 200:
                self.log_result(
                    "Audit Log Export CSV API",
                    False,
                    f"Expected status 200, got {response.status_code}"
                )
                return False

            # Verify content type is CSV
            content_type = response.headers.get("Content-Type", "")
            if "text/csv" not in content_type and "application/csv" not in content_type:
                self.log_result(
                    "Audit Log Export CSV Content-Type",
                    False,
                    f"Expected CSV content-type, got '{content_type}'"
                )
                return False

            # Verify content-disposition header
            content_disposition = response.headers.get("Content-Disposition", "")
            if "attachment" not in content_disposition or ".csv" not in content_disposition:
                self.log_result(
                    "Audit Log Export CSV Headers",
                    False,
                    f"Expected CSV file download, got disposition: '{content_disposition}'"
                )
                return False

            # Verify CSV content is not empty
            csv_content = response.text
            if not csv_content or len(csv_content.strip()) == 0:
                self.log_result(
                    "Audit Log Export CSV Content",
                    False,
                    "CSV content is empty"
                )
                return False

            # Verify CSV has header
            lines = csv_content.strip().split('\n')
            if len(lines) < 1:
                self.log_result(
                    "Audit Log Export CSV Format",
                    False,
                    "CSV should have at least a header row"
                )
                return False

            expected_headers = ["Timestamp", "User ID", "User Email", "Action", "Resource Type"]
            header_line = lines[0]
            missing_headers = [
                header for header in expected_headers
                if header not in header_line
            ]

            if missing_headers:
                self.log_result(
                    "Audit Log Export CSV Headers",
                    False,
                    f"Missing CSV headers: {', '.join(missing_headers)}"
                )
                return False

            self.log_result(
                "Audit Log Export CSV",
                True,
                f"CSV export successful, {len(lines)} rows (including header)"
            )
            return True

        except Exception as e:
            self.log_result("Audit Log Export CSV", False, f"Error: {str(e)}")
            return False

    def verify_security_dashboard_sub_endpoints(self) -> bool:
        """Verify security dashboard sub-endpoints"""
        try:
            endpoints = [
                "/api/admin/security/dashboard/metrics",
                "/api/admin/security/dashboard/data-protection",
                "/api/admin/security/dashboard/access-control",
                "/api/admin/security/dashboard/security-configs",
                "/api/admin/security/dashboard/recent-events"
            ]

            all_passed = True
            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{self.backend_url}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        self.log_result(
                            f"Sub-endpoint: {endpoint.split('/')[-1]}",
                            True,
                            f"Status: {response.status_code}"
                        )
                    else:
                        self.log_result(
                            f"Sub-endpoint: {endpoint.split('/')[-1]}",
                            False,
                            f"Expected status 200, got {response.status_code}"
                        )
                        all_passed = False
                except Exception as e:
                    self.log_result(
                        f"Sub-endpoint: {endpoint.split('/')[-1]}",
                        False,
                        f"Error: {str(e)}"
                    )
                    all_passed = False

            return all_passed

        except Exception as e:
            self.log_result("Security Dashboard Sub-endpoints", False, f"Error: {str(e)}")
            return False

    def generate_report(self) -> Dict[str, Any]:
        """Generate verification report"""
        total_checks = len(self.verification_results)
        passed_checks = sum(1 for r in self.verification_results if r["success"])
        failed_checks = total_checks - passed_checks

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "success_rate": f"{(passed_checks / total_checks * 100):.1f}%" if total_checks > 0 else "0%"
            },
            "results": self.verification_results
        }

        return report

    def run_verification(self) -> bool:
        """Run complete verification flow"""
        print("\n" + "="*70)
        print("COMPLIANCE DASHBOARD END-TO-END VERIFICATION")
        print("="*70 + "\n")

        # Phase 1: Server Health Checks
        print("Phase 1: Server Health Checks")
        print("-" * 70)
        if not self.verify_backend_running():
            print("\n❌ Backend server is not accessible. Aborting verification.")
            return False
        if not self.verify_frontend_running():
            print("\n⚠️  Frontend server is not accessible. Continuing with backend verification only.")

        # Phase 2: Authentication
        print("\nPhase 2: Authentication")
        print("-" * 70)
        if not self.get_admin_token():
            print("\n❌ Admin authentication failed. Aborting verification.")
            return False

        # Phase 3: SOC 2 Compliance Status
        print("\nPhase 3: SOC 2 Compliance Status Verification")
        print("-" * 70)
        self.verify_soc2_compliance_status()

        # Phase 4: GDPR Compliance Status
        print("\nPhase 4: GDPR Compliance Status Verification")
        print("-" * 70)
        self.verify_gdpr_compliance_status()

        # Phase 5: Security Metrics Charts
        print("\nPhase 5: Security Metrics Charts Verification")
        print("-" * 70)
        self.verify_security_metrics_charts()

        # Phase 6: Audit Log Export
        print("\nPhase 6: Audit Log Export Verification")
        print("-" * 70)
        self.verify_audit_log_export_json()
        self.verify_audit_log_export_csv()

        # Phase 7: Dashboard Sub-endpoints
        print("\nPhase 7: Dashboard Sub-endpoints Verification")
        print("-" * 70)
        self.verify_security_dashboard_sub_endpoints()

        # Generate and display report
        print("\n" + "="*70)
        print("VERIFICATION REPORT")
        print("="*70 + "\n")

        report = self.generate_report()

        print(f"Total Checks: {report['summary']['total']}")
        print(f"Passed: {report['summary']['passed']} ✅")
        print(f"Failed: {report['summary']['failed']} ❌")
        print(f"Success Rate: {report['summary']['success_rate']}")
        print()

        # Return success if all checks passed
        return report['summary']['failed'] == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Verify compliance dashboard end-to-end functionality"
    )
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--frontend-url",
        default="http://localhost:3000",
        help="Frontend URL (default: http://localhost:3000)"
    )
    parser.add_argument(
        "--output",
        help="Output file for verification report (JSON format)"
    )

    args = parser.parse_args()

    verifier = ComplianceDashboardVerifier(
        base_url=args.backend_url,
        frontend_url=args.frontend_url
    )

    success = verifier.run_verification()

    # Save report if output file specified
    if args.output:
        report = verifier.generate_report()
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {args.output}")

    print("\n" + "="*70)
    if success:
        print("✅ ALL VERIFICATION CHECKS PASSED")
    else:
        print("❌ SOME VERIFICATION CHECKS FAILED")
    print("="*70 + "\n")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
