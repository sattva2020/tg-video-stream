```markdown
# research.md — Project Critical Analysis (phase 0)

Generated: 2025-11-08

## Purpose

Resolve technical-context unknowns required to produce Phase 1 artifacts (data-model, contracts, quickstart). Record decisions, rationale and alternatives.

## Decisions

1. Decision: Language/runtime

   - Chosen: Python 3.12
   - Rationale: Repository uses per-release venvs, recent Python features seen in code, and native bindings for `ntgcalls` built against modern CPython. Targeting 3.12 avoids compatibility issues with newer wheels and is consistent with server-side packaging.
   - Alternatives: 3.10 / 3.11 (more conservative) — benefit: wider package compatibility; downside: might require rebuilding some newer wheels and lose language features.

2. Decision: Primary dependencies

   - Chosen: Pyrogram (Telegram client), py-tgcalls/ntgcalls (voice/video), ffmpeg (system binary), yt-dlp, python-dotenv
   - Rationale: These are already used in the repo and required for streaming + session management.
   - Alternatives: Telethon as fallback for session generation and some client tasks — keep as fallback in tests/tools.

3. Decision: Testing

   - Chosen: pytest as primary test runner and small test harnesses in `test/` for functional checks.
   - Rationale: pytest is standard in Python and aligns with the project size; current repo contains small test helpers. A focused set of unit + integration tests will be added in Phase 1.
   - Alternatives: unittest (stdlib) — less ergonomic for modern Python testing.

4. Decision: Target platform and deployment pattern

   - Chosen: Linux (systemd) with per-release layout under `/opt/tg_video_streamer` and `tgstream` service account.
   - Rationale: Existing deployment scripts and systemd unit assume this layout; native builds performed on the server for `ntgcalls`.

5. Decision: Performance baseline

   - Chosen: Support a target host class: 2 vCPU, 2-4 GB RAM. Optimize for low memory and CPU-heavy FFmpeg operations.
   - Rationale: Matches constitution assumptions and typical small cloud VM sizes.

6. Decision: Secrets & environment

   - Chosen: `.env` stored under `/opt/tg_video_streamer/current/.env` with backups by deploy pipeline; sensitive fields masked in CI logs.
   - Rationale: Matches current repo pattern; deploy pipeline will ensure backups and masked logs.

## Resolved Unknowns (NEEDS CLARIFICATION → resolved here as assumptions)

- Constitution file: currently a template. ACTION: project maintainers must ratify the constitution file; for planning we assume the core principles are: Autonomous Operation, Resource Efficiency, Fail-Safe Error Handling, Configuration-Driven Behavior, Minimal Attack Surface.
- Test-First requirement: Assume not mandatory for this repository (mark tests as recommended), unless constitution is later amended.

## Alternatives & Risks

- Risk: Native builds for `ntgcalls` increase deployment complexity — mitigation: produce prebuilt wheels for supported targets or use CI to build per-release wheels and cache.
- Alternative: Use Telethon-only stack (no py-tgcalls) — downside: loses voice/video native acceleration; advantage: simpler Python-only deployment.

## Next actions (Phase 1 prerequisites)

1. Ratify constitution in `.specify/memory/constitution.md` (replace placeholders with project-specific principles and required gates).  
2. Create `data-model.md` mapping Analysis Report, Finding, Recommendation entities.  
3. Add a minimal pytest harness covering: `test/test_session.py` and a smoke test that imports `pyrogram` and `pytgcalls` in a clean venv.  
4. Run dependency scan (safety/bandit/oss security) in CI and produce the vulnerability list for inclusion in the report.

```# Research: Project Critical Analysis

**Date**: 2025-11-02
**Feature**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Objective

Research and select appropriate tools, methodologies, and best practices for implementing a comprehensive critical analysis system that evaluates Python codebases against custom governance principles (constitution).

---

## Research Areas

### 1. Python Static Analysis Tools

**Question**: Which tools best analyze Python code for complexity, quality, and security?

#### Research Findings

**Code Complexity & Metrics:**
- **`radon`** - Cyclomatic complexity (McCabe), Halstead metrics, maintainability index
  - **Pros**: Lightweight, CLI-friendly, JSON output, widely adopted
  - **Cons**: Limited to metrics (no fix suggestions)
  - **Decision**: ✅ **SELECTED** - Industry standard for Python complexity analysis

**Code Quality & Linting:**
- **`pylint`** - Comprehensive code analysis (PEP 8, bugs, design issues)
  - **Pros**: Configurable rules, detailed reports, integrates with editors
  - **Cons**: Can be slow on large codebases, verbose output
  - **Alternative**: `flake8` (faster but less comprehensive)
  - **Decision**: ✅ **SELECTED** - More thorough than flake8, acceptable for ~200 LOC

