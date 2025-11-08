# Tasks: Project Critical Analysis

**Input**: Design documents from `/specs/001-critical-analysis/`
**Prerequisites**: plan.md (required), spec.md (required), data-model.md, contracts/, research.md, quickstart.md

**Tests**: Not explicitly requested in feature specification - no test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow the structure defined in plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for analysis tooling

- [x] T001 Create src/analysis/ directory structure with __init__.py files
- [x] T002 Create src/analysis/analyzers/ directory with __init__.py
- [x] T003 [P] Create src/analysis/models/ directory with __init__.py
- [x] T004 [P] Create src/analysis/reporters/ directory with __init__.py
- [x] T005 [P] Create src/analysis/reporters/templates/ directory for Jinja2 templates
- [x] T006 [P] Create specs/001-critical-analysis/reports/ directory for output
- [x] T007 Update requirements.txt with analysis dependencies (radon, pylint, bandit, pydocstyle, safety, pip-audit, jinja2, markdown)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 [P] Implement Finding model in src/analysis/models/finding.py with pydantic validation
- [x] T009 [P] Implement Recommendation model in src/analysis/models/recommendation.py with pydantic validation
- [x] T010 [P] Implement ComplianceItem model in src/analysis/models/compliance_item.py with pydantic validation
- [x] T011 [P] Implement RiskAssessment model in src/analysis/models/risk_assessment.py with pydantic validation
- [x] T012 [P] Implement Report model in src/analysis/models/report.py with pydantic validation and aggregation logic
- [x] T013 [P] Implement supporting types (Location, ConstitutionViolation, EffortEstimate, etc.) in src/analysis/models/__init__.py
- [x] T014 Implement base analyzer abstract class in src/analysis/analyzers/__init__.py defining common interface (analyze() method, error handling)
- [x] T015 Implement Markdown reporter in src/analysis/reporters/markdown.py with Jinja2 rendering
- [x] T016 [P] Implement constitution loader utility in src/analysis/utils.py to parse .specify/memory/constitution.md
- [x] T017 [P] Implement codebase snapshot utility in src/analysis/utils.py to extract git commit, branch, LOC
- [x] T018 Implement CLI argument parser in src/analysis/cli.py with options for --all, --architecture, --code-quality, --security, --performance, --output

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Architecture & Design Review (Priority: P1) 🎯 MVP

**Goal**: Deliver architecture analysis report identifying components, patterns, and constitution compliance

**Independent Test**: Run `python -m src.analysis.cli --architecture` and verify report contains: architectural components (Pyrogram, PyTgCalls, FFmpeg, playlist), design patterns (async, piping, config injection), constitution compliance for all 5 principles

### Implementation for User Story 1

- [x] T019 [P] [US1] Create architecture analyzer skeleton in src/analysis/analyzers/architecture.py extending base analyzer
- [x] T020 [US1] Implement codebase structure analysis in src/analysis/analyzers/architecture.py (identify main.py, utils.py, generate_session.py components)
- [x] T021 [US1] Implement design pattern detection in src/analysis/analyzers/architecture.py (detect async/await, argparse/dotenv config, direct piping)
- [x] T022 [US1] Implement constitution compliance validator in src/analysis/analyzers/architecture.py (check all 5 principles with evidence collection)
- [x] T023 [US1] Implement AST parser for Principle I validation in src/analysis/analyzers/constitution.py (detect input(), GUI imports, interactive prompts)
- [x] T024 [US1] Implement AST parser for Principle III validation in src/analysis/analyzers/constitution.py (check try-except coverage on external calls)
- [x] T025 [US1] Implement AST parser for Principle IV validation in src/analysis/analyzers/constitution.py (detect hardcoded strings, magic values)
- [x] T026 [US1] Implement AST parser for Principle V validation in src/analysis/analyzers/constitution.py (detect socket, http.server, flask imports)
- [x] T027 [US1] Create architecture report Jinja2 template in src/analysis/reporters/templates/architecture.md.j2
- [x] T028 [US1] Integrate architecture analyzer with CLI --architecture option in src/analysis/cli.py
- [x] T029 [US1] Add error handling for missing constitution file or parse errors in src/analysis/analyzers/architecture.py
- [x] T030 [US1] Add logging for architecture analysis steps in src/analysis/analyzers/architecture.py

**Checkpoint**: At this point, User Story 1 should be fully functional - run `python -m src.analysis.cli --architecture` to generate architecture-review.md

