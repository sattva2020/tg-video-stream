# Quickstart: Running Project Critical Analysis

**Feature**: Project Critical Analysis
**Date**: 2025-11-02
**Related Docs**: [spec.md](spec.md) | [plan.md](plan.md) | [data-model.md](data-model.md)

## Overview

This guide explains how to run the critical analysis tool on the Telegram Video Streamer codebase and interpret the results.

---

## Prerequisites

### System Requirements

- **Python**: 3.11+ (analysis tools) | 3.8+ (existing project)
- **Git**: For codebase snapshot information
- **Platform**: Linux (Ubuntu 22.04/24.04) or compatible

### Dependencies

Install analysis dependencies:

```bash
# From repository root
pip install radon pylint bandit pydocstyle safety pip-audit jinja2 markdown
```

Or add to `requirements-dev.txt`:

```
# Analysis Tools
radon==6.0.1
pylint==3.0.3
bandit==1.7.5
pydocstyle==6.3.0
safety==2.3.5
pip-audit==2.6.1

# Report Generation
jinja2==3.1.2
markdown==3.5.1
```

---

## Running the Analysis

### Quick Start (All Reports)

Run complete analysis and generate all four reports:

```bash
# From repository root
python -m src.analysis.cli --all --output specs/001-critical-analysis/reports/
```

**Expected output:**
```
Starting critical analysis...
✓ Loaded constitution (v1.0.0)
✓ Scanned 12 files, 347 lines of code

Running static analysis...
  [1/4] Architecture review... ✓ (12 findings)
  [2/4] Code quality assessment... ✓ (15 findings)
  [3/4] Security scan... ✓ (8 findings)
  [4/4] Performance analysis... ✓ (5 findings)

Generating reports...
  ✓ architecture-review.md
  ✓ code-quality.md
  ✓ security-assessment.md
  ✓ performance-analysis.md

Analysis complete in 87 seconds.
Total: 40 findings (2 critical, 5 high, 18 medium, 15 low)
Constitution compliance: 67%

⚠ 2 critical findings require immediate attention!
```

### Individual Reports

Run specific analysis categories:

```bash
# Architecture review only
python -m src.analysis.cli --architecture

# Code quality only
python -m src.analysis.cli --code-quality

# Security assessment only
python -m src.analysis.cli --security

# Performance analysis only
python -m src.analysis.cli --performance
```

### Custom Options

```bash
# Specify output directory
python -m src.analysis.cli --all --output /path/to/reports/

# Set minimum severity threshold (suppress low/medium findings)
python -m src.analysis.cli --all --min-severity high

# JSON output (instead of Markdown)
python -m src.analysis.cli --all --format json

# Verbose logging
python -m src.analysis.cli --all --verbose

# Dry run (show what would be analyzed without running)
python -m src.analysis.cli --all --dry-run
```

---

## Understanding the Reports

### Report Structure

Each report follows this structure:

```markdown
# [Report Type] - [Date]

## Executive Summary
- Total findings: X (breakdown by severity)
- Constitution compliance: XX%
- Top 3 critical issues
- Estimated remediation effort

## Findings

### Critical Severity

#### [FINDING-ID] [Title]
**Severity**: Critical
**Category**: [category]
**Location**: [file:line]

[Description]

**Impact**: [why this matters]

**Evidence**:
- [code snippet or metric]

**Recommendation**: See REC-XXX

---

[Additional findings...]

## Recommendations

### REC-XXX: [Title]
**Priority**: P0
**Addresses**: [FINDING-ID]
**Effort**: [time estimate]

**Remediation Steps**:
1. [step 1]
2. [step 2]
...

**Expected Benefits**:
- [benefit 1]
- [benefit 2]

---

## Constitution Compliance

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Autonomous Operation | ✅ Compliant | [evidence] |
| II. Resource Efficiency | ⚠ Partial | [findings] |
...

## Risk Assessments (Security reports only)

[Risk matrices and evaluations]

## Appendix

- Tools used and versions
- Analysis configuration
- Codebase snapshot (git commit, LOC)
```

### Severity Levels

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| **Critical** | Immediate security risk or constitution violation (NON-NEGOTIABLE principle) | Fix before deployment |
| **High** | Significant security/operational risk or major code quality issue | Fix within sprint |
| **Medium** | Moderate quality/security concern | Prioritize in backlog |
| **Low** | Minor quality improvement | Address when convenient |

### Priority Levels (Recommendations)

| Priority | Timeframe | Scope |
|----------|-----------|-------|
| **P0** | Immediate (hours) | Blocks production deployment |
| **P1** | This sprint (days) | High-impact improvements |
| **P2** | Next sprint (weeks) | Medium-impact improvements |
| **P3** | Backlog (months) | Nice-to-have enhancements |

---

## Interpreting Results

### Constitution Compliance Percentage

**Formula**:
```
compliance_percentage = (compliant_principles / total_principles) * 100
```

**Status Definitions**:
- **Compliant**: Fully adheres to principle requirements
- **Partial**: Some violations but mitigating factors present
- **Violation**: Clear breach of principle requirements

**Example**:
```
5 principles total:
- I: Compliant
- II: Compliant
- III: Partial (missing retry logic)
- IV: Violation (hardcoded credentials)
- V: Compliant

Compliance = (3 compliant / 5 total) * 100 = 60%
```

### Risk Scores

**Calculation**:
```
likelihood_value = {"high": 3, "medium": 2, "low": 1}
impact_value = {"critical": 10, "high": 7, "medium": 4, "low": 1}
risk_score = (likelihood_value / 3) * impact_value
```