**Security Scanning:**
- **`bandit`** - Security vulnerability detection (hardcoded passwords, SQL injection, etc.)
  - **Pros**: OWASP-aligned, severity ratings, CLI + Python API
  - **Cons**: Limited to common vulnerability patterns (no dataflow analysis)
  - **Decision**: ✅ **SELECTED** - Industry standard for Python security scanning

**Documentation Quality:**
- **`pydocstyle`** - Docstring convention checker (PEP 257)
  - **Pros**: Fast, configurable conventions, integrates with linters
  - **Cons**: Only checks docstrings (not README or inline comments)
  - **Decision**: ✅ **SELECTED** - Essential for maintainability assessment

**Alternatives Considered:**
- **SonarQube**: Comprehensive but requires server infrastructure (violates Resource Efficiency)
- **Codacy**: Cloud-based (requires network, violates Minimal Attack Surface)
- **mypy**: Type checking only (useful but limited scope)

---

### 2. Dependency Security Scanning

**Question**: How to detect CVEs and supply chain vulnerabilities in Python dependencies?

#### Research Findings

**CVE Detection:**
- **`safety`** - Checks installed packages against vulnerability database
  - **Pros**: Simple CLI, JSON output, actively maintained database
  - **Cons**: Requires network for DB updates (cache for offline use)
  - **Decision**: ✅ **SELECTED** - De facto standard for Python CVE scanning

**Supply Chain Security:**
- **`pip-audit`** - PyPI package auditing (official Python Packaging Authority tool)
  - **Pros**: Audits requirements.txt + installed packages, OSV database integration
  - **Cons**: Slower than safety (more comprehensive analysis)
  - **Decision**: ✅ **SELECTED** - Complements safety with supply chain checks

**Alternatives Considered:**
- **Snyk**: Commercial tool with free tier (requires account, violates Minimal Attack Surface)
- **OWASP Dependency-Check**: Java-based (heavyweight, violates Resource Efficiency)

**Best Practice**: Run both `safety` and `pip-audit` for comprehensive coverage (safety for speed, pip-audit for depth).

---

### 3. Architecture Analysis Methodology

**Question**: How to systematically analyze software architecture and design patterns?

#### Research Findings

**Architecture Documentation Languages:**
- **C4 Model** (Context, Container, Component, Code) - Hierarchical architecture diagrams
  - **Pros**: Industry standard, clear abstraction levels, widely understood
  - **Cons**: Manual creation required (no automated generation for Python)
  - **Decision**: ✅ **REFERENCE** - Use C4 terminology in architecture reports

**Pattern Detection Approaches:**
- **Manual Code Review** - Read code, identify patterns (async/await, piping, dependency injection)
  - **Pros**: Flexible, context-aware, can assess design intent
  - **Cons**: Labor-intensive, requires domain expertise
  - **Decision**: ✅ **SELECTED** - Most appropriate for small codebase (~200 LOC)

**Automated Pattern Detection:**
- **`pyreverse`** (from pylint) - Generate UML diagrams from code
  - **Pros**: Automated class/module relationship visualization
  - **Cons**: Limited pattern recognition (shows structure, not intent)
  - **Decision**: ⚠️ **OPTIONAL** - Useful for visualization but not primary analysis method

**Constitution Compliance Validation:**
- **Custom Analysis Framework** - Parse code + config, validate against constitution rules
  - **Approach**: Check for patterns that violate principles (e.g., hardcoded credentials → violates Principle IV)
  - **Decision**: ✅ **REQUIRED** - No existing tool validates custom governance principles

**Best Practice**: Combine manual review (for design intent) with automated tools (for metrics) and custom validation (for constitution compliance).

---

### 4. Report Generation & Templating

**Question**: What's the best approach for generating structured, readable analysis reports?

#### Research Findings

**Templating Engines:**
- **`jinja2`** - Python templating engine (used by Flask, Ansible, etc.)
  - **Pros**: Powerful, flexible, supports inheritance/includes, widely known
  - **Cons**: Requires template design (not a con for our use case)
  - **Decision**: ✅ **SELECTED** - Industry standard for Python template generation

**Report Formats:**
- **Markdown** - Human-readable, version-control friendly, renders in GitHub/VSCode
  - **Pros**: Plain text, easy to review, supports tables/code blocks/links
  - **Cons**: Limited formatting compared to HTML/PDF
  - **Decision**: ✅ **SELECTED** - Aligns with constitution (simplicity, text-based)

- **HTML** - Rich formatting, interactive elements
  - **Cons**: Requires browser, harder to version control
  - **Decision**: ❌ **REJECTED** - Violates simplicity principle