---

## Phase 4: User Story 2 - Code Quality & Maintainability Assessment (Priority: P2)

**Goal**: Deliver code quality report with complexity metrics, documentation coverage, and refactoring recommendations

**Independent Test**: Run `python -m src.analysis.cli --code-quality` and verify report contains: cyclomatic complexity for each function, docstring coverage %, pylint findings with severity ratings, actionable recommendations

### Implementation for User Story 2

- [x] T031 [P] [US2] Create code quality analyzer skeleton in src/analysis/analyzers/code_quality.py extending base analyzer
- [x] T032 [US2] Integrate radon for complexity analysis in src/analysis/analyzers/code_quality.py (cyclomatic complexity, maintainability index per file/function)
- [x] T033 [US2] Integrate pylint for code quality checks in src/analysis/analyzers/code_quality.py (PEP 8, bug detection, design issues)
- [x] T034 [US2] Integrate pydocstyle for documentation coverage in src/analysis/analyzers/code_quality.py (PEP 257 docstring validation)
- [x] T035 [US2] Implement finding severity mapper in src/analysis/analyzers/code_quality.py (map complexity >15 → high, 10-15 → medium, <10 → low)
- [x] T036 [US2] Implement recommendation generator in src/analysis/analyzers/code_quality.py (suggest refactoring for high complexity functions)
- [x] T037 [US2] Create code quality report Jinja2 template in src/analysis/reporters/templates/code_quality.md.j2
- [x] T038 [US2] Integrate code quality analyzer with CLI --code-quality option in src/analysis/cli.py
- [x] T039 [US2] Add error handling for tool failures (radon/pylint crash) in src/analysis/analyzers/code_quality.py with partial report generation
- [x] T040 [US2] Add logging for code quality analysis steps in src/analysis/analyzers/code_quality.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - run both `--architecture` and `--code-quality` to verify

---

## Phase 5: User Story 3 - Security & Operational Risk Assessment (Priority: P3)

**Goal**: Deliver security report with vulnerability findings, dependency CVEs, risk assessments, and constitution security compliance

**Independent Test**: Run `python -m src.analysis.cli --security` and verify report contains: bandit security findings, safety/pip-audit CVE reports, risk assessments with scores, credential handling evaluation, systemd configuration review

### Implementation for User Story 3

- [x] T041 [P] [US3] Create security analyzer skeleton in src/analysis/analyzers/security.py extending base analyzer
- [x] T042 [US3] Integrate bandit for security vulnerability scanning in src/analysis/analyzers/security.py (hardcoded passwords, SQL injection, etc.)
- [x] T043 [US3] Integrate safety for CVE detection in src/analysis/analyzers/security.py (scan requirements.txt against vulnerability database)
- [x] T044 [US3] Integrate pip-audit for supply chain security in src/analysis/analyzers/security.py (PyPI package auditing)
- [x] T045 [US3] Implement risk assessment calculator in src/analysis/analyzers/security.py (likelihood × impact → risk score per formula in data-model.md)
- [x] T046 [US3] Implement credential handling validator in src/analysis/analyzers/security.py (check for SESSION_STRING, API keys, passwords in code)
- [x] T047 [US3] Implement systemd service security review in src/analysis/analyzers/security.py (parse tg_video_streamer.service for Restart, User, permissions)
- [x] T048 [US3] Implement constitution security principles validator in src/analysis/analyzers/security.py (Principles IV and V specific checks)
- [x] T049 [US3] Create security report Jinja2 template in src/analysis/reporters/templates/security.md.j2 with risk matrix tables
- [x] T050 [US3] Integrate security analyzer with CLI --security option in src/analysis/cli.py
- [x] T051 [US3] Add error handling for network failures in safety/pip-audit in src/analysis/analyzers/security.py (use cached databases if available)
- [x] T052 [US3] Add logging for security analysis steps and sensitive finding detection in src/analysis/analyzers/security.py

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently

---

## Phase 6: User Story 4 - Performance & Resource Optimization Analysis (Priority: P4)

**Goal**: Deliver performance report with resource consumption analysis, async anti-patterns, optimization recommendations

**Independent Test**: Run `python -m src.analysis.cli --performance` and verify report contains: memory usage patterns, CPU optimization opportunities, async/await anti-pattern detection, resource efficiency compliance validation

### Implementation for User Story 4

