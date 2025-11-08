# Data Model: Project Critical Analysis

**Date**: 2025-11-02
**Feature**: [spec.md](spec.md)
**Research**: [research.md](research.md)

## Overview

This document defines the data structures for the critical analysis system. All entities are designed to be serializable to JSON for report generation and interoperability.

---

## Entity: Finding

**Purpose**: Represents an individual issue or observation discovered during analysis.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (e.g., "ARCH-001", "SEC-042") |
| `category` | enum | Yes | One of: "architecture", "code_quality", "security", "performance", "operational", "documentation" |
| `severity` | enum | Yes | One of: "critical", "high", "medium", "low" |
| `title` | string | Yes | Short descriptive title (max 100 chars) |
| `description` | string | Yes | Detailed explanation of the finding |
| `impact` | string | Yes | Why this matters (security risk, technical debt, etc.) |
| `location` | Location | No | Where the finding was detected (file, line, function) |
| `evidence` | array[string] | No | Code snippets, metrics, or data supporting the finding |
| `constitution_violation` | ConstitutionViolation | No | If finding violates a constitution principle |
| `detected_by` | string | Yes | Tool or method that detected this (e.g., "bandit", "manual_review") |
| `detected_at` | datetime | Yes | Timestamp when finding was detected |

### Validation Rules

- `id` must be unique across all findings in a report
- `severity` must map to CVSS-inspired scale (Critical: 9.0-10.0, High: 7.0-8.9, Medium: 4.0-6.9, Low: 0.1-3.9)
- If `constitution_violation` is present, `severity` must be at least "high"
- `title` should be action-oriented (e.g., "Hardcoded credentials detected" not "Credentials")

### Example

```json
{
  "id": "SEC-001",
  "category": "security",
  "severity": "critical",
  "title": "Hardcoded SESSION_STRING in main.py",
  "description": "Found hardcoded credential on line 45 of main.py. Sensitive SESSION_STRING value is embedded directly in source code.",
  "impact": "Credentials could be exposed via version control history, logs, or unauthorized access to codebase. Violates security best practices and Constitution Principle IV (Configuration-Driven Behavior).",
  "location": {
    "file": "main.py",
    "line": 45,
    "function": null
  },
  "evidence": [
    "SESSION_STRING = \"1BVtsOK...\" # Line 45"
  ],
  "constitution_violation": {
    "principle": "IV. Configuration-Driven Behavior",
    "is_non_negotiable": false,
    "rationale": "All deployment-specific settings MUST be externalized to environment variables"
  },
  "detected_by": "bandit",
  "detected_at": "2025-11-02T14:30:00Z"
}
```

---

## Entity: Recommendation

**Purpose**: Actionable improvement suggestion with implementation guidance.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (e.g., "REC-001") |
| `finding_id` | string | Yes | References the Finding this recommendation addresses |
| `priority` | enum | Yes | One of: "P0" (critical/blocking), "P1" (high), "P2" (medium), "P3" (low) |
| `title` | string | Yes | Short actionable title (max 100 chars, imperative mood) |
| `rationale` | string | Yes | Why this recommendation should be implemented |
| `remediation_steps` | array[string] | Yes | Ordered list of steps to implement the fix |
| `estimated_effort` | EffortEstimate | Yes | Time estimate and complexity |
| `expected_benefits` | array[string] | Yes | What improvements this delivers |
| `alternatives` | array[Alternative] | No | Other approaches considered |
| `references` | array[string] | No | Links to documentation, standards, examples |

### Validation Rules

- `finding_id` must reference an existing Finding
- `priority` must align with Finding severity (Critical → P0, High → P1, Medium → P2, Low → P3)
- `remediation_steps` must have at least one step
- `estimated_effort.duration` must be positive

### Example

```json
{
  "id": "REC-001",
  "finding_id": "SEC-001",
  "priority": "P0",
  "title": "Externalize SESSION_STRING to environment variable",
  "rationale": "Removing hardcoded credentials from source code prevents accidental exposure and enables environment-specific configuration without code changes.",
  "remediation_steps": [
    "Add SESSION_STRING to .env file (never commit this file)",
    "Install python-dotenv if not already present: pip install python-dotenv",
    "Add at top of main.py: from dotenv import load_dotenv; load_dotenv()",
    "Replace hardcoded value with: SESSION_STRING = os.getenv('SESSION_STRING')",
    "Add validation: if not SESSION_STRING: raise ValueError('SESSION_STRING not set')",
    "Verify .env is in .gitignore"
  ],
  "estimated_effort": {
    "duration": 15,
    "unit": "minutes",
    "complexity": "low"
  },
  "expected_benefits": [
    "Eliminates critical security vulnerability",
    "Achieves full compliance with Constitution Principle IV",
    "Enables environment-specific configuration (dev/staging/prod)",
    "Removes credentials from version control history"
  ],
  "alternatives": [
    {
      "approach": "Use systemd environment variables directly",
      "pros": "No .env file needed",
      "cons": "Less flexible for local development, harder to manage multiple values"
    }
  ],
  "references": [
    "https://12factor.net/config",
    "https://pypi.org/project/python-dotenv/"
  ]
}
```

