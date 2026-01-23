# Security Scanning Enhancements

## Overview
Enhanced the security scanning workflow (`security-scan.yml`) with additional tools, better reporting, and improved stability.

## Date
2026-01-23

## Enhancements Made

### 1. **SBOM Generation (New Job)**
- **Tool**: Syft v1.5.0
- **Purpose**: Generate Software Bill of Materials (SBOM) for compliance
- **Outputs**:
  - CycloneDX JSON format (backend, frontend, Docker image)
  - SPDX JSON format (backend, frontend)
  - All SBOMs uploaded as artifacts for compliance documentation
- **Compliance**: Supports SOC 2, GDPR, and other compliance frameworks requiring SBOM

### 2. **Python Security Scanning (New Job)**
- **Tool**: Bandit with TOML support
- **Purpose**: Python-specific security vulnerability detection
- **Integration**:
  - Generates SARIF output for GitHub Security tab
  - Produces JSON report for detailed analysis
  - Complements Semgrep for Python code

### 3. **Enhanced Secret Scanning**
- **Improvement**: Upgraded from manual gitleaks installation to official GitHub Action
- **Version**: Gitleaks Action v2.5.0
- **Benefits**:
  - More reliable and maintained integration
  - Better error handling
  - Automatic updates from Gitleaks team
  - Support for GITLEAKS_LICENSE if available

### 4. **Improved Trivy Container Scanning**
- **Version Pinning**: Changed from `@master` to `@0.24.0`
- **Severity Enhancement**: Added MEDIUM severity to scans
- **Better SARIF Upload**: Now uploads all three scan types to GitHub Security:
  - Backend container scan
  - Frontend container scan
  - Filesystem scan (secrets, vulnerabilities, config issues)

### 5. **Enhanced ZAP DAST Scanning**
- **Version Updates**:
  - Baseline scan: `v0.12.0` → `v0.13.0`
  - API scan: `v0.7.0` → `v0.8.0`
- **Timeout**: Added `-t 10` option for 10-minute timeout per scan
- **Benefits**: More reliable scans with proper timeouts

### 6. **Comprehensive Security Report**
- **Enhanced Summary**: Now includes:
  - Scan date and timestamp
  - Commit SHA reference
  - Table with scanner status and descriptions
  - Overall status calculation (PASSED/ATTENTION REQUIRED)
  - Quick links to GitHub Security tabs
- **Security Score**: New feature that calculates:
  - Base score: 100
  - Deductions for failed scans (Semgrep: -20, CodeQL: -20, etc.)
  - Letter grade (A-F) based on final score
  - Provides quick assessment of security posture

### 7. **Better Artifact Management**
- All SARIF files now uploaded to GitHub Security tab
- SBOM files available for compliance audits
- Combined security report artifact for easy access

## Security Scanners Coverage

| Scanner | Type | Coverage | SARIF Upload |
|---------|------|----------|--------------|
| Semgrep | SAST | Python, TypeScript, React, Docker | ✅ Yes |
| CodeQL | SAST | JavaScript, Python | ✅ Yes |
| Bandit | SAST | Python-specific | ✅ Yes |
| Trivy | Container | Docker images, filesystem | ✅ Yes |
| Gitleaks | Secrets | Git history, files | ✅ Yes |
| ZAP | DAST | Running web application | No (HTML/JSON) |
| pip-audit | Dependencies | Python packages | No (Markdown) |
| npm audit | Dependencies | Node packages | No (Markdown) |
| Syft | SBOM | All dependencies | N/A (CycloneDX/SPDX) |

## Compliance Mapping

### SOC 2 Type II
- ✅ **CC6.1**: Logical and physical access controls
- ✅ **CC6.6**: Malware protection
- ✅ **CC7.2**: System monitoring
- ✅ **CC8.1**: System vulnerability identification and protection
- ✅ **A1.2**: Criteria for risk assessment (SBOM for dependency tracking)

### GDPR
- ✅ **Article 32**: Security of processing (technical measures)
- ✅ **Article 25**: Data protection by design and default
- ✅ **Article 30**: Records of processing activities (SBOM support)

## Workflow Triggers
1. **Push to main**: Immediate scan on production changes
2. **Pull requests**: Pre-merge security validation
3. **Weekly schedule**: Sundays at 3:00 UTC - regular security health check
4. **Manual dispatch**: On-demand full scans including DAST

## Security Grade Calculation
```
Base Score: 100

Deductions:
- Semgrep failure: -20
- CodeQL failure: -20
- Trivy failure: -20
- Secret scan failure: -25
- Bandit failure: -10
- Dependency audit failure: -5

Grades:
- A (90-100): Excellent security posture
- B (80-89): Good security posture
- C (70-79): Fair security posture - attention needed
- D (60-69): Poor security posture - action required
- F (0-59): Critical issues - immediate action required
```

## GitHub Security Integration
All SARIF results are automatically uploaded to GitHub Security tab:
- **Code Scanning**: Semgrep, CodeQL, Bandit, Trivy results
- **Secret Scanning**: Gitleaks findings
- **Dependency Review**: Manual review of audit reports
- **Security Alerts**: Aggregated view of all findings

## Next Steps
1. ✅ Run initial scan to establish baseline
2. ✅ Review results in GitHub Security tab
3. ✅ Address any critical findings
4. ✅ Set up security alerts notifications
5. ✅ Use SBOMs for compliance documentation
6. ✅ Track security score trends over time

## Maintenance Notes
- Review and update scanner versions quarterly
- Adjust severity thresholds based on risk tolerance
- Update SBOM generation on each release
- Monitor security score trends in reports
- Archive security reports for audit trail

## Related Documentation
- [ZAP Rules Configuration](../.zap/rules.tsv)
- [SOC 2 Compliance](../../docs/compliance/SOC2_README.md)
- [GDPR Compliance](../../docs/compliance/GDPR_README.md)
- [Security Testing Guide](../../docs/security/TESTING_GUIDE.md)

## Version History
- **v1.0** (2026-01-23): Initial security scanning workflow
- **v2.0** (2026-01-23): Enhanced with SBOM, Bandit, improved reporting, security score
