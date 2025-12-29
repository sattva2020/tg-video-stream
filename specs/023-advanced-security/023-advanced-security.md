# Spec 023: Advanced Security

## 1. Introduction
This specification outlines the implementation of advanced security measures for the Telegram Streamer project. The goal is to harden the application against common web attacks, implement rate limiting to prevent abuse/DDoS, and ensure secure configuration of headers and CORS.

## 2. Scope
The scope includes:
- **Nginx Security Headers**: Implementing strict Content-Security-Policy (CSP), HSTS, X-Frame-Options, etc.
- **Rate Limiting**: Configuring Nginx to limit request rates for API and Authentication endpoints.
- **CORS Hardening**: Restricting Cross-Origin Resource Sharing to trusted domains only.
- **Security Audit**: Creating automated scripts to verify security configurations.
- **Basic DDoS Protection**: Connection limits and timeouts.

## 3. Technical Requirements

### 3.1. Nginx Configuration
- **Headers**:
  - `Content-Security-Policy`: Restrict sources for scripts, styles, images, etc.
  - `Strict-Transport-Security`: Enforce HTTPS.
  - `X-Frame-Options`: Prevent clickjacking.
  - `X-Content-Type-Options`: Prevent MIME type sniffing.
  - `Referrer-Policy`: Control referrer information.
  - `Permissions-Policy`: Disable unused browser features.
- **Rate Limiting**:
  - Zone `api_limit`: 10 requests/second for general API.
  - Zone `login_limit`: 5 requests/minute for login endpoints.
  - Burst settings to allow short spikes.
- **Connection Limits**:
  - Limit concurrent connections per IP.

### 3.2. Backend Configuration (FastAPI)
- **CORS**:
  - Update `CORSMiddleware` to accept specific origins from environment variables (`ALLOWED_ORIGINS`).
  - Disable wildcard `*` for origins in production.

### 3.3. Verification
- **Audit Script**: A Python or Shell script to:
  - Check if security headers are present in responses.
  - Test rate limiting by sending rapid requests.
  - Verify CORS behavior with different origins.

## 4. Implementation Plan
1.  **Analyze Current Config**: Review existing `nginx.conf` and `main.py`.
2.  **Implement Headers**: Create `security-headers.conf` and include it in Nginx.
3.  **Implement Rate Limiting**: Add `limit_req_zone` and `limit_req` directives.
4.  **Harden CORS**: Modify `backend/src/main.py` to use `ALLOWED_ORIGINS`.
5.  **Create Audit Tool**: Develop `tests/security/audit.py`.
6.  **Testing**: Verify all changes in a local Docker environment.

## 5. Success Criteria
- All specified security headers are present in HTTP responses.
- Requests exceeding the rate limit return `503 Service Unavailable` or `429 Too Many Requests`.
- CORS blocks requests from unauthorized origins.
- Security audit script passes.