- [x] T053 [P] [US4] Create performance analyzer skeleton in src/analysis/analyzers/performance.py extending base analyzer
- [x] T054 [US4] Implement async anti-pattern detector in src/analysis/analyzers/performance.py using AST (blocking I/O in async, time.sleep vs asyncio.sleep)
- [x] T055 [US4] Implement dependency resource profiler in src/analysis/analyzers/performance.py (check requirements.txt for high-memory packages)
- [x] T056 [US4] Implement FFmpeg configuration analyzer in src/analysis/analyzers/performance.py (parse utils.py for encoding settings, validate quality presets)
- [x] T057 [US4] Implement constitution Principle II validator in src/analysis/analyzers/performance.py (check resource efficiency: no caching, direct piping, sequential processing)
- [x] T058 [US4] Implement profiling guidance generator in src/analysis/analyzers/performance.py (recommendations for memory_profiler and cProfile usage)
- [x] T059 [US4] Create performance report Jinja2 template in src/analysis/reporters/templates/performance.md.j2
- [x] T060 [US4] Integrate performance analyzer with CLI --performance option in src/analysis/cli.py
- [x] T061 [US4] Add error handling for missing files (utils.py, requirements.txt) in src/analysis/analyzers/performance.py
- [x] T062 [US4] Add logging for performance analysis steps in src/analysis/analyzers/performance.py

**Checkpoint**: All user stories (1-4) should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and finalize the analysis tool

