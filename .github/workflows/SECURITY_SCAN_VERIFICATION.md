# Security Scanning Verification Guide

## Subtask: subtask-8-9
**Phase:** Integration & End-to-End Testing
**Service:** all

## Purpose
Verify that the enhanced security scanning workflow is working correctly and all scanners pass.

## Pre-verification Checklist

### 1. File Structure Verification
```bash
# Verify workflow file exists
ls -la .github/workflows/security-scan.yml

# Verify ZAP rules exist
ls -la .zap/rules.tsv

# Verify dependency files exist
ls -la backend/requirements.txt
ls -la frontend/package.json
```

**Expected Output:**
- ✅ All files exist and are readable

### 2. Workflow Syntax Verification
```bash
# If you have yamllint installed
yamllint .github/workflows/security-scan.yml

# Or use GitHub's workflow validator
# (upload to GitHub and check for syntax errors)
```

**Expected Output:**
- ✅ No YAML syntax errors

## Manual Verification Steps

### Step 1: Trigger Security Scan

**Option A: Push to Main Branch**
```bash
git add .
git commit -m "test: trigger security scan verification"
git push origin main
```

**Option B: Manual Workflow Dispatch**
1. Go to GitHub repository → Actions tab
2. Select "Security Scan" workflow
3. Click "Run workflow" button
4. Select branch and enable "full_scan" option
5. Click "Run workflow"

**Option C: Pull Request**
```bash
git checkout -b test/security-scan-verification
git push origin test/security-scan-verification
# Create PR on GitHub
```

### Step 2: Monitor Workflow Execution

Navigate to: `https://github.com/<org>/<repo>/actions/workflows/security-scan.yml`

**Expected Jobs:**
1. ✅ Semgrep SAST
2. ✅ CodeQL Analysis (JavaScript, Python)
3. ✅ Dependency Audit
4. ✅ Generate SBOM
5. ✅ Trivy Container Scan
6. ✅ Secret Scan
7. ✅ Bandit Python Security
8. ✅ OWASP ZAP DAST (only if full_scan enabled)
9. ✅ Security Report

**Expected Status:**
- All SAST/DAST jobs should show green checkmarks ✅
- Security Report should show Grade A (90-100)

### Step 3: Verify Job Outputs

#### 3.1 Semgrep SAST
- **Check:** Click on "Semgrep SAST" job
- **Verify:**
  - [x] Job completed successfully
  - [x] No critical/high severity findings
  - [x] SARIF file uploaded as artifact
  - [x] Results available in GitHub Security tab

#### 3.2 CodeQL Analysis
- **Check:** Click on "CodeQL Analysis" job
- **Verify:**
  - [x] Both JavaScript and Python scans completed
  - [x] No security queries failed
  - [x] Results uploaded to GitHub Security

#### 3.3 Dependency Audit
- **Check:** Click on "Dependency Audit" job → View "Summary"
- **Verify:**
  - [x] Python dependencies scanned with pip-audit
  - [x] Node dependencies scanned with pnpm audit
  - [x] No known critical vulnerabilities
  - [x] Findings documented in job summary

#### 3.4 SBOM Generation
- **Check:** Click on "Generate SBOM" job
- **Verify:**
  - [x] Job completed successfully
  - [x] 5 SBOM files generated:
    - backend-sbom.json (CycloneDX)
    - backend-sbom-spdx.json (SPDX)
    - frontend-sbom.json (CycloneDX)
    - frontend-sbom-spdx.json (SPDX)
    - backend-image-sbom.json (CycloneDX)
  - [x] All files available in artifacts

#### 3.5 Trivy Container Scan
- **Check:** Click on "Trivy Container Scan" job
- **Verify:**
  - [x] Backend image scanned
  - [x] Frontend image scanned
  - [x] Filesystem scanned
  - [x] All 3 SARIF files uploaded to GitHub Security tab
  - [x] No CRITICAL vulnerabilities

#### 3.6 Secret Scan
- **Check:** Click on "Secret Scan" job
- **Verify:**
  - [x] Gitleaks scan completed
  - [x] No secrets detected (or reviewed if any found)
  - [x] Report uploaded as artifact
  - [x] Results in GitHub Security tab (if enabled)

#### 3.7 Bandit Python Security
- **Check:** Click on "Bandit Python Security" job
- **Verify:**
  - [x] Bandit scan completed on backend/
  - [x] SARIF file uploaded to GitHub Security
  - [x] JSON report available as artifact
  - [x] No high/critical severity issues

#### 3.8 ZAP DAST (if full_scan enabled)
- **Check:** Click on "OWASP ZAP DAST" job
- **Verify:**
  - [x] Services started (postgres, redis, backend, frontend)
  - [x] Baseline scan completed
  - [x] API scan completed
  - [x] No FAIL-level violations in .zap/rules.tsv
  - [x] Reports uploaded as artifacts (HTML, JSON)

#### 3.9 Security Report
- **Check:** Click on "Security Report" job → View "Summary"
- **Verify:**
  - [x] All scanner statuses shown
  - [x] Overall status: PASSED ✅
  - [x] Security score: Grade A (90-100)
  - [x] Quick links to GitHub Security tabs
  - [x] All artifacts uploaded

### Step 4: Verify GitHub Security Tab

Navigate to: `https://github.com/<org>/<repo>/security`