**Example**:
- Likelihood: high (3)
- Impact: critical (10)
- Risk Score: (3/3) * 10 = **10.0** (maximum risk)

**Prioritization**:
1. Risk Score ≥ 7.0 → **Immediate action**
2. Risk Score 4.0-6.9 → **Plan remediation**
3. Risk Score < 4.0 → **Monitor**

---

## Common Workflows

### Pre-Deployment Security Check

Before deploying to production:

```bash
# Run security analysis with high severity threshold
python -m src.analysis.cli --security --min-severity high

# Review report
less specs/001-critical-analysis/reports/security-assessment.md

# If critical findings exist, halt deployment
# Fix critical issues, re-run analysis
```

### Code Review Integration

During pull request review:

```bash
# Run code quality analysis on changed files
python -m src.analysis.cli --code-quality --files main.py utils.py

# Check for new findings compared to baseline
python -m src.analysis.cli --code-quality --diff-baseline master
```

### Continuous Monitoring

Weekly health check:

```bash
# Generate all reports
python -m src.analysis.cli --all

# Track trends over time
python -m src.analysis.cli --all --compare-previous

# Email summary to team
python -m src.analysis.cli --all --send-summary team@example.com
```

---

## Troubleshooting

### Analysis Fails to Start

**Error**: `ModuleNotFoundError: No module named 'radon'`

**Solution**: Install analysis dependencies
```bash
pip install -r requirements-dev.txt
```

---

### Missing Constitution File

**Error**: `FileNotFoundError: constitution.md not found`

**Solution**: Ensure constitution exists at `.specify/memory/constitution.md`
```bash
ls -la .specify/memory/constitution.md
```

---

### Permission Denied on Reports Directory

**Error**: `PermissionError: [Errno 13] Permission denied: 'specs/001-critical-analysis/reports/'`

**Solution**: Create directory with write permissions
```bash
mkdir -p specs/001-critical-analysis/reports
chmod 755 specs/001-critical-analysis/reports
```

---

### Tool Not Found (bandit, pylint, etc.)

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'bandit'`

**Solution**: Verify tools are in PATH
```bash
which bandit
which pylint
```

If missing, reinstall:
```bash
pip install --force-reinstall bandit pylint radon pydocstyle
```

---

### Analysis Timeout

**Error**: `TimeoutError: Analysis exceeded 2 hour limit`

**Solution**: Increase timeout or reduce scope
```bash
# Increase timeout to 4 hours
python -m src.analysis.cli --all --timeout 14400

# Or analyze individual components
python -m src.analysis.cli --security --files main.py
```

---

## Configuration

### Analysis Configuration File

Create `.analysis-config.yaml` in repository root:

```yaml
# Constitution validation
constitution:
  path: .specify/memory/constitution.md
  version: 1.0.0
  enforce_non_negotiable: true

# Severity thresholds
thresholds:
  min_severity: medium
  fail_on_critical: true
  max_high_findings: 10

# Tool-specific settings
tools:
  pylint:
    config: .pylintrc
    max_score: 8.0

  bandit:
    config: .bandit
    severity_level: low

  radon:
    max_complexity: 10
    min_maintainability: 'B'

# Report output
output:
  directory: specs/001-critical-analysis/reports
  format: markdown
  include_evidence: true
  verbose: false

# Exclusions
exclude:
  files:
    - "*/migrations/*"
    - "*/tests/*"
    - "*/__pycache__/*"
  directories:
    - venv/
    - .git/
```

Load configuration:
```bash
python -m src.analysis.cli --all --config .analysis-config.yaml
```

---

## Next Steps

After reviewing reports:

1. **Triage findings** - Sort by severity, identify P0/P1 items
2. **Create remediation plan** - Use recommendations as starting point
3. **Track progress** - Move findings to task tracking (Jira, GitHub Issues)
4. **Re-run analysis** - Verify fixes resolve findings
5. **Monitor trends** - Compare reports over time to track improvement

For detailed implementation guidance, see:
- [tasks.md](tasks.md) - Implementation task list (generated via `/speckit.tasks`)
- [data-model.md](data-model.md) - Report entity schemas
- [research.md](research.md) - Tool selection rationale

---

## FAQ

### Q: How long does a full analysis take?

**A**: ~1-2 minutes for the Telegram Video Streamer codebase (~200 LOC). Larger codebases (10k+ LOC) may take 15-30 minutes.

---

### Q: Can I run this in CI/CD?

**A**: Yes! Example GitHub Actions workflow:

```yaml
name: Critical Analysis
on: [pull_request]
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: python -m src.analysis.cli --security --min-severity high
      - run: python -m src.analysis.cli --code-quality --min-severity medium
```

---

### Q: What if I disagree with a finding?

**A**: Findings can be suppressed with justification:

1. Add `# nosec` comment (for bandit)
2. Add `# pylint: disable=rule-name` (for pylint)
3. Document suppression rationale in code comment
4. Track as accepted risk in risk register

**Example**:
```python
# Intentional use of assert for development validation
# Production code uses proper error handling
assert user.is_authenticated  # pylint: disable=W0101
```

---

### Q: Can I customize report templates?

**A**: Yes! Edit Jinja2 templates in `src/analysis/reporters/templates/`:

```bash
vim src/analysis/reporters/templates/security.md.j2
```

Then regenerate reports:
```bash
python -m src.analysis.cli --security --force-regenerate
```

---

## Support

For issues or questions:
- Check [troubleshooting](#troubleshooting) section
- Review [research.md](research.md) for tool-specific documentation
- Consult tool docs: [radon](https://radon.readthedocs.io/), [pylint](https://pylint.pycqa.org/), [bandit](https://bandit.readthedocs.io/)
