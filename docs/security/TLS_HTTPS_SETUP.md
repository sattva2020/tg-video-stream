# TLS/HTTPS Configuration and Verification

## Overview

This document describes the TLS/HTTPS security features implemented for the Telegram Broadcast API to ensure secure communications and compliance with SOC 2 and GDPR requirements.

## Features

### 1. TLS Security Middleware

The `TLSSecurityMiddleware` automatically adds security headers and enforces HTTPS in production:

#### Security Headers Added

- **Strict-Transport-Security (HSTS)**: Forces HTTPS connections
  - `max-age=31536000` (1 year)
  - `includeSubDomains`
  - `preload` (for HSTS preload list)

- **X-Content-Type-Options: nosniff**: Prevents MIME-sniffing attacks

- **X-Frame-Options**: Prevents clickjacking
  - Production: `DENY`
  - Development: `SAMEORIGIN`

- **X-XSS-Protection: 1; mode=block**: Enables browser XSS filter

- **Content-Security-Policy**: Restricts content sources
  - Default: `'self'` only
  - Allows images from data and HTTPS
  - Prevents embedding in frames (production)

- **Referrer-Policy**: `strict-origin-when-cross-origin`

- **Permissions-Policy**: Controls browser features (geolocation, microphone, camera)

- **Server Header Removal**: Hides server information in production

#### HTTPS Redirect

In production mode with TLS enabled, the middleware automatically redirects HTTP requests to HTTPS.

### 2. Certificate Validation Utilities

The `tls_validator.py` module provides tools to validate TLS certificates:

- **Certificate Expiry Checking**: Checks if certificates are valid or expiring soon
- **Certificate Chain Validation**: Verifies certificate chain integrity
- **HTTPS Connection Testing**: Tests HTTPS connectivity to remote hosts
- **Configuration Status Reporting**: Comprehensive TLS security status

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# TLS/HTTPS Configuration
TLS_ENABLED=true  # Enable TLS (set to true in production)
TLS_CERT_PATH=/etc/ssl/certs/app.crt  # Path to TLS certificate
TLS_KEY_PATH=/etc/ssl/private/app.key  # Path to TLS private key

# HSTS Configuration
HSTS_MAX_AGE=31536000  # HSTS max-age in seconds (default: 1 year)
HSTS_INCLUDE_SUBDOMAINS=true  # Include subdomains in HSTS
HSTS_PRELOAD=true  # Allow HSTS preload

# Security Headers
X_FRAME_OPTIONS=DENY  # X-Frame-Options header value
REFERRER_POLICY=strict-origin-when-cross-origin  # Referrer-Policy header
```

### Production Setup

1. **Obtain TLS Certificate**:
   ```bash
   # Using Let's Encrypt with certbot
   sudo certbot certonly --standalone -d yourdomain.com
   ```

2. **Configure Application**:
   ```bash
   # In production .env
   ENVIRONMENT=production
   TLS_ENABLED=true
   TLS_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
   TLS_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   ```

3. **Configure Reverse Proxy (Optional)**:
   If using Nginx or Apache as a reverse proxy, configure TLS at the proxy level and set:
   ```bash
   TLS_ENABLED=false  # TLS handled by proxy
   ```
   The middleware will respect `X-Forwarded-Proto` header from the proxy.

## API Endpoints

### Get TLS Configuration

**GET** `/api/system/tls/config`

Returns current TLS configuration.

```json
{
  "production_mode": true,
  "tls_enabled": true,
  "tls_cert_path": "/etc/ssl/certs/app.crt",
  "tls_key_path": "/etc/ssl/private/app.key",
  "https_enforced": true,
  "hsts_enabled": true,
  "security_headers_enabled": true
}
```

### Check Certificate Validity

**GET** `/api/system/tls/certificate`

Checks TLS certificate validity and expiry.

```json
{
  "tls_enabled": true,
  "valid_from": "2025-01-01T00:00:00Z",
  "valid_until": "2026-01-01T00:00:00Z",
  "days_until_expiry": 365,
  "is_expired": false,
  "is_not_yet_valid": false,
  "is_valid": true,
  "status": "valid",
  "warning": null,
  "cert_path": "/etc/ssl/certs/app.crt",
  "issuer": "CN=Let's Encrypt Authority X3",
  "subject": "CN=yourdomain.com"
}
```

**Status values**:
- `valid`: Certificate is valid and not expiring soon
- `expiring`: Certificate expires in 30 days or less
- `expiring_soon`: Certificate expires in 7 days or less
- `expired`: Certificate has expired
- `not_yet_valid`: Certificate is not yet valid

### Get TLS Security Status

**GET** `/api/system/tls/status`

Comprehensive TLS security status with warnings and recommendations.

```json
{
  "tls_enabled": true,
  "environment": "production",
  "certificate_path": "/etc/ssl/certs/app.crt",
  "key_path": "/etc/ssl/private/app.key",
  "certificate_valid": true,
  "certificate_expiry": "2026-01-01T00:00:00Z",
  "certificate_chain": {
    "is_valid": true,
    "is_self_signed": false,
    "signature_algorithm": "sha256WithRSAEncryption",
    "subject": "CN=yourdomain.com",
    "issuer": "CN=Let's Encrypt Authority X3",
    "serial_number": "0x1234567890abcdef",
    "version": "v1"
  },
  "warnings": [],
  "recommendations": []
}
```

## Monitoring and Alerting

### Certificate Expiry Monitoring

Use the `/api/system/tls/status` endpoint to monitor certificate expiry:

```bash
# Check certificate status
curl https://your-api.com/api/system/tls/status

