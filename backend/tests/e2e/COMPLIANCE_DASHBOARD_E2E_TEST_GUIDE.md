# Compliance Dashboard End-to-End Test Guide

**Feature:** Advanced Security & Compliance Features (Spec 025)
**Subtask:** 8-8 - Verify compliance dashboard displays accurate status
**Test Type:** End-to-End Integration Testing

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Test Environment Setup](#test-environment-setup)
4. [Verification Phases](#verification-phases)
5. [Test Scenarios](#test-scenarios)
6. [Expected Results](#expected-results)
7. [Troubleshooting](#troubleshooting)
8. [Test Results Template](#test-results-template)

---

## Overview

This guide provides comprehensive instructions for end-to-end verification of the compliance dashboard functionality. The compliance dashboard is the central monitoring interface for security and compliance status, displaying SOC 2 and GDPR compliance information, security metrics, and audit log export capabilities.

### What Is Being Tested

The compliance dashboard integrates multiple security features:
- **Compliance Status Display:** SOC 2 and GDPR framework compliance status
- **Security Metrics:** Event counts, severity breakdown, category analysis
- **Data Protection Status:** Encryption, audit logging, access control checks
- **Access Control Status:** Authentication, authorization, session management
- **Security Configuration Summary:** SAML, security policies, IP whitelist, 2FA status
- **Security Events Chart:** Time-series visualization of security events
- **Audit Log Export:** CSV and JSON export functionality for compliance reporting

### Test Objectives

✅ Verify the security dashboard displays accurate compliance status
✅ Verify SOC 2 compliance status displays correctly
✅ Verify GDPR compliance status displays correctly
✅ Verify security metrics charts render properly
✅ Verify audit log export functionality works

---

## Prerequisites

### Required Access

- **Admin Account:** Valid admin user credentials for API and frontend access
- **Database Access:** PostgreSQL database with compliance and audit log data
- **Network Access:** Access to backend and frontend servers

### System Requirements

- **Python:** 3.11+ (for automated verification script)
- **Node.js:** 18+ (for frontend server)
- **Backend Server:** FastAPI server running on port 8000 (default)
- **Frontend Server:** React dev server running on port 3000 (default)

### Test Data

The following test data should exist in the database:
- Admin user account
- Compliance log entries (SOC 2 and GDPR)
- Audit log entries
- Security policies (optional)
- SAML configurations (optional)
- IP whitelist entries (optional)

---

## Test Environment Setup

### 1. Start Backend Server

```bash
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Verify backend is running:
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-23T12:00:00Z"
}
```

### 2. Start Frontend Server

```bash
cd frontend
pnpm dev
```

Verify frontend is running:
- Open browser: `http://localhost:3000`
- Should see application login page

### 3. Verify Database Connectivity

```bash
cd backend
python -c "
from database import SessionLocal
from src.models.compliance_log import ComplianceLog
from src.models.audit_log import AdminAuditLog

db = SessionLocal()
compliance_count = db.query(ComplianceLog).count()
audit_count = db.query(AdminAuditLog).count()
print(f'Compliance logs: {compliance_count}')
print(f'Audit logs: {audit_count}')
db.close()
"
```

### 4. Prepare Authentication

Obtain admin authentication token:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin_password"}'
```

Save the `access_token` from the response for subsequent API calls.

---

## Verification Phases

### Phase 1: Navigate to Security Dashboard

**Objective:** Verify the security dashboard is accessible and renders correctly.

#### Automated Verification

```bash
cd backend
python tests/e2e/verify_compliance_dashboard.py \
  --backend-url http://localhost:8000 \
  --frontend-url http://localhost:3000
```

#### Manual Browser Verification

1. **Login to Application**
   - Navigate to: `http://localhost:3000`
   - Login with admin credentials
   - Verify successful authentication

2. **Navigate to Security Dashboard**
   - Click on "Admin" in navigation menu
   - Click on "Security" or navigate to: `http://localhost:3000/admin/security`
   - Verify page loads without errors

3. **Check Browser Console**
   - Open Developer Tools (F12)
   - Check Console tab for errors
   - Check Network tab for failed requests

**Expected Results:**
- ✅ Dashboard page loads successfully
- ✅ No JavaScript errors in console
- ✅ All API requests return status 200
- ✅ Dashboard displays loading state briefly, then shows data

---

### Phase 2: Verify SOC 2 Compliance Status

**Objective:** Verify SOC 2 compliance status displays correctly with accurate data.

#### API Verification

Test endpoint: `GET /api/admin/security/dashboard?framework=soc2&days=30`

```bash
curl -X GET "http://localhost:8000/api/admin/security/dashboard?framework=soc2&days=30" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response Structure:**

```json
{
  "compliance_status": {
    "framework": "soc2",
    "overall_status": "compliant",
    "non_compliant_events_last_30_days": 0,
    "requirements": [
      {
        "requirement": "Access Control",
        "status": "compliant",
        "description": "System implements proper access controls"
      }
    ],
    "last_checked": "2024-01-23T12:00:00Z"
  },
  "security_metrics": {
    "total_events": 150,
    "by_status": {
      "compliant": 140,
      "non_compliant": 5,
      "pending_review": 5
    },
    "by_severity": {
      "critical": 2,
      "high": 8,
      "medium": 30,
      "low": 110
    },
    "by_category": {
      "access_control": 40,
      "data_protection": 35,
      "audit_logging": 30,
      "encryption": 25,
      "monitoring": 20
    },
    "unresolved_incidents": 10,
    "period": {
      "start": "2023-12-24T00:00:00Z",
      "end": "2024-01-23T00:00:00Z",
      "days": 30
    }
  },
  "data_protection": {
    "overall_status": "compliant",
    "checks": {
      "encryption_at_rest": {
        "status": "pass",
        "description": "Database encryption enabled"
      },
      "encryption_in_transit": {
        "status": "pass",
        "description": "TLS/HTTPS configured"
      },
      "audit_logging": {
        "status": "pass",
        "description": "Comprehensive audit trail"
      },
      "data_retention": {
        "status": "pass",
        "description": "Retention policy enforced"
      }
    },
    "last_checked": "2024-01-23T12:00:00Z"
  },
  "access_control": {
    "overall_status": "compliant",
    "checks": {
      "authentication": {
        "status": "pass",
        "description": "Strong authentication required"
      },
      "authorization": {
        "status": "pass",
        "description": "RBAC implemented"
      },
      "session_management": {
        "status": "pass",
        "description": "Secure session handling"
      },
      "ip_whitelisting": {
        "status": "pass",
        "description": "IP access restrictions enabled"
      }
    },
    "last_checked": "2024-01-23T12:00:00Z"
  },
  "security_configs": {
    "saml_configs_enabled": 2,
    "saml_configs_total": 3,
    "security_policies_enabled": 4,
    "security_policies_total": 5,
    "ip_whitelist_entries": 10,
    "two_factor_enforcement_enabled": true
  },
  "recent_critical_events": [],
  "generated_at": "2024-01-23T12:00:00Z"
}
```

#### Frontend Verification

1. **Check Compliance Status Badge**
   - Locate SOC 2 compliance badge in dashboard
   - Verify status color coding:
     - 🟢 Green: `compliant`
     - 🔴 Red: `non_compliant`
     - 🟡 Yellow: `pending_review`
     - ⚪ Gray: `unknown`

2. **Verify Framework Selection**
   - Use framework dropdown to select "SOC 2"
   - Verify dashboard updates with SOC 2 data
   - Verify "Framework: SOC2" label displays

3. **Check Requirements List**
   - Verify requirements are listed under compliance status
   - Verify each requirement has status indicator
   - Verify status badges are color-coded correctly

**Expected Results:**
- ✅ SOC 2 framework selected
- ✅ Overall status displays correctly (compliant/non_compliant/pending_review)
- ✅ Non-compliant events count is accurate
- ✅ Requirements list displays with status indicators
- ✅ Last checked timestamp is recent

---

### Phase 3: Verify GDPR Compliance Status

**Objective:** Verify GDPR compliance status displays correctly with accurate data.

#### API Verification

Test endpoint: `GET /api/admin/security/dashboard?framework=gdpr&days=30`

```bash
curl -X GET "http://localhost:8000/api/admin/security/dashboard?framework=gdpr&days=30" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response Structure:** Same as SOC 2, but with `framework: "gdpr"`

#### Frontend Verification

1. **Switch to GDPR Framework**
   - Use framework dropdown to select "GDPR"
   - Verify dashboard updates with GDPR data
   - Verify "Framework: GDPR" label displays

2. **Check GDPR-Specific Requirements**
   - Look for GDPR-specific compliance requirements:
     - Data Protection (Article 32)
     - Right to Erasure (Article 17)
     - Right to Data Portability (Article 20)
     - Data Breach Notification (Articles 33-34)
     - Consent Management (Article 7)
     - DPIA (Article 35)

**Expected Results:**
- ✅ GDPR framework selected
- ✅ Overall status displays correctly
- ✅ GDPR-specific requirements are shown
- ✅ Non-compliant events count is accurate
- ✅ Status badges are color-coded correctly

---

### Phase 4: Verify Security Metrics Charts Render

**Objective:** Verify security metrics charts render with correct data visualization.

#### API Verification

Test endpoint: `GET /api/admin/security/security/events?period=7d&interval=day`

```bash
curl -X GET "http://localhost:8000/api/admin/security/security/events?period=7d&interval=day" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response Structure:**

```json
{
  "period": {
    "start": "2024-01-16T00:00:00Z",
    "end": "2024-01-23T00:00:00Z",
    "days": 7
  },
  "interval": "day",
  "total_events": 45,
  "buckets": [
    {
      "timestamp": "2024-01-16T00:00:00Z",
      "total_events": 5,
      "by_severity": {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 2
      },
      "by_status": {
        "compliant": 4,
        "non_compliant": 1,
        "pending_review": 0,
        "resolved": 0
      },
      "by_category": {
        "access_control": 2,
        "data_protection": 1,
        "audit_logging": 1,
        "encryption": 1
      },
      "critical_events": 0,
      "high_events": 1,
      "resolved_events": 0
    }
  ],
  "summary": {
    "resolved_events": 30,
    "critical_events": 2,
    "high_events": 8,
    "unresolved_events": 15
  }
}
```

#### Frontend Verification

1. **Locate Security Metrics Chart**
   - Scroll to "Security Events History" section
   - Verify chart container is visible

2. **Verify Chart Renders**
   - Verify chart area displays with proper dimensions
   - Verify axes (X-axis: dates, Y-axis: event counts)
   - Verify data series render correctly:
     - 🔴 Critical events (red area)
     - 🟠 High events (orange area)
     - 🟡 Medium events (yellow area)
     - 🔵 Low events (blue area)

3. **Check Chart Interactivity**
   - Hover over chart data points
   - Verify tooltip displays with event breakdown
   - Verify legend is visible and interactive

4. **Test Time Period Selection**
   - Change time period dropdown (7d, 30d, 90d, 1y)
   - Verify chart updates with new data
   - Verify X-axis labels adjust to period

**Expected Results:**
- ✅ Chart renders without errors
- ✅ All data series display with correct colors
- ✅ Tooltips show accurate information
- ✅ Legend displays all severity levels
- ✅ Chart is responsive to window resizing
- ✅ Time period selection updates chart

---

### Phase 5: Verify Audit Log Export Functionality

**Objective:** Verify audit log export works in both JSON and CSV formats.

#### JSON Export Verification

**Test 1: Basic JSON Export**

```bash
curl -X GET "http://localhost:8000/api/admin/audit-logs/export?format=json&limit=10" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -o audit_logs_export.json
```

**Expected Response Structure:**

```json
{
  "export_date": "2024-01-23T12:00:00Z",
  "export_type": "audit_logs",
  "format": "json",
  "total_records": 10,
  "date_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-23T12:00:00Z"
  },
  "logs": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "timestamp": "2024-01-23T11:00:00Z",
      "user_id": "user-uuid",
      "user_email": "admin@example.com",
      "action": "create",
      "resource_type": "user",
      "resource_id": "resource-uuid",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "details": {
        "user_email": "newuser@example.com",
        "role": "user"
      }
    }
  ]
}
```

**Verification Steps:**
1. ✅ Response status code is 200
2. ✅ Content-Type is `application/json`
3. ✅ `format` field is `"json"`
4. ✅ `logs` array contains `total_records` entries
5. ✅ Each log entry has all required fields
6. ✅ Timestamps are valid ISO 8601 format
7. ✅ `details` field is parsed as JSON object

**Test 2: Filtered JSON Export**

```bash
curl -X GET "http://localhost:8000/api/admin/audit-logs/export?format=json&action=delete&limit=5" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Results:**
- ✅ Only logs with `action: "delete"` are returned
- ✅ Maximum 5 records returned
- ✅ Response structure is valid

#### CSV Export Verification

**Test 3: Basic CSV Export**

```bash
curl -X GET "http://localhost:8000/api/admin/audit-logs/export?format=csv&limit=10" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -o audit_logs_export.csv
```

**Verification Steps:**
1. ✅ Response status code is 200
2. ✅ Content-Type contains `text/csv` or `application/csv`
3. ✅ Content-Disposition header contains `attachment` and `.csv`
4. ✅ File is downloadable
5. ✅ CSV has header row with expected columns:
   - Timestamp
   - User ID
   - User Email
   - Action
   - Resource Type
   - Resource ID
   - IP Address
   - User Agent
   - Details
6. ✅ Data rows have correct number of fields
7. ✅ Timestamps are valid ISO 8601 format

**Test 4: Verify CSV Format**

```bash
# View first few lines
head -n 5 audit_logs_export.csv

# Count rows (excluding header)
tail -n +2 audit_logs_export.csv | wc -l
```

**Expected Results:**
- ✅ Header row is present
- ✅ Data rows match requested limit (10)
- ✅ Fields are properly comma-separated
- ✅ Special characters are properly quoted

#### Frontend Export Verification

1. **Locate Export Button**
   - Find "Export Logs" button in dashboard header
   - Verify button is visible and enabled

2. **Test Export Functionality**
   - Click "Export Logs" button
   - Verify export notification appears
   - Verify file download starts
   - Check downloaded file content

**Expected Results:**
- ✅ Export button triggers download
- ✅ Toast notification shows export started
- ✅ File downloads with proper naming: `audit_logs_YYYYMMDD_HHMMSS.csv`
- ✅ File content matches API response

---

## Test Scenarios

### Scenario 1: Fresh Dashboard Load

**Steps:**
1. Clear browser cache and cookies
2. Login as admin
3. Navigate to security dashboard
4. Wait for initial data load

**Expected Results:**
- ✅ Loading skeleton displays briefly
- ✅ Dashboard loads within 3 seconds
- ✅ All sections display data
- ✅ No console errors

### Scenario 2: Framework Switching

**Steps:**
1. Load dashboard with SOC 2 framework
2. Note the compliance status and metrics
3. Switch to GDPR framework
4. Verify data updates
5. Switch back to SOC 2

**Expected Results:**
- ✅ Framework selection persists
- ✅ Data updates correctly on each switch
- ✅ No duplicate API calls
- ✅ UI updates smoothly

### Scenario 3: Time Period Changes

**Steps:**
1. Load dashboard with 7-day period
2. Note the event counts and chart
3. Change to 30-day period
4. Verify metrics and chart update
5. Change to 90-day period

**Expected Results:**
- ✅ Event counts increase appropriately
- ✅ Chart shows more data points
- ✅ All metrics reflect selected period
- ✅ No data loss or corruption

### Scenario 4: Export with Filters

**Steps:**
1. Navigate to security dashboard
2. Use framework filter to select SOC 2
3. Click export logs button
4. Verify exported data matches dashboard

**Expected Results:**
- ✅ Export includes correct framework
- ✅ Date range matches dashboard
- ✅ All critical events are included
- ✅ File is valid and parseable

### Scenario 5: Error Handling

**Steps:**
1. Stop backend server
2. Try to load dashboard
3. Check error messages
4. Restart backend server
5. Refresh dashboard

**Expected Results:**
- ✅ User-friendly error message displays
- ✅ No unhandled exceptions
- ✅ Retry mechanism works
- ✅ Dashboard recovers when backend is available

---

## Expected Results Summary

### Dashboard Display

| Element | Expected State |
|---------|---------------|
| Framework Selector | Dropdown with SOC 2 and GDPR options |
| Compliance Status | Color-coded badge (green/red/yellow) |
| Requirements List | All requirements with status indicators |
| Metrics Cards | Total events, unresolved incidents, policies, critical events |
| Data Protection | Status checks with pass/fail indicators |
| Access Control | Status checks with pass/fail indicators |
| Security Configs | Progress bars for SAML and policies |
| Recent Events | List of critical/high severity events |
| Security Chart | Stacked area chart with 4 severity levels |
| Export Button | Triggers file download |

### API Endpoints

| Endpoint | Method | Status | Response Time |
|----------|--------|--------|---------------|
| `/api/admin/security/dashboard` | GET | 200 | < 500ms |
| `/api/admin/security/dashboard/metrics` | GET | 200 | < 300ms |
| `/api/admin/security/dashboard/compliance/{framework}` | GET | 200 | < 300ms |
| `/api/admin/security/dashboard/data-protection` | GET | 200 | < 200ms |
| `/api/admin/security/dashboard/access-control` | GET | 200 | < 200ms |
| `/api/admin/security/dashboard/security-configs` | GET | 200 | < 200ms |
| `/api/admin/security/dashboard/recent-events` | GET | 200 | < 300ms |
| `/api/admin/security/security/events` | GET | 200 | < 500ms |
| `/api/admin/audit-logs/export` | GET | 200 | < 2s |

### Data Validation

| Data Field | Validation Rule |
|------------|----------------|
| `framework` | Must be "soc2" or "gdpr" |
| `overall_status` | Must be one of: compliant, non_compliant, pending_review, unknown |
| `total_events` | Non-negative integer |
| `non_compliant_events_last_30_days` | Non-negative integer |
| `timestamp` | Valid ISO 8601 format |
| `severity` | One of: critical, high, medium, low |
| `compliance_status` | One of: compliant, non_compliant, pending_review, resolved |

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Dashboard Shows "No Data Available"

**Possible Causes:**
- No compliance logs in database
- Backend service error
- Incorrect API endpoint configuration

**Solutions:**
1. Check browser console for errors
2. Verify backend is running: `curl http://localhost:8000/api/health`
3. Check database has compliance logs:
   ```sql
   SELECT COUNT(*) FROM compliance_log;
   ```
4. Add sample compliance data if needed

#### Issue 2: Chart Does Not Render

**Possible Causes:**
- Recharts library not loaded
- Invalid data format from API
- CSS conflicts

**Solutions:**
1. Check Network tab for API response
2. Verify `buckets` array is not empty
3. Check console for Recharts errors
4. Verify chart container has non-zero dimensions

#### Issue 3: Export Button Does Nothing

**Possible Causes:**
- Frontend function not implemented
- Backend endpoint not responding
- CORS issues

**Solutions:**
1. Check browser console for errors
2. Verify export endpoint is accessible:
   ```bash
   curl -X GET "http://localhost:8000/api/admin/audit-logs/export?format=json&limit=1" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
3. Check Network tab for failed requests
4. Verify export function is wired to button

#### Issue 4: Status Colors Not Showing

**Possible Causes:**
- Tailwind CSS not loaded
- CSS variable conflicts
- Dark mode styling issues

**Solutions:**
1. Check browser dev tools for applied styles
2. Verify Tailwind CSS is loaded
3. Check for CSS override conflicts
4. Test in both light and dark modes

#### Issue 5: Framework Switch Does Not Update Dashboard

**Possible Causes:**
- React query not refetching
- State not updating
- API not responding with new data

**Solutions:**
1. Check React Query DevTools
2. Verify query key includes framework parameter
3. Check Network tab for API calls
4. Manually trigger refetch

---

## Test Results Template

Use this template to document test results:

```markdown
# Compliance Dashboard E2E Test Results

**Test Date:** YYYY-MM-DD
**Tester:** [Name]
**Environment:** [dev/staging/prod]
**Backend Version:** [version]
**Frontend Version:** [version]

## Test Execution Summary

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Navigate to Dashboard | ✅/❌ | |
| Phase 2: SOC 2 Compliance Status | ✅/❌ | |
| Phase 3: GDPR Compliance Status | ✅/❌ | |
| Phase 4: Security Metrics Charts | ✅/❌ | |
| Phase 5: Audit Log Export (JSON) | ✅/❌ | |
| Phase 5: Audit Log Export (CSV) | ✅/❌ | |

## Detailed Results

### Phase 1: Navigate to Security Dashboard
- [x] Dashboard loads successfully
- [x] No console errors
- [x] All API requests return 200

**Issues Found:**
- [List any issues]

### Phase 2: SOC 2 Compliance Status
- [x] SOC 2 framework selectable
- [x] Overall status displays correctly
- [x] Requirements list shows all items
- [x] Status badges color-coded correctly

**Issues Found:**
- [List any issues]

### Phase 3: GDPR Compliance Status
- [x] GDPR framework selectable
- [x] GDPR-specific requirements shown
- [x] Overall status displays correctly

**Issues Found:**
- [List any issues]

### Phase 4: Security Metrics Charts
- [x] Chart renders without errors
- [x] All data series display correctly
- [x] Tooltips show accurate information
- [x] Time period selection works

**Issues Found:**
- [List any issues]

### Phase 5: Audit Log Export
- [x] JSON export works
- [x] CSV export works
- [x] Filters work correctly
- [x] File downloads with proper name

**Issues Found:**
- [List any issues]

## Automated Script Results

```bash
# Run automated verification
python tests/e2e/verify_compliance_dashboard.py

# Output
Total Checks: 15
Passed: 14 ✅
Failed: 1 ❌
Success Rate: 93.3%
```

## Screenshots

[Attach relevant screenshots]

## Performance Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Dashboard Load Time | [ms] | < 3000ms |
| API Response Time (Dashboard) | [ms] | < 500ms |
| API Response Time (Events) | [ms] | < 500ms |
| Export Time (1000 records) | [ms] | < 2000ms |

## Defects Found

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| 1 | [High/Med/Low] | [Description] | [Open/Fixed] |

## Recommendations

[List any recommendations for improvements]

## Sign-off

**Tester Signature:** _________________ **Date:** _______

**Reviewer Signature:** _________________ **Date:** _______
```

---

## Quick Reference Commands

```bash
# Run automated verification
python backend/tests/e2e/verify_compliance_dashboard.py

# Generate report with output
python backend/tests/e2e/verify_compliance_dashboard.py --output report.json

# Test specific endpoints
curl -X GET "http://localhost:8000/api/admin/security/dashboard?framework=soc2&days=30" \
  -H "Authorization: Bearer YOUR_TOKEN"

curl -X GET "http://localhost:8000/api/admin/security/security/events?period=7d&interval=day" \
  -H "Authorization: Bearer YOUR_TOKEN"

curl -X GET "http://localhost:8000/api/admin/audit-logs/export?format=json&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

curl -X GET "http://localhost:8000/api/admin/audit-logs/export?format=csv&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN" -o audit_logs.csv

# Check database for test data
python -c "
from database import SessionLocal
from src.models.compliance_log import ComplianceLog
from src.models.audit_log import AdminAuditLog

db = SessionLocal()
print(f'Compliance logs: {db.query(ComplianceLog).count()}')
print(f'Audit logs: {db.query(AdminAuditLog).count()}')
db.close()
"
```

---

## Conclusion

This comprehensive test guide ensures the compliance dashboard is thoroughly verified end-to-end. The combination of automated scripts and manual testing provides confidence that:

1. ✅ The security dashboard displays accurate compliance status
2. ✅ SOC 2 and GDPR compliance status display correctly
3. ✅ Security metrics charts render properly
4. ✅ Audit log export functionality works correctly

Following this guide ensures the compliance dashboard meets enterprise requirements for security monitoring and compliance reporting.

---

**Document Version:** 1.0
**Last Updated:** 2024-01-23
**Maintained By:** Security & Compliance Team
