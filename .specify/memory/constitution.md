```markdown
# Telegram Streaming App Constitution

**Version**: 1.0.0 | **Ratified**: 2025-11-08 | **Last Amended**: 2025-11-08

---

## Core Principles

### I. Production-First
All code must be suitable for production deployment. Security hardening, error handling, and observability are **non-negotiable**, not optional. Features without production-ready status must be marked as EXPERIMENTAL and cannot be deployed to live hosts.

**MUST**:
- All service-critical code has explicit error handling
- All secrets (.env, SESSION_STRING, API credentials) are protected (chmod 600, unprivileged ownership)
- All deployments use systemd units with hardening options (ProtectSystem, NoNewPrivileges, PrivateTmp)
- No hardcoded credentials or API keys

### II. Explicit Contracts
All APIs, CLI tools, systemd services, and inter-component communication must have well-defined contracts: exit codes, error messages, input/output formats, timeouts, and retry logic.

**MUST**:
- Every CLI command documents success (exit 0) and failure (exit != 0) codes
- Every error logs the cause + actionable recommendation for operators
- Every timeout documented (e.g., CI restart waits max 60s)
- Every async operation defines success/failure criteria and max retries

### III. Test-Driven for Critical Paths
Core functionality (session recovery, systemd restart, deployment) must be validated by automated tests **before** claiming implementation complete.

**MUST**:
- Session recovery (SessionExpired handling) has acceptance test
- systemd restart logic validated with smoke test
- Prometheus metrics exposed and scrapeable
- CI restart step tested with dry-run or staging environment

### IV. Security-First
Least privilege, data protection, and secure defaults are mandatory.

**MUST**:
- .env permissions always 600 (owner read/write only)
- .env owner is unprivileged user (tgstream)
- systemd runs app under unprivileged user
- Session strings never logged in plaintext; masked as `***` or truncated
- Deploy script enforces permissions on every release

### V. Clear Error Handling & Observability
No silent failures. All errors must be logged with sufficient context for operators to diagnose.

**MUST**:
- Every error logged to stderr or syslog with timestamp, level (ERROR/WARN/INFO), and component
- SessionExpired errors suggest recovery path (run auto_session_runner.py --write-env)
- Prometheus metrics export operational health (streams_played_total, last_error_timestamp)
- systemd RestartSec logged; manual restarts auditable

---

## Non-Functional Requirements

### Performance
- Session authentication must complete within 10s or fail gracefully
- Prometheus scrape must respond within 5s
- yt-dlp updates must not block main service (async/background)

### Availability
- systemd Restart=always ensures auto-recovery after crashes
- Session regeneration possible without manual code changes (--write-env flag)
- Degraded mode allows operator awareness without service crash

### Scalability
- Per-release layout allows multiple versions deployed simultaneously
- Prometheus metrics designed to not grow unbounded (counters, not lists)
- yt-dlp updates via timer, not cron polling

---

## Security Requirements

### Secrets Management
- API_ID, API_HASH, SESSION_STRING stored in .env (not in code/git)
- .env never committed to repository; .gitignore enforced
- .env permissions enforced by deploy script (600, tgstream:tgstream)

### Service Isolation
- systemd unit runs as tgstream (unprivileged user)
- ProtectSystem=full, NoNewPrivileges=yes, PrivateTmp=true mandatory
- No root execution for main streaming service

### Update Safety
- yt-dlp updates happen via systemd-timer, not ad-hoc
- Update failures logged but do not crash main service
- Rollback path documented (pin yt-dlp version in requirements.txt if needed)

---

## Development Workflow

### Implementation Phase
1. **Spec Clarity**: All ambiguities (timeouts, error codes, edge cases) resolved before coding
2. **Test First**: Test written and reviewed before implementation code
3. **Code Review**: All changes reviewed against constitution principles
4. **Production Validation**: Tested on staging environment before live deploy

### Quality Gates
- Constitution violations → PR blocked
- Missing error handling → PR blocked
- Hardcoded secrets → PR blocked
- Missing tests for critical paths → PR blocked

### Governance
**Constitution supersedes all other practices.** If a convention or guideline conflicts with a MUST principle, the constitution wins.

**Amendments**: Changes to constitution require:
1. Explicit documentation of why current principle is insufficient
2. Proposed new principle or modification
3. Impact analysis (what breaks? what needs migration?)
4. Approval before implementation begins

---

## Reference

**Rules Synced From**: constitution.md (source of truth)  
**Last Validated**: 2025-11-08  
**Applicable To**: 002-prod-broadcast-improvements feature + all future features unless explicitly overridden

```