#### 4.1 Code Scanning
- **Check:** Code Scanning tab
- **Verify:**
  - [x] Semgrep results visible
  - [x] CodeQL results visible
  - [x] Bandit results visible
  - [x] Trivy results visible (3 categories: backend, frontend, filesystem)
  - [x] Can filter by severity and tool

#### 4.2 Secret Scanning
- **Check:** Secret Scanning tab
- **Verify:**
  - [x] Gitleaks results shown (if any)
  - [x] Can view secret details
  - [x] Can dismiss false positives

#### 4.3 Dependency Review
- **Check:** Dependencies tab (if enabled)
- **Verify:**
  - [x] Dependency alerts visible
  - [x] Can review affected packages
  - [x] Update suggestions available

### Step 5: Download and Verify Artifacts

Navigate to workflow run → Scroll to "Artifacts" section

**Expected Artifacts:**
1. ✅ semgrep-results (SARIF)
2. ✅ trivy-results (3 SARIF files)
3. ✅ gitleaks-report (JSON)
4. ✅ bandit-results (JSON + SARIF)
5. ✅ sbom-reports (5 SBOM files)
6. ✅ zap-results (HTML + JSON, if DAST ran)
7. ✅ security-report-combined (all reports)

**Verification:**
```bash
# Download artifacts and verify contents
# After download and extraction:
ls -la semgrep-results/
ls -la trivy-results/
ls -la sbom-reports/

# Verify SBOMs are valid JSON
cat sbom-reports/backend-sbom.json | jq . > /dev/null && echo "✅ Valid JSON"
cat sbom-reports/frontend-sbom.json | jq . > /dev/null && echo "✅ Valid JSON"

# Verify SBOM structure
cat sbom-reports/backend-sbom.json | jq '.bomFormat'
# Expected: "CycloneDX"
```

### Step 6: Verify Compliance Documentation

**For SOC 2:**
- [x] SBOMs available for dependency tracking (A1.2)
- [x] Vulnerability scans documented (CC8.1)
- [x] Security testing evidence (CC7.2)

**For GDPR:**
- [x] Technical security measures documented (Article 32)
- [x] Data protection by design verification (Article 25)
- [x] Processing activity records support (Article 30)

## Troubleshooting

### Issue: Workflow fails with YAML syntax error
**Solution:**
```bash
# Check for common YAML issues:
# - Indentation (use spaces, not tabs)
# - Colon after job names
# - Correct array syntax
# - No trailing spaces
```

### Issue: Trivy scan fails with "image not found"
**Solution:**
```bash
# Verify Dockerfiles exist
ls -la backend/Dockerfile
ls -la frontend/Dockerfile

# Verify images build successfully
docker build -t test-backend -f backend/Dockerfile backend/
docker build -t test-frontend -f frontend/Dockerfile frontend/
```

### Issue: ZAP scan fails with "connection refused"
**Solution:**
- Verify backend/frontend start correctly with test database
- Check health endpoints are accessible
- Review service startup logs in workflow

### Issue: SBOM generation fails
**Solution:**
```bash
# Verify Syft installation
wget https://github.com/anchore/syft/releases/download/v1.5.0/syft_1.5.0_linux_amd64.tar.gz
tar -xzf syft_1.5.0_linux_amd64.tar.gz
./syft version

# Test SBOM generation manually
./syft backend/ -o cyclonedx-json
```

### Issue: Bandit scan reports issues
**Solution:**
- Review findings in GitHub Security tab
- Fix critical/high severity issues
- Document false positives with `# nosec` comments
- Re-run scan to verify fixes

## Success Criteria

✅ **All scanners complete successfully**
✅ **No critical vulnerabilities detected**
✅ **Security score: Grade A (90-100)**
✅ **All SARIF results uploaded to GitHub Security tab**
✅ **SBOMs generated and available as artifacts**
✅ **Security report summary displays correctly**
✅ **Quick links to GitHub Security tabs work**

## Evidence Collection

For compliance audits, collect:
1. ✅ Workflow run logs (download from GitHub Actions)
2. ✅ Security report summary (from job summary)
3. ✅ SBOM files (from artifacts)
4. ✅ SARIF files (from GitHub Security tab export)
5. ✅ Screenshots of GitHub Security tab findings
6. ✅ This verification document with all checkboxes marked

## Next Steps After Verification

1. **Set up Security Notifications:**
   - Configure GitHub security alerts
   - Set up email/Slack notifications for critical findings
   - Configure Dependabot for dependency updates

2. **Establish Security Baseline:**
   - Document current security score
   - Track trends over time
   - Set thresholds for alerts

3. **Regular Maintenance:**
   - Review scanner versions quarterly
   - Update ZAP rules as needed
   - Tune scanner configurations
   - Archive security reports for audit trail

4. **Integrate with CI/CD:**
   - Block deployments on critical findings
   - Require security review for high-severity issues
   - Track remediation time

## Verification Report

**Date:** _______________
**Verified By:** _______________
**Workflow Run:** _______________
**Security Score:** __________ / 100
**Grade:** __________

**Findings:**
- Critical: ___
- High: ___
- Medium: ___
- Low: ___

**Overall Status:** ⬜ PASSED ⬜ ATTENTION REQUIRED

**Notes:**
_________________________________________________________________________
_________________________________________________________________________
_________________________________________________________________________

**Sign-off:** ___________________ Date: _______________
