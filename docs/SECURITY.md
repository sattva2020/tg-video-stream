# Security Policy

## Overview
This document outlines the security measures implemented in the Telegram Streamer project to protect the application and user data.

## Network Security (Nginx)

### Security Headers
We enforce strict HTTP headers to mitigate common web attacks:
- **Content-Security-Policy (CSP)**: Restricts sources of executable scripts and resources.
- **Strict-Transport-Security (HSTS)**: Enforces HTTPS connections.
- **X-Frame-Options**: Prevents clickjacking by denying iframe embedding.
- **X-Content-Type-Options**: Prevents MIME-type sniffing.
- **X-XSS-Protection**: Enables browser XSS filtering.
- **Referrer-Policy**: Controls how much referrer information is sent.
- **Permissions-Policy**: Disables sensitive browser features (camera, mic, geolocation).

### Rate Limiting
To prevent abuse and DDoS attacks, we implement rate limiting at the Nginx level:
- **API Endpoints (`/api/`)**: 10 requests per second (burst 20).
- **Login Endpoints (`/api/auth/login`)**: 5 requests per minute (burst 2).
- **Connection Limits**: Maximum 10 concurrent connections per IP.

## Backend Security (FastAPI)

### CORS (Cross-Origin Resource Sharing)
CORS is strictly configured to allow requests only from trusted domains defined in `ALLOWED_ORIGINS`.
- **Development**: `http://localhost:3000`, `http://localhost:8000`
- **Production**: Must be configured in `.env`.

### Authentication
- **JWT**: JSON Web Tokens are used for stateless authentication.
- **Secure Cookies**: Tokens are stored in HttpOnly, Secure cookies (in production).

## Verification
Automated security tests are available in `tests/security/`:
- `test_headers.py`: Verifies presence and values of security headers.
- `test_rate_limit.py`: Simulates high-load traffic to test rate limiting.
- `test_cors.py`: Verifies CORS restrictions.

To run security tests:
```bash
pytest tests/security/
```

## Reporting Vulnerabilities
If you discover a security vulnerability, please report it to the development team immediately.
