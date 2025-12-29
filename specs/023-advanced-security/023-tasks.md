# Tasks for Spec 023: Advanced Security

## Phase 1: Nginx Configuration
- [x] **T001** Create `config/nginx/security-headers.conf` with CSP, HSTS, etc.
- [x] **T002** Create `config/nginx/rate-limit.conf` with `limit_req_zone` definitions.
- [x] **T003** Update `frontend/nginx.conf` (or main `nginx.conf`) to include these configurations.
- [x] **T004** Configure connection limits (`limit_conn`) in Nginx.

## Phase 2: Backend Hardening
- [x] **T005** Update `backend/src/core/config.py` to include `ALLOWED_ORIGINS` (list of strings).
- [x] **T006** Update `backend/src/main.py` to use `settings.ALLOWED_ORIGINS` for CORS.
- [x] **T007** Ensure `template.env` includes `ALLOWED_ORIGINS` with a default value.

## Phase 3: Verification & Audit
- [x] **T008** Create `tests/security/test_headers.py` to verify security headers.
- [x] **T009** Create `tests/security/test_rate_limit.py` to verify rate limiting.
- [x] **T010** Create `tests/security/test_cors.py` to verify CORS restrictions.
- [ ] **T011** Run all security tests and fix any issues.

## Phase 4: Documentation
- [x] **T012** Update `docs/SECURITY.md` (or create if missing) with new security measures.
- [x] **T013** Update `README.md` to mention security features.