- [x] T063 [P] Implement --all option handler in src/analysis/cli.py to run all four analyzers sequentially
- [x] T064 [P] Implement report metadata collection in src/analysis/reporters/markdown.py (tool versions, runtime, config)
- [x] T065 [P] Add comprehensive error handling wrapper in src/analysis/cli.py for graceful failures
- [x] T066 [P] Implement progress indicators in src/analysis/cli.py (e.g., "  [1/4] Architecture review... ✓")
- [x] T067 [P] Implement summary report generator in src/analysis/cli.py (total findings by severity, compliance %, critical warnings)
- [x] T068 [P] Add configuration file loader in src/analysis/cli.py to support .analysis-config.yaml per quickstart.md
- [x] T069 [P] Implement --min-severity filter in src/analysis/cli.py to suppress low/medium findings
- [x] T070 [P] Implement --format json option in src/analysis/cli.py for JSON output (alternative to Markdown)
- [x] T071 [P] Implement --verbose logging option in src/analysis/cli.py
- [x] T072 [P] Add JSON schema validation in src/analysis/reporters/json_reporter.py using contracts/report-schema.json
- [x] T073 [P] Update README.md with analysis tool usage section referencing quickstart.md
- [x] T074 [P] Create .analysis-config.yaml.example in repository root with default configuration
- [x] T075 [P] Add .gitignore entry for specs/001-critical-analysis/reports/*.md (exclude generated reports)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - No dependencies on other stories

**Key Insight**: All user stories are independent after Foundational phase completes. This enables true parallel development.

### Within Each User Story

- Create analyzer skeleton first (provides structure for subsequent tasks)
- Integration tasks depend on analysis logic being complete
- Template creation can happen in parallel with analyzer implementation
- Error handling and logging are final polish within each story

### Parallel Opportunities

**Phase 1 (Setup)**: Tasks T003, T004, T005, T006, T007 can run in parallel after T001-T002

**Phase 2 (Foundational)**:
- Models (T008-T013) can all run in parallel
- Utilities (T016, T017) can run in parallel with models
- T014 (base analyzer) should complete before user story analyzers start
- T015, T018 can run in parallel after models complete

**Phase 3 (US1)**:
- T019 can start immediately after Phase 2
- T023-T026 (AST validators) can run in parallel
- T027, T029, T030 can run in parallel after T022 completes

**Phase 4 (US2)**:
- T031 can start immediately after Phase 2 (independent of US1)
- T032, T033, T034 (tool integrations) can run in parallel
- T037, T039, T040 can run in parallel after T036 completes

**Phase 5 (US3)**:
- T041 can start immediately after Phase 2 (independent of US1, US2)
- T042, T043, T044 (tool integrations) can run in parallel
- T046, T047, T048 (validators) can run in parallel
- T049, T051, T052 can run in parallel after T048 completes

**Phase 6 (US4)**:
- T053 can start immediately after Phase 2 (independent of US1, US2, US3)
- T054, T055, T056 (analyzers) can run in parallel
- T059, T061, T062 can run in parallel after T058 completes

**Phase 7 (Polish)**:
- ALL tasks (T063-T075) can run in parallel once all user stories complete

---

## Parallel Example: Foundational Phase

Once Phase 1 (Setup) completes, launch these tasks together:

```bash
# All model tasks (no dependencies on each other)
T008: Implement Finding model in src/analysis/models/finding.py
T009: Implement Recommendation model in src/analysis/models/recommendation.py
T010: Implement ComplianceItem model in src/analysis/models/compliance_item.py
T011: Implement RiskAssessment model in src/analysis/models/risk_assessment.py
T012: Implement Report model in src/analysis/models/report.py
T013: Implement supporting types in src/analysis/models/__init__.py

# Utilities (can run alongside models)
T016: Implement constitution loader in src/analysis/utils.py
T017: Implement codebase snapshot in src/analysis/utils.py
```

After models complete, launch:
```bash
T014: Base analyzer abstract class
T015: Markdown reporter
T018: CLI argument parser
```

---

## Parallel Example: User Story Phase (After Foundational)

Once Phase 2 (Foundational) completes, **ALL four user stories can start in parallel**:

```bash
# Developer A: User Story 1
T019: Architecture analyzer skeleton
T020-T030: Architecture analysis implementation

# Developer B: User Story 2
T031: Code quality analyzer skeleton
T032-T040: Code quality analysis implementation

# Developer C: User Story 3
T041: Security analyzer skeleton
T042-T052: Security analysis implementation

# Developer D: User Story 4
T053: Performance analyzer skeleton
T054-T062: Performance analysis implementation
```

Each developer works independently on their user story, testing as they go.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (7 tasks)
2. Complete Phase 2: Foundational (11 tasks - CRITICAL)
3. Complete Phase 3: User Story 1 (12 tasks)
4. **STOP and VALIDATE**: Run `python -m src.analysis.cli --architecture`
5. Verify architecture-review.md contains all required sections
6. Deploy/demo if ready (minimum viable analysis tool with constitution compliance)

**Estimated Effort**: 30 tasks for MVP

### Incremental Delivery

1. **Sprint 1**: Setup + Foundational → Foundation ready (18 tasks)
2. **Sprint 2**: User Story 1 → Test independently → Deploy/Demo (12 tasks, MVP!)
3. **Sprint 3**: User Story 2 → Test independently → Deploy/Demo (10 tasks)
4. **Sprint 4**: User Story 3 → Test independently → Deploy/Demo (12 tasks)
5. **Sprint 5**: User Story 4 → Test independently → Deploy/Demo (10 tasks)
6. **Sprint 6**: Polish → Finalize all features (13 tasks)

Each sprint adds value without breaking previous stories.

### Parallel Team Strategy

With 4 developers after Foundational phase completes:

1. **Team completes Setup + Foundational together** (Days 1-3)
2. **Once Foundational is done** (Day 4+):
   - Developer A: User Story 1 (Architecture)
   - Developer B: User Story 2 (Code Quality)
   - Developer C: User Story 3 (Security)
   - Developer D: User Story 4 (Performance)
3. **Stories complete and integrate independently** (Day 7)
4. **Team converges on Polish phase** (Day 8)

**Estimated Timeline**: 8 days with 4 developers working in parallel vs. 20+ days sequential

---

## Notes

- **[P] tasks** = different files, no dependencies - can run in parallel
- **[Story] label** maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **No test tasks included**: Feature specification did not explicitly request TDD or test-first approach
- **All analyzers use common base class** from T014 ensuring consistent error handling
- **Constitution validation** is core to US1 but also validates principles in US2, US3, US4
- **Report generation** uses Jinja2 templates enabling easy customization without code changes
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Total Task Count

- **Phase 1 (Setup)**: 7 tasks
- **Phase 2 (Foundational)**: 11 tasks
- **Phase 3 (US1 - Architecture)**: 12 tasks
- **Phase 4 (US2 - Code Quality)**: 10 tasks
- **Phase 5 (US3 - Security)**: 12 tasks
- **Phase 6 (US4 - Performance)**: 10 tasks
- **Phase 7 (Polish)**: 13 tasks

**TOTAL**: 75 tasks

**MVP Scope** (Setup + Foundational + US1): 30 tasks
**Parallel Opportunities**: 40+ tasks can run in parallel across phases