- **PDF** - Professional appearance, fixed layout
  - **Cons**: Binary format, not version-control friendly, requires rendering libraries
  - **Decision**: ❌ **REJECTED** - Violates simplicity + Resource Efficiency

**Severity Rating Systems:**
- **CVSS (Common Vulnerability Scoring System)** - 0.0-10.0 scale with severity bands
  - **Adapted**: Critical (9.0-10.0), High (7.0-8.9), Medium (4.0-6.9), Low (0.1-3.9)
  - **Decision**: ✅ **REFERENCE** - Use CVSS-inspired 4-tier system (Critical/High/Medium/Low)

**Best Practice**: Generate Markdown reports from Jinja2 templates, store in `specs/001-critical-analysis/reports/` for version control and review.

---

### 5. Constitution Compliance Validation

**Question**: How to programmatically validate code against custom governance principles?

#### Research Findings

**Validation Approaches:**

**Principle I: Autonomous Operation**
- **Check**: No `input()` calls, no GUI imports (tkinter, Qt), no blocking file dialogs
- **Tool**: Custom AST parser (Python `ast` module)
- **Decision**: ✅ **CUSTOM VALIDATOR** - Scan for interactive patterns

**Principle II: Resource Efficiency**
- **Check**: No large in-memory data structures, no file caching, streaming patterns used
- **Tool**: Manual review + memory profiling guidance in report
- **Decision**: ⚠️ **MANUAL + GUIDANCE** - Hard to automate, provide optimization recommendations

**Principle III: Fail-Safe Error Handling**
- **Check**: Try-except blocks around external calls (API, file I/O), retry logic present
- **Tool**: Custom AST parser + pylint error handling checks
- **Decision**: ✅ **CUSTOM VALIDATOR** - Scan for unprotected external calls

**Principle IV: Configuration-Driven Behavior**
- **Check**: No hardcoded credentials, URLs, paths; environment variables used
- **Tool**: `bandit` (detects hardcoded passwords) + custom validator for magic values
- **Decision**: ✅ **BANDIT + CUSTOM** - Bandit for secrets, custom for other hardcoded values

**Principle V: Minimal Attack Surface**
- **Check**: No network servers (Flask, FastAPI), no exposed ports, read-only file operations
- **Tool**: Custom AST parser (detect `socket`, `http.server`, `flask`, `fastapi` imports)
- **Decision**: ✅ **CUSTOM VALIDATOR** - Scan for networking/server patterns

**Implementation**: Create `src/analysis/analyzers/constitution.py` module with AST-based validators for each principle.

---

### 6. Performance Analysis for Async Python

**Question**: How to analyze performance and resource consumption in async Python applications?

#### Research Findings

**Memory Profiling:**
- **`memory_profiler`** - Line-by-line memory usage analysis
  - **Pros**: Detailed per-line profiling, decorators for async functions
  - **Cons**: Significant runtime overhead (not suitable for production)
  - **Decision**: ⚠️ **GUIDANCE ONLY** - Recommend for manual profiling, don't run automatically

**CPU Profiling:**
- **`cProfile`** - Built-in profiler (function call statistics)
  - **Pros**: No dependencies, low overhead, detailed call graphs
  - **Cons**: Requires running the application (not static analysis)
  - **Decision**: ⚠️ **GUIDANCE ONLY** - Provide instructions in performance report

**Static Performance Analysis:**
- **Pattern Detection** - Identify anti-patterns (blocking I/O in async, inefficient loops)
  - **Check**: Synchronous file I/O in async functions, `time.sleep()` vs `asyncio.sleep()`
  - **Tool**: Custom AST parser
  - **Decision**: ✅ **CUSTOM VALIDATOR** - Scan for async anti-patterns

**Resource Consumption Validation:**
- **Approach**: Compare requirements.txt against constitution target (2 vCPU / 2-4 GB RAM)
  - **Check**: Dependencies with known high memory usage (pandas, scipy → ❌ not present)
  - **Decision**: ✅ **DEPENDENCY REVIEW** - Manual assessment of dependency resource requirements

**Best Practice**: Combine static anti-pattern detection with profiling guidance for hands-on performance testing.

---

## Technology Selection Summary

| Category | Tool/Approach | Rationale |
|----------|---------------|-----------|
| **Complexity** | `radon` | Industry standard, lightweight, JSON output |
| **Code Quality** | `pylint` | Comprehensive PEP 8 + bug detection |
| **Security** | `bandit` | OWASP-aligned vulnerability scanning |
| **Documentation** | `pydocstyle` | PEP 257 docstring validation |
| **CVE Detection** | `safety` | Fast vulnerability database checks |
| **Supply Chain** | `pip-audit` | Comprehensive PyPI auditing |
| **Architecture** | Manual Review + C4 terminology | Flexible for small codebase, clear documentation |
| **Constitution** | Custom AST validators | No existing tool for custom governance |
| **Reports** | Jinja2 + Markdown | Simple, version-control friendly, readable |
| **Performance** | Static analysis + profiling guidance | Practical for analysis tool constraints |