---

## Entity: ComplianceItem

**Purpose**: Validation result for a specific constitution principle or technical constraint.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `principle` | string | Yes | Constitution principle name (e.g., "I. Autonomous Operation") |
| `is_non_negotiable` | boolean | Yes | Whether principle is marked NON-NEGOTIABLE |
| `status` | enum | Yes | One of: "compliant", "partial", "violation" |
| `evidence` | array[string] | Yes | Supporting facts for the status |
| `findings` | array[string] | No | IDs of related findings (if status is partial/violation) |
| `recommendations` | array[string] | No | IDs of recommendations to achieve compliance |
| `validation_method` | string | Yes | How compliance was checked (e.g., "manual_review", "ast_validator") |

### Validation Rules

- If `is_non_negotiable` is true and `status` is "violation", overall analysis must fail
- `evidence` must have at least one item
- If `status` is "partial" or "violation", `findings` should be populated

### Example

```json
{
  "principle": "IV. Configuration-Driven Behavior",
  "is_non_negotiable": false,
  "status": "violation",
  "evidence": [
    "Found hardcoded SESSION_STRING in main.py:45",
    "CHAT_ID hardcoded in utils.py:12",
    ".env.example exists but .env usage not enforced"
  ],
  "findings": ["SEC-001", "SEC-002"],
  "recommendations": ["REC-001", "REC-002"],
  "validation_method": "bandit + custom_ast_validator"
}
```

---

## Entity: RiskAssessment

**Purpose**: Security or operational risk evaluation with likelihood and impact.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (e.g., "RISK-001") |
| `title` | string | Yes | Short risk description |
| `category` | enum | Yes | One of: "security", "operational", "compliance" |
| `likelihood` | enum | Yes | One of: "high", "medium", "low" |
| `impact` | enum | Yes | One of: "critical", "high", "medium", "low" |
| `risk_score` | float | Yes | Calculated: likelihood × impact (scale 0.0-10.0) |
| `description` | string | Yes | Detailed risk scenario |
| `current_mitigations` | array[string] | No | Existing controls in place |
| `recommended_controls` | array[string] | Yes | Additional controls to implement |
| `findings` | array[string] | No | Related finding IDs |
| `recommendations` | array[string] | No | Related recommendation IDs |

### Risk Score Calculation

```
likelihood_value = {"high": 3, "medium": 2, "low": 1}
impact_value = {"critical": 10, "high": 7, "medium": 4, "low": 1}
risk_score = (likelihood_value[likelihood] / 3) * impact_value[impact]
```

### Example

```json
{
  "id": "RISK-001",
  "title": "Credential exposure via version control",
  "category": "security",
  "likelihood": "high",
  "impact": "critical",
  "risk_score": 10.0,
  "description": "If SESSION_STRING remains hardcoded, any developer with repository access can extract user credentials. Historical commits may already contain exposed values.",
  "current_mitigations": [
    ".gitignore includes .env file"
  ],
  "recommended_controls": [
    "Remove hardcoded SESSION_STRING from all source files",
    "Use environment variables exclusively for credentials",
    "Rotate SESSION_STRING immediately after remediation",
    "Add pre-commit hook to detect hardcoded secrets"
  ],
  "findings": ["SEC-001"],
  "recommendations": ["REC-001"]
}
```

---

## Entity: Report