# Parse with jq for scripting
curl https://your-api.com/api/system/tls/status | jq '.days_until_expiry'
```

### Alerting Recommendations

Set up alerts for:
- Certificate expiring in less than 30 days
- Certificate expired
- TLS not enabled in production
- Certificate validation errors

## Compliance

### SOC 2 Compliance

This implementation addresses SOC 2 requirements for:
- **CC6.1**: Logical and physical access controls (HTTPS enforcement)
- **CC7.2**: System monitoring (certificate validation endpoints)
- **CC8.1**: Change detection (security headers)

### GDPR Compliance

Supports GDPR requirements for:
- **Article 32**: Security of processing (encryption in transit via TLS)
- **Article 25**: Data protection by design (HTTPS enforced by default)

## Testing

### Manual Verification

1. **Check HTTPS Redirect**:
   ```bash
   curl -I http://yourdomain.com  # Should return 301 to HTTPS
   ```

2. **Verify Security Headers**:
   ```bash
   curl -I https://yourdomain.com | grep -E "Strict-Transport-Security|X-Content-Type-Options|X-Frame-Options"
   ```

3. **Check Certificate Validity**:
   ```bash
   curl https://yourdomain.com/api/system/tls/certificate
   ```

4. **Test SSL Configuration**:
   ```bash
   # Using sslscan (install with: apt-get install sslscan)
   sslscan yourdomain.com:443

   # Using testssl.sh (install from GitHub)
   ./testssl.sh https://yourdomain.com
   ```

### Automated Testing

```python
import requests

def test_tls_security():
    # Test HTTPS redirect
    response = requests.get('http://yourdomain.com', allow_redirects=False)
    assert response.status_code == 301
    assert response.headers['Location'].startswith('https://')

    # Test security headers
    response = requests.get('https://yourdomain.com')
    assert 'Strict-Transport-Security' in response.headers
    assert 'X-Content-Type-Options' in response.headers
    assert 'X-Frame-Options' in response.headers

    # Test certificate endpoint
    cert_info = requests.get('https://yourdomain.com/api/system/tls/certificate').json()
    assert cert_info['is_valid'] is True
```

## Troubleshooting

### Common Issues

**1. HTTPS redirect not working**
- Verify `TLS_ENABLED=true` and `ENVIRONMENT=production`
- Check that reverse proxy is not stripping headers
- Ensure `X-Forwarded-Proto` is set correctly if using proxy

**2. Certificate validation fails**
- Verify certificate file path is correct
- Check certificate file permissions
- Ensure certificate and key match
- Verify certificate is not expired

**3. Security headers not appearing**
- Check middleware order (TLS middleware should be first)
- Verify no other middleware is removing headers
- Check for reverse proxy overriding headers

## Best Practices

1. **Always use HTTPS in production**
   - Set `ENVIRONMENT=production` and `TLS_ENABLED=true`

2. **Use strong TLS configuration**
   - Minimum TLS 1.2
   - Strong cipher suites
   - Disable weak protocols (SSLv3, TLS 1.0, TLS 1.1)

3. **Monitor certificate expiry**
   - Set up automated monitoring
   - Use alerting for expiring certificates
   - Auto-renew certificates (Let's Encrypt certbot)

4. **Regular security scans**
   - Use SSL Labs test: https://www.ssllabs.com/ssltest/
   - Run security scanner in CI/CD pipeline

5. **Keep certificates secure**
   - Private keys should have restrictive permissions (600)
   - Never commit certificates to version control
   - Use certificate rotation policies

## References

- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [RFC 6797 - HTTP Strict Transport Security](https://tools.ietf.org/html/rfc6797)