---

## Best Practices Consolidated

### Analysis Execution Flow

```
1. Pre-Analysis Setup
   ↓
   - Validate environment (Python 3.8+, tools installed)
   - Load constitution.md for compliance rules
   - Configure analysis scope (which files, which checks)

2. Static Analysis (Parallel)
   ↓
   - radon: Complexity metrics → findings
   - pylint: Code quality → findings
   - bandit: Security scan → findings
   - pydocstyle: Documentation → findings
   - Custom: Constitution validation → compliance items

3. Dependency Analysis (Sequential)
   ↓
   - safety: CVE scan → risk assessments
   - pip-audit: Supply chain audit → risk assessments
   - requirements.txt review → dependency findings

4. Architecture Review (Manual + Automated)
   ↓
   - Parse main.py, utils.py (AST analysis)
   - Identify patterns (async, piping, config injection)
   - Generate architecture description
   - Validate against constitution principles

5. Report Generation (Sequential)
   ↓
   - Aggregate findings by category
   - Apply severity ratings (Critical/High/Medium/Low)
   - Generate recommendations with remediation effort
   - Render Markdown reports from Jinja2 templates

6. Post-Analysis
   ↓
   - Write reports to specs/001-critical-analysis/reports/
   - Log analysis summary (findings count, runtime)
   - Exit with status code (0 = success, 1 = critical findings)
```

### Severity Rating Guidelines

Based on CVSS principles, adapted for code analysis:

| Severity | Criteria | Examples |
|----------|----------|----------|
| **Critical** | Immediate security risk or constitution violation (NON-NEGOTIABLE principle) | Hardcoded credentials, no error handling on critical paths, interactive prompts in production |
| **High** | Significant security/operational risk or major code quality issue | Known CVE in dependency, missing input validation, high cyclomatic complexity (>15) |
| **Medium** | Moderate quality/security concern, does not block production | Missing docstrings, medium complexity (10-15), deprecated API usage |
| **Low** | Minor quality improvement, cosmetic issues | PEP 8 violations (whitespace), unused imports, minor typos in comments |

### Actionable Recommendation Format

Each recommendation must include:

1. **Finding**: What was detected (specific line/file if applicable)
2. **Impact**: Why it matters (security, performance, maintainability)
3. **Remediation**: Step-by-step fix guidance
4. **Effort**: Estimated time (minutes for low, hours for medium/high, days for critical)
5. **Priority**: Based on severity + impact to constitution compliance

**Example**:
```markdown
### Finding: Hardcoded API credentials in main.py:45

**Severity**: CRITICAL
**Category**: Security / Constitution Violation (Principle IV)

**Impact**: Exposes SESSION_STRING in source code, violates Configuration-Driven Behavior principle. Credentials could be leaked via version control or logs.

**Remediation**:
1. Move `SESSION_STRING = "..."` to `.env` file
2. Add `from dotenv import load_dotenv` and `load_dotenv()` to main.py
3. Replace hardcoded value with `os.getenv("SESSION_STRING")`
4. Verify `.env` is in `.gitignore`

**Effort**: 10 minutes
**Priority**: P0 (must fix before production deployment)
```

---

## Unknowns Resolved

All "NEEDS CLARIFICATION" items from plan.md Technical Context have been resolved through this research:

✅ **Language/Version**: Python 3.11+ for analysis tools (existing project uses 3.8+)
✅ **Primary Dependencies**: radon, pylint, bandit, pydocstyle, safety, pip-audit, jinja2, markdown
✅ **Storage**: File-based Markdown reports in specs/001-critical-analysis/reports/
✅ **Testing**: pytest for analysis tool validation
✅ **Constitution Validation**: Custom AST validators for each of 5 principles
✅ **Report Format**: Markdown generated from Jinja2 templates
✅ **Severity System**: 4-tier CVSS-inspired (Critical/High/Medium/Low)

---

## Next Steps

Research complete. Proceed to **Phase 1: Design** to create:
1. [data-model.md](data-model.md) - Entity schemas (Finding, Recommendation, Report, etc.)
2. [contracts/report-schema.json](contracts/report-schema.json) - JSON schema for validation
3. [quickstart.md](quickstart.md) - How to run analysis and interpret results
4. Update agent context with analysis tooling details