**Purpose**: Aggregates all analysis results for a specific category (architecture, code quality, security, performance).

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `report_id` | string | Yes | Unique identifier (e.g., "architecture-2025-11-02") |
| `report_type` | enum | Yes | One of: "architecture", "code_quality", "security", "performance" |
| `generated_at` | datetime | Yes | Timestamp when report was generated |
| `codebase_snapshot` | CodebaseSnapshot | Yes | Git commit, branch, file count, LOC |
| `summary` | ReportSummary | Yes | High-level statistics (findings count by severity, compliance %) |
| `findings` | array[Finding] | No | All findings for this report category |
| `recommendations` | array[Recommendation] | No | All recommendations for this report category |
| `compliance_items` | array[ComplianceItem] | No | Constitution validation results (if applicable) |
| `risk_assessments` | array[RiskAssessment] | No | Risk evaluations (security/operational reports only) |
| `metadata` | ReportMetadata | Yes | Analysis tool versions, runtime, config |

### Example

```json
{
  "report_id": "security-2025-11-02",
  "report_type": "security",
  "generated_at": "2025-11-02T15:00:00Z",
  "codebase_snapshot": {
    "git_commit": "14eff28",
    "branch": "001-critical-analysis",
    "total_files": 12,
    "total_loc": 347
  },
  "summary": {
    "total_findings": 8,
    "by_severity": {
      "critical": 2,
      "high": 3,
      "medium": 2,
      "low": 1
    },
    "constitution_compliance": "67%"
  },
  "findings": [...],
  "recommendations": [...],
  "compliance_items": [...],
  "risk_assessments": [...],
  "metadata": {
    "tools": {
      "bandit": "1.7.5",
      "safety": "2.3.5",
      "pip-audit": "2.6.1"
    },
    "runtime_seconds": 45,
    "config": {
      "constitution_version": "1.0.0",
      "severity_threshold": "medium"
    }
  }
}
```

---

## Supporting Types

### Location

```json
{
  "file": "string (relative path from repo root)",
  "line": "integer | null",
  "function": "string | null",
  "column": "integer | null"
}
```

### ConstitutionViolation

```json
{
  "principle": "string (full principle name)",
  "is_non_negotiable": "boolean",
  "rationale": "string (why this violates the principle)"
}
```

### EffortEstimate

```json
{
  "duration": "integer (time value)",
  "unit": "enum (minutes|hours|days)",
  "complexity": "enum (low|medium|high)"
}
```

### Alternative

```json
{
  "approach": "string (alternative solution description)",
  "pros": "string",
  "cons": "string"
}
```

### CodebaseSnapshot

```json
{
  "git_commit": "string (short SHA)",
  "branch": "string",
  "total_files": "integer",
  "total_loc": "integer"
}
```

### ReportSummary

```json
{
  "total_findings": "integer",
  "by_severity": {
    "critical": "integer",
    "high": "integer",
    "medium": "integer",
    "low": "integer"
  },
  "constitution_compliance": "string (percentage, e.g., '80%')"
}
```

### ReportMetadata

```json
{
  "tools": "object (tool_name: version)",
  "runtime_seconds": "integer",
  "config": "object (configuration key-value pairs)"
}
```

---

## Entity Relationships

```
Report (1)
  ├─── contains ───> Finding (0..*)
  ├─── contains ───> Recommendation (0..*)
  ├─── contains ───> ComplianceItem (0..*)
  └─── contains ───> RiskAssessment (0..*)

Finding (1)
  ├─── referenced by ───> Recommendation (1..*)
  ├─── referenced by ───> ComplianceItem (0..*)
  └─── referenced by ───> RiskAssessment (0..*)

Recommendation (1)
  ├─── addresses ───> Finding (1)
  └─── referenced by ───> RiskAssessment (0..*)

ComplianceItem (1)
  ├─── references ───> Finding (0..*)
  └─── references ───> Recommendation (0..*)

RiskAssessment (1)
  ├─── references ───> Finding (0..*)
  └─── references ───> Recommendation (0..*)
```

---

## Implementation Notes

### Serialization

All entities must be serializable to/from JSON for:
- Report file generation (Markdown with embedded JSON)
- API responses (if future integration needed)
- Testing fixtures

Use Python `dataclasses` with `dataclasses-json` or `pydantic` for automatic serialization.

### Validation

- Use `pydantic` models for automatic validation of required fields, enums, and type constraints
- Implement custom validators for business rules (e.g., `finding_id` references, severity-priority alignment)

### Storage

- Reports stored as Markdown files with embedded JSON metadata in frontmatter
- Individual entities (Finding, Recommendation) rendered as Markdown sections within reports
- No database required (file-based storage per Constitution Principle II: Resource Efficiency)

---

## Next Steps

Proceed to creating:
1. [contracts/report-schema.json](contracts/report-schema.json) - JSON Schema for validation
2. [quickstart.md](quickstart.md) - Usage documentation
