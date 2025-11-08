```markdown
# Feature Specification: CI/CD Remote Deploy

**Feature Branch**: `001-cicd-remote-deploy`  
**Created**: 2025-11-08  
**Status**: Draft  
**Input**: User description: "использую CI/CD - развернуть нш проект на удаленном сервере"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated push-to-deploy (Priority: P1)

As a developer, when I merge code to the `main` branch, I want the CI/CD pipeline to build, test, package, and deploy the release automatically to the remote server so that the latest stable code runs in production with minimal manual effort.

**Why this priority**: This is the primary delivery flow that provides continuous delivery value and reduces manual errors and lead time.

**Independent Test**: Merge a small, non-breaking change to `main`. The CI pipeline should run and report success, produce an artifact, upload it to the remote server under `/opt/tg_video_streamer/releases/<timestamp>`, update `/opt/tg_video_streamer/current` to the new release, and restart the `tg_video_streamer` systemd service. Verify the service journal shows successful start and application health checks pass.

**Acceptance Scenarios**:

1. **Given** a green CI build for `main`, **When** pipeline reaches deploy stage, **Then** the remote server has a new release directory with the artifact unpacked and a symlink `current` pointing to it.
2. **Given** deploy succeeded, **When** systemd is restarted, **Then** `tg_video_streamer` service is active and logs show no fatal import/runtime errors within 60 seconds.

---

### User Story 2 - Safe rollback (Priority: P2)

As an operator, I want the CI/CD pipeline to support quick rollback to the previous release so I can recover service quickly if the new release fails.

**Why this priority**: Rollback capability reduces MTTR and gives operators safe escape if a bad release is deployed.

**Independent Test**: Trigger the rollback job (manual pipeline run or dedicated UI). The pipeline should update `/opt/tg_video_streamer/current` to point to the previous release directory and restart the service. Confirm the app health returns to the previous baseline.

**Acceptance Scenarios**:

1. **Given** two releases exist, **When** rollback job is executed, **Then** `current` points to the previous release and the service restarts cleanly.

---

### User Story 3 - Manual/Hotfix deploy (Priority: P3)

As a developer, I want to trigger a manual deploy for a hotfix build (from a release branch or a tag) so I can patch production quickly without going through the full automated cadence.

**Why this priority**: Hotfix path is required for urgent fixes and must be faster and auditable.

**Independent Test**: Manually trigger the manual-deploy job with a specific artifact (commit/tag). The pipeline should deploy that artifact to a new release directory and restart the service.

**Acceptance Scenarios**:

1. **Given** an artifact created by CI, **When** operator triggers manual deploy with that artifact identifier, **Then** that specific artifact is deployed and service restarted.

---

### Edge Cases

- What happens when SSH/connection to remote server fails mid-deploy? The deploy pipeline must detect failure, not update the `current` symlink, keep a safe backup, and notify operators.
- What if remote Python dependency installation fails? The pipeline should record logs, keep the previous release untouched, and mark the deployment as failed with logs collected.
- If disk space on remote server is low, the pipeline should detect insufficient space before unpacking and abort cleanly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CI/CD system MUST run on a push or merge event to `main` and be configurable to run on tags/branches for manual/hotfix deploys.
- **FR-002**: The pipeline MUST perform the following stages: checkout, unit/static tests, build/package artifact, artifact storage (temporary), deploy to remote server, post-deploy smoke checks.
- **FR-003**: The pipeline MUST create a per-release deployment directory on the remote server at `/opt/tg_video_streamer/releases/<timestamp-or-version>` and keep at least the last N releases (configurable).
- **FR-004**: The pipeline MUST use an atomic update pattern: deploy to a new release dir, verify, then update `/opt/tg_video_streamer/current` symlink to point to new release.
- **FR-005**: The pipeline MUST create a Python virtual environment per release, install dependencies from `requirements.txt`, and verify imports (smoke test) before switching `current`.
- **FR-006**: The pipeline MUST back up the remote `.env` to `<path>.bak.<timestamp>` before copying a new `.env` and must not expose secrets in logs.
- **FR-007**: The pipeline MUST support rollback to the previous release using a dedicated job that simply updates the `current` symlink and restarts the service.
- **FR-008**: The pipeline MUST authenticate to the remote server with SSH keys stored securely in CI secrets or a secrets manager; the pipeline must not store private keys in plaintext in repository.
- **FR-009**: The pipeline MUST collect and persist deployment logs and artifacts for auditing and debugging for at least 30 days (configurable).
- **FR-010**: The pipeline MUST run under least-privilege: deploy operations should run under a dedicated `tgstream` user on the remote host or use sudo with limited allowed commands.
- **FR-011**: The pipeline MUST expose a manual trigger and parameters for manual/hotfix deploys (artifact id, release tag, or branch name).
- **FR-012**: The pipeline MUST notify configured channels (e.g., email/Slack) on success/failure and include links to logs and artifact ids.

### Key Entities

- **Release**: A packaged artifact produced by CI (build + dependencies) and deployed to `/opt/tg_video_streamer/releases/<id>`.
- **Artifact**: The built distribution or archive (tar/wheel) uploaded by CI for deployment.
- **Environment**: Set of runtime variables (`.env`) required by the application.
- **Deploy Job**: CI job responsible for transferring artifact and performing remote orchestration.
- **Rollback Job**: CI job that reverts `current` symlink to previous release and restarts service.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A full automated deploy (build → deploy → restart) completes successfully within 10 minutes for a typical change (measured median over 10 runs).
- **SC-002**: Post-deploy smoke checks (application start + basic health check) pass within 60 seconds for 95% of automated deploys.
- **SC-003**: Rollback to a previous release completes within 5 minutes and restores service health to the pre-deploy baseline in 95% of rollback attempts.
- **SC-004**: Secrets are never printed in CI logs; sensitive fields must be masked in 100% of pipeline logs.
- **SC-005**: Deploy success rate on `main` (non-flaky) must be >= 98% over a 30-day window (excludes planned maintenance).

### Acceptance Criteria (short)

- The repo must include an executable CI pipeline config (e.g., `.github/workflows/deploy.yml`) that implements FR-001..FR-012.
- The pipeline must be demonstrable in a staging environment and then enabled for production host `10.99.99.2` (or configured host supplied by ops).
- The pipeline must not require interactive secrets entry during automated runs.

## Assumptions

- The remote server is reachable via SSH and has a `tgstream` user with proper permissions and sudo for specific actions.
- The remote host runs systemd and supports per-release layout under `/opt/tg_video_streamer`.
- Python runtime on remote is 3.12 (or compatible) and required system packages for native builds (rust, cmake, libopus, libsodium, ffmpeg) are either pre-installed or installable by ops.
- CI provider supports storing secrets (GitHub Actions secrets, GitLab CI variables, or similar) and running deploy jobs with SSH keys.
- The repository already follows the per-release layout conventions used by the project (releases/<id>, current symlink, per-release venv).

## Non-functional Requirements

- **NFR-001**: The pipeline must fail fast and provide clear error messages and logs for each stage.
- **NFR-002**: The pipeline should minimize downtime — switching `current` must be atomic and service restarts should be limited to the minimum required window.
- **NFR-003**: The pipeline must support dry-run mode for staging tests (no symlink switch).

## Next Steps

1. Create a staging workflow file `.github/workflows/deploy-staging.yml` implementing the pipeline skeleton.
2. Provision a staging host or container that mirrors production (with system packages) and run 3 successful automated deploys.
3. Add CI secrets (SSH key, remote user, path, notification tokens) to CI provider.
4. Run post-deploy validation on production host `10.99.99.2` with a non-production tag.

---

**Spec status**: Draft — ready for review and clarification.

```