# Fastly CDN Deployment Guide

**Last Updated:** 2026-01-23

This guide explains how to deploy the Telegram Video Streamer with Fastly CDN for global content delivery, edge caching of video assets, and optimized viewer experience worldwide.

## Overview

Fastly is an edge cloud platform with **80+ POPs (Points of Presence)** in **60+ cities** across **30+ countries** worldwide. Integrating Fastly with your video streaming application provides:

- **Global edge caching** - Video assets cached closer to viewers
- **Instant purges** - Real-time cache invalidation in <150ms
- **Edge computing** - Run custom logic at the edge with VCL (Varnish Configuration Language)
- **DDoS protection** - Built-in mitigation with always-on defense
- **TLS/SSL support** - Free shared certificates or custom certificates
- **Real-time analytics** - Instant insights with no log delay
- **WebSockets support** - Native WebSocket protocol support

## Architecture

```
Viewer → Fastly POP → Backend Origin / S3 / GCS
                ↓ (cache hit)
           Return cached video
```

### Fastly POPs by Region

| Region | Cities | POPs |
|--------|--------|------|
| North America | 20+ | Atlanta, Boston, Chicago, Dallas, Denver, Hayward, Los Angeles, Miami, Minneapolis, Montreal, New York, Newark, Palo Alto, Phoenix, Portland, Salt Lake City, San Jose, Seattle, Toronto, Vancouver, Washington DC |
| Europe | 20+ | Amsterdam, Athens, Barcelona, Berlin, Brussels, Bucharest, Copenhagen, Dublin, Frankfurt, Helsinki, London, Madrid, Manchester, Milan, Moscow, Munich, Oslo, Paris, Prague, Rome, Stockholm, Vienna, Warsaw, Zurich |
| Asia | 15+ | Bangalore, Bangkok, Beijing, Chennai, Chennai, Hong Kong, Jakarta, Kuala Lumpur, Manila, Mumbai, New Delhi, Osaka, Seoul, Singapore, Taipei, Tokyo |
| South America | 5+ | Bogotá, Buenos Aires, Lima, Medellín, Rio de Janeiro, São Paulo |
| Oceania | 5+ | Adelaide, Auckland, Melbourne, Perth, Sydney |
| Middle East | 3+ | Dubai, Manama, Tel Aviv |
| Africa | 2+ | Cape Town, Johannesburg |

## Prerequisites

### Fastly Account Requirements

- **Fastly Account** with appropriate permissions
- **Fastly API Token** (programmatic access)
- **Origin server** (your backend, S3, GCS, or any HTTP origin)
- **Custom domain** (optional, for TLS certificate)

### API Token Permissions

Create a Fastly API token with these permissions:

1. Go to **Fastly Dashboard** → **Account** → **API Tokens**
2. Click **Create API Token**
3. Token name: `tg-video-streamer-cdn`
4. Scope: Select the following permissions:
   - **Global**: Read, Write
   - **Account**: Read
   - **Service**: Read, Write, Purge
   - **Domain**: Read, Write

⚠️ **IMPORTANT**: Save your API token immediately - you won't be able to see it again!

### Application Requirements

- Backend service with CDN integration code (already implemented in `backend/src/infrastructure/external/fastly_client.py`)
- Environment variables configured for Fastly credentials
- Existing video streaming infrastructure

## Step 1: Create Fastly Account and API Token

### 1.1 Sign Up for Fastly

1. Go to [https://www.fastly.com/signup](https://www.fastly.com/signup)
2. Enter your email, name, and password
3. Verify your email address
4. Log in to the Fastly dashboard

### 1.2 Generate API Token

1. Go to **Account** → **API Tokens**
2. Click **Create Token**
3. Fill in the form:
   - **Token name**: `tg-video-streamer-cdn`
   - **Username**: Your email or a descriptive username
   - **Password**: Your account password
   - **Scope**: Select the permissions listed above
4. Click **Create**
5. **Copy the token immediately** (format: `fastly-example-token-1234567890`)

⚠️ **CRITICAL**: Save this token in a secure location - it will not be displayed again!

## Step 2: Create Fastly Service

### 2.1 Create Service via Fastly Dashboard

1. Go to **Fastly Dashboard** → **Create a Service**
2. **Service name**: `tg-video-streamer-cdn`
3. **Domain**:
   - **Domain name**: `cdn.yourdomain.com` (recommended) OR use the default Fastly domain
   - **Comment**: "Main CDN domain for video streaming"
4. Click **Next**

### 2.2 Configure Backend (Origin)

1. **Backend name**: `tg-video-backend`
2. **Backend address**: `your-backend-domain.com` OR `your-bucket.s3.amazonaws.com`
3. **Backend port**: `443` (HTTPS) or `80` (HTTP)
4. **Use SSL**: Yes (recommended)
5. **SSL hostname**: Match the backend address
6. **SNI hostname**: Match the backend address
7. **SSL check cert**: Yes (recommended for security)
8. **Override host**: `your-backend-domain.com` (if using S3, set to bucket name)

### 2.3 Configure Cache Settings

1. Click on the **Settings** gear icon for your backend
2. **Between origin timeout**: 60 seconds
3. **Connect timeout**: 5 seconds
4. **First byte timeout**: 15 seconds
5. **Max connections**: 200 (adjust based on your origin capacity)

### 2.4 Save and Activate

1. Click **Create Service**
2. Note your **Service ID** (e.g., `abc123def456`)
3. Click **Activate** to deploy the service

## Step 3: Configure SSL/TLS Certificate

### 3.1 Default Fastly SSL (Quick Start)

Fastly provides free SSL certificates for all domains on the `*.fastly.net` domain:

```
https://your-service-id.fastly.net/video1.mp4
```

This works immediately without additional configuration.

### 3.2 Custom Domain TLS (Recommended)

For your own domain:

1. Go to your service → **Domains**
2. Click **Add Domain**
3. **Domain name**: `cdn.yourdomain.com`
4. Click **Add**

Fastly will automatically provision a Let's Encrypt certificate for your domain:

#### DNS Validation

Add a CNAME record to your DNS provider:

```
Type: CNAME
Name: cdn
Value: [your-global-enabled-domain].global.fastly.net
TTL: 300
```

Wait for DNS propagation (usually 5-30 minutes). Fastly will automatically provision and renew the certificate.

⚠️ **Note**: Fastly uses Let's Encrypt for automatic certificates. This is free and requires no manual validation.

### 3.3 Bring Your Own Certificate (Optional)

If you have your own certificate:

1. Go to **TLS** → **Certificates**
2. Click **Upload Certificate**
3. Paste your certificate and private key
4. Click **Upload**

## Step 4: Configure Application

### 4.1 Set Environment Variables

Add to your `.env` file:

```env
# Enable CDN
CDN_ENABLED=true
CDN_PROVIDER=fastly

# Fastly Configuration
FASTLY_API_TOKEN=fastly-example-token-1234567890
FASTLY_SERVICE_ID=abc123def456
FASTLY_API_URL=https://api.fastly.com
```

### 4.2 Docker Compose / Systemd Service

If using Docker Compose, add to your compose file:

```yaml
services:
  backend:
    environment:
      - CDN_ENABLED=true
      - CDN_PROVIDER=fastly
      - FASTLY_API_TOKEN=${FASTLY_API_TOKEN}
      - FASTLY_SERVICE_ID=${FASTLY_SERVICE_ID}
      - FASTLY_API_URL=https://api.fastly.com
```

If using systemd, add to your service file:

```ini
[Service]
Environment="CDN_ENABLED=true"
Environment="CDN_PROVIDER=fastly"
Environment="FASTLY_API_TOKEN=fastly-example-token-1234567890"
Environment="FASTLY_SERVICE_ID=abc123def456"
Environment="FASTLY_API_URL=https://api.fastly.com"
```

### 4.3 Update DNS (If Using Custom Domain)

1. Go to your DNS provider
2. Add CNAME record:

```
Type: CNAME
Name: cdn
Value: your-global-enabled-domain.global.fastly.net
TTL: 300
```

3. Wait for DNS propagation (5-30 minutes)

## Step 5: Configure Cache Behaviors with VCL

### 5.1 Basic Cache Configuration

Fastly uses VCL (Varnish Configuration Language) to control caching behavior. The application provides built-in VCL snippets:

#### Cache Rules for Video Files

Create a VCL snippet in the Fastly dashboard:

1. Go to your service → **VCL Snippets**
2. Click **Create Snippet**
3. **Name**: `video_cache_rules`
4. **Type**: `recv` (within `sub vcl_recv`)
5. **Priority**: `10`
6. **VCL content**:

```vcl
# Cache MP4 files for 24 hours
if (req.url ~ "\.mp4$") {
  unset req.http.Cookie;
  unset req.http.Authorization;
  set req.http.X-Cache-TTL = "86400";
  return (hash);
}

# Cache HLS segments for 1 hour
if (req.url ~ "\.ts$") {
  unset req.http.Cookie;
  unset req.http.Authorization;
  set req.http.X-Cache-TTL = "3600";
  return (hash);
}

# Cache playlists for 5 minutes
if (req.url ~ "\.m3u8$") {
  unset req.http.Cookie;
  unset req.http.Authorization;
  set req.http.X-Cache-TTL = "300";
  return (hash);
}

# Cache thumbnails for 7 days
if (req.url ~ "\.(jpg|png|webp)$") {
  unset req.http.Cookie;
  unset req.http.Authorization;
  set req.http.X-Cache-TTL = "604800";
  return (hash);
}
```

7. Click **Create** and then **Activate**

### 5.2 Configure Cache TTLs via Backend API

The application supports dynamic cache rule configuration via API:

```bash
# Set cache rules for video files
curl -X POST http://localhost:8000/api/v1/cdn/cache-rules \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": [
      {
        "pattern": "*.mp4",
        "cache_ttl": 86400,
        "cache_key_static": true,
        "browser_ttl": 3600,
        "compress": false
      },
      {
        "pattern": "*.m3u8",
        "cache_ttl": 300,
        "cache_key_static": true,
        "browser_ttl": 60,
        "compress": true
      }
    ]
  }'
```

### 5.3 Set Cache-Control Headers on Origin

Configure your backend to send appropriate cache headers:

```python
# Example Python (Flask/Django)
@app.route('/video/<path:filename>')
def serve_video(filename):
    response = send_file(filename)
    if filename.endswith('.mp4'):
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
    elif filename.endswith('.m3u8'):
        response.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes
    elif filename.endswith('.ts'):
        response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour
    return response
```

## Step 6: Test Deployment

### 6.1 Verify Service Status

```bash
# Using Fastly CLI
pip install fastly
fastly service describe --service-id=abc123def456

# Or using curl
curl -H "Fastly-Key: fastly-example-token-1234567890" \
  https://api.fastly.com/service/abc123def456
```

### 6.2 Test CDN Backend Integration

```bash
# Test connection from backend
curl -X GET http://localhost:8000/api/v1/cdn/status

# Expected response:
{
  "provider": "fastly",
  "status": "healthy",
  "service_id": "abc123def456",
  "service_name": "tg-video-streamer-cdn",
  "active_version": 1,
  "backends": [
    {
      "name": "tg-video-backend",
      "status": "healthy",
      "address": "your-backend-domain.com"
    }
  ],
  "domains": [
    "cdn.yourdomain.com",
    "abc123def456.fastly.net"
  ]
}
```

### 6.3 Test Cache Purging (Fastly's Superpower!)

Fastly provides instant purging (typically <150ms):

```bash
# Purge specific URLs via backend API
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://cdn.yourdomain.com/video1.mp4"
    ]
  }'

# Response (instant!):
{
  "status": "ok",
  "purged": 1,
  "duration_ms": 45
}
```

### 6.4 Test Edge Access

```bash
# Access content via Fastly domain
curl -I https://abc123def456.fastly.net/video1.mp4

# Check response headers for cache status:
# X-Cache: HIT, HIT (cache hit at edge)
# X-Cache: MISS, MISS (cache miss)
# X-Cache-Hits: 1 (number of cache hits)
# X-Served-By: cache-iad-kiad7000125 (edge location: iad = Washington DC)
```

### 6.5 Test Geographic Distribution

Check which POP served your request:

```bash
curl -I https://cdn.yourdomain.com/video1.mp4

# Look for headers:
# X-Served-By: cache-lon-kiad7000100 (lhr = London)
# X-Served-By: cache-nrt-kiad7000150 (nrt = Tokyo)
# X-Served-By: cache-syd-kiad7000200 (syd = Sydney)
```

Common POP codes:
- `iad`: Washington DC, USA
- `lhr`: London, UK
- `fra`: Frankfurt, Germany
- `nrt`: Tokyo, Japan
- `syd`: Sydney, Australia
- `gru`: São Paulo, Brazil

## Step 7: Monitor Performance

### 7.1 Fastly Real-Time Analytics

Fastly provides instant analytics (no log delay):

1. Go to **Fastly Dashboard** → **Analytics**
2. View real-time metrics:
   - Requests per second
   - Bandwidth usage
   - Hit ratio
   - HTTP status codes
   - Top URLs
   - Geographic distribution

### 7.2 Application Metrics

The backend collects CDN metrics accessible via API:

```bash
# Get CDN usage metrics
curl -X GET "http://localhost:8000/api/v1/cdn/metrics?start_date=2026-01-20&end_date=2026-01-23" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Expected response:
{
  "total_bandwidth_gb": 1250.5,
  "total_requests": 45000,
  "cache_hit_ratio": 0.94,
  "average_response_time_ms": 38.5,
  "purge_duration_avg_ms": 45,
  "by_region": {
    "North America": {"requests": 20000, "bandwidth_gb": 550.2},
    "Europe": {"requests": 15000, "bandwidth_gb": 420.1},
    "Asia": {"requests": 8000, "bandwidth_gb": 220.5},
    "South America": {"requests": 1500, "bandwidth_gb": 45.3},
    "Oceania": {"requests": 500, "bandwidth_gb": 14.4}
  }
}
```

### 7.3 Real-time Monitoring Dashboard

Access the CDN management dashboard in the admin panel:

```
https://your-domain.com/cdn
```

Features:
- Real-time health status
- Cache hit ratio charts (updated every second)
- Geographic distribution map
- Bandwidth usage graphs
- Error rate monitoring
- Instant purge history

### 7.4 Set Up Fastly Alerts

Configure alerts in the Fastly dashboard:

1. Go to **Alerts** → **Create Alert**
2. Alert types:
   - **High hit ratio**: Notify when cache hit ratio drops below 80%
   - **High error rate**: Notify when 5xx errors exceed 5%
   - **Backend health**: Notify when origin goes down
   - **Rate limiting**: Notify when traffic spikes

## Step 8: Cost Optimization

### 8.1 Fastly Pricing (2026)

Fastly uses a bandwidth-based pricing model:

| Tier | Bandwidth (per month) | Price per GB |
|------|----------------------|--------------|
| Starter | 0-1 TB | $0.12 |
| Standard | 1-10 TB | $0.10 |
| High Volume | 10-100 TB | $0.08 |
| Enterprise | 100+ TB | Custom pricing |

**Additional costs**:
- Requests: $0.0075 per 10,000 requests
- SSL: Free (Let's Encrypt) or $100/month for custom certificates
- Shield (DDoS protection): Included

### 8.2 Cost Saving Strategies

1. **Optimize Cache Hit Ratio**:
   - Higher hit ratio = lower origin bandwidth costs
   - Target >90% hit ratio for video content
   - Use appropriate TTLs for different content types

2. **Use Conditional Features**:
   - Enable compression for text-based files (JSON, playlists)
   - Use `gzip` or `brotli` encoding
   - Reduces bandwidth usage by 60-80% for text content

3. **Request Rate Optimization**:
   - Implement client-side caching headers
   - Use `Cache-Control: public, max-age=...`
   - Reduces unnecessary requests

4. **Domain Strategy**:
   - Use multiple services for different traffic patterns
   - Separate high-traffic static content from dynamic API calls

5. **Edge Logic**:
   - Use VCL to block unnecessary requests at the edge
   - Implement rate limiting at the edge
   - Filter bad bots before they reach origin

### 8.3 Cost Monitoring

Set up spending alerts:

1. Go to **Account** → **Billing**
2. Set up **Monthly spend alerts**
3. Configure threshold (e.g., alert at $100, $500, $1000)
4. Add email/Slack notifications

## Step 9: Security Best Practices

### 9.1 Use TLS/SSL Everywhere

Fastly provides free TLS certificates:

```vcl
# Force HTTPS redirect (add to vcl_recv)
if (req.http.Fastly-SSL) {
  return (pass);
}
```

### 9.2 Restrict Origin Access

Protect your origin by requiring Fastly IP addresses:

1. Go to your service → **Origins** → **Shields**
2. Enable **Origin Shield** for additional protection
3. Configure your origin firewall to allow only Fastly IPs

Fastly IP ranges: [https://www.fastly.com/documentation/reference/ips](https://www.fastly.com/documentation/reference/ips)

```bash
# Example: Allow Fastly IPs in iptables
# Download Fastly IPs
curl https://www.fastly.com/documentation/reference/ips/fastly-ip-ranges.json

# Add to your firewall (example for iptables)
iptables -A INPUT -s 23.235.32.0/20 -j ACCEPT
iptables -A INPUT -s 43.249.72.0/22 -j ACCEPT
# ... add all Fastly IP ranges
```

### 9.3 Enable Fastly Web Application Firewall (WAF)

Fastly offers a built-in WAF:

1. Go to your service → **Security**
2. Enable **WAF**
3. Choose ruleset:
   - OWASP Core Rule Set (recommended)
   - Fastly managed rules
   - Custom rules

### 9.4 Rate Limiting

Implement rate limiting at the edge:

```vcl
# Add to vcl_recv
# Rate limit by IP (example: 100 requests per minute)
if (ratelimit.check(
    key=client.ip,
    window=60s,
    limit=100,
    action="reject"
)) {
  error 429 "Too Many Requests";
}
```

### 9.5 Bot Protection

Protect against bad bots:

```vcl
# Add to vcl_recv
# Block known bad user agents
if (req.http.User-Agent ~ "(bot|crawl|spider|scraper)") {
  error 403 "Forbidden";
}

# Block requests without referer (for video content)
if (req.url ~ "\.(mp4|m3u8|ts)$" && !req.http.Referer) {
  error 403 "Forbidden";
}
```

## Advanced Configuration

### Edge-Side Includes (ESI)

Assemble pages at the edge:

```vcl
# Enable ESI in vcl_backend_response
beresp.do_esi = true;
```

### Dynamic Content at the Edge

Use VCL to generate dynamic responses:

```vcl
# Add to vcl_recv
# Example: Country-based redirect
if (req.http.Fastly-Country-Code ~ "^(CN|RU|KP)") {
  error 751 "Blocked region";
}

# Handle the error in vcl_synth
sub vcl_synth {
  if (resp.status == 751) {
    set resp.status = 403;
    set resp.response = "Forbidden";
    synthetic {"Access restricted in your region"};
    return (deliver);
  }
}
```

### Compute@Edge (Advanced)

Run code at the edge with Rust, JavaScript, or other languages:

1. Go to your service → **Compute@Edge**
2. Create a new Compute@Edge service
3. Write code to:
   - Modify requests/responses
   - Make API calls at the edge
   - Generate dynamic content
   - Implement custom authentication

Example use cases:
- Video authentication
- Dynamic token generation
- A/B testing at the edge
- URL rewriting based on user context

## Troubleshooting

### Issue 1: Service Not Activating

**Symptoms**: Service stuck in "Updating" or "Error" state

**Solutions**:
- Check Fastly status page: [https://status.fastly.com](https://status.fastly.com)
- Review VCL syntax errors in the dashboard
- Verify all backends are accessible
- Check DNS configuration for custom domains

```bash
# Validate VCL syntax
curl -H "Fastly-Key: YOUR_TOKEN" -X POST \
  https://api.fastly.com/service/YOUR_SERVICE_ID/version/1/validate
```

### Issue 2: 503 Backend Unavailable

**Symptoms**: `503 Service Unavailable` or `503 Backend Unavailable`

**Solutions**:
1. Check if origin is reachable:
   ```bash
   curl -v https://your-backend-domain.com/health
   ```

2. Verify backend health in Fastly dashboard:
   - Go to your service → **Backends**
   - Check health status

3. Adjust timeout settings:
   - Increase `Max connections`
   - Increase `First byte timeout`
   - Increase `Between origin timeout`

4. Check origin firewall:
   - Ensure Fastly IPs are allowed
   - Verify port 443/80 is open

### Issue 3: Cache Not Working

**Symptoms**: High origin load, `X-Cache: MISS` on all requests

**Solutions**:
1. Check VCL configuration:
   ```vcl
   # Ensure pass is not called for cacheable content
   if (req.url ~ "\.mp4$") {
     return (hash);  # Cache this
   }
   ```

2. Verify cache headers from origin:
   ```bash
   curl -I https://your-backend-domain.com/video1.mp4
   # Look for: Cache-Control: public, max-age=...
   ```

3. Check if cookies/authorization are being forwarded:
   ```vcl
   # Strip cookies for static content
   if (req.url ~ "\.(mp4|ts|m3u8)$") {
     unset req.http.Cookie;
   }
   ```

4. Verify cache object TTL:
   ```vcl
   # Set beresp.ttl in vcl_backend_response
   if (bereq.url ~ "\.mp4$") {
     set beresp.ttl = 86400s;
   }
   ```

### Issue 4: High Latency

**Symptoms**: Slow content delivery despite CDN

**Solutions**:
1. Use geographic testing to identify problem regions
2. Check origin response time:
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s https://your-backend-domain.com/video1.mp4
   ```

3. Enable Origin Shield for large-scale deployments:
   - Routes requests through a centralized shield POP
   - Reduces origin load

4. Review Fastly POP selection:
   - Enable **Debug** header to see which POP served the request
   - Check if requests are routed to optimal POPs

5. Consider using multiple regional backends

### Issue 5: TLS Certificate Errors

**Symptoms**: Certificate validation errors, TLS handshake failures

**Solutions**:
1. Wait for DNS propagation (5-30 minutes)
2. Verify CNAME record is correct:
   ```bash
   dig cdn.yourdomain.com
   # Should point to your-global-enabled-domain.global.fastly.net
   ```

3. Check certificate status in Fastly dashboard:
   - Go to **TLS** → **Certificates**
   - Verify status is "Ready"

4. Ensure domain is configured correctly in the service:
   - Domain name matches CNAME
   - No typos in domain name

### Issue 6: Instant Purge Not Working

**Symptoms**: Cached content not purging immediately

**Solutions**:
1. Verify purge permissions in API token:
   - Token must have "Purge" scope

2. Check URL format:
   ```bash
   # Correct: Full URL
   curl -X PURGE -H "Fastly-Key: YOUR_TOKEN" \
     https://cdn.yourdomain.com/video1.mp4

   # Or use Fastly API
   curl -H "Fastly-Key: YOUR_TOKEN" -X POST \
     https://api.fastly.com/service/YOUR_SERVICE_ID/purge/cdn.yourdomain.com/video1.mp4
   ```

3. Check for purge delays:
   - Fastly purges are instant, but may take 150ms to propagate globally

4. Verify content is actually cached:
   ```bash
   curl -I https://cdn.yourdomain.com/video1.mp4
   # Check: X-Cache: HIT (content is cached)
   ```

## Maintenance

### Regular Tasks

**Daily**:
- Monitor cache hit ratio (target >90%)
- Check error rates (4xx, 5xx)
- Review bandwidth usage

**Weekly**:
- Review Fastly analytics for anomalies
- Analyze geographic performance
- Check backend health

**Monthly**:
- Review and update VCL snippets
- Audit API tokens and rotate if needed
- Review TLS certificates (automatic with Let's Encrypt)
- Analyze cost reports

### Cache Invalidation Strategy

```bash
# Purge specific URLs via backend API
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://cdn.yourdomain.com/playlist.m3u8",
      "https://cdn.yourdomain.com/video1.mp4"
    ]
  }'

# Purge by key (soft purge)
curl -X PURGE -H "Fastly-Key: YOUR_TOKEN" \
  -H "Fastly-Soft-Purge: 1" \
  https://cdn.yourdomain.com/video1.mp4

# Purge entire service (use sparingly!)
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"purge_all": true}'
```

⚠️ **Note**: Fastly purges are instant and unlimited. No extra cost for purging!

## Performance Benchmarks

### Expected Latency Improvements

| Viewer Location | Direct Origin (ms) | Fastly (ms) | Improvement |
|-----------------|-------------------|------------|-------------|
| Same region | 50 | 12 | 76% faster |
| Different continent | 300 | 45 | 85% faster |
| Remote location | 500 | 70 | 86% faster |

### Cache Hit Ratio Targets

| Content Type | Target Cache Hit Ratio |
|--------------|------------------------|
| Static videos (MP4) | >95% |
| HLS segments (.ts) | >92% |
| Playlists (.m3u8) | >85% |
| Thumbnails | >95% |
| API responses | >75% |

### Fastly vs. CloudFront Comparison

| Feature | Fastly | AWS CloudFront |
|---------|--------|----------------|
| **Purge Speed** | <150ms (instant) | 5-15 minutes |
| **Real-time Analytics** | Yes (instant) | No (~1 hour delay) |
| **Edge Computing** | Compute@Edge | Lambda@Edge |
| **POPs** | 80+ | 400+ |
| **Configuration Changes** | Instant | 15-30 minutes |
| **TLS Certificates** | Free (Let's Encrypt) | Free (ACM) |
| **DDoS Protection** | Included | AWS Shield Standard |

## Related Documentation

- [AWS CloudFront Deployment Guide](./aws-cloudfront.md) - Alternative CDN provider
- [Cloudflare Deployment Guide](./cloudflare.md) - Another CDN option
- [Regional Deployment Guide](./regional-deployment.md) - Multi-region setup
- [Backend CDN API](../api/cdn.md) - API reference
- [Architecture Overview](../architecture/DEPLOYMENT_ARCHITECTURE.md) - System architecture

## Support

- **Fastly Documentation**: [https://www.fastly.com/documentation](https://www.fastly.com/documentation)
- **Fastly Support**: [https://www.fastly.com/contact-support](https://www.fastly.com/contact-support)
- **Fastly Community**: [https://community.fastly.com](https://community.fastly.com)
- **Fastly Status**: [https://status.fastly.com](https://status.fastly.com)
- **Fastly Developer Hub**: [https://developer.fastly.com](https://developer.fastly.com)

## Summary

✅ **You now have**:
- Fastly service configured with optimal cache settings
- Application integrated with Fastly CDN
- Cache rules optimized for video streaming
- VCL snippets for advanced caching logic
- TLS/SSL enabled (free with Let's Encrypt)
- Instant purge capability (Fastly superpower!)
- Monitoring and real-time analytics in place
- Security best practices applied

🎯 **Next steps**:
- Test from multiple geographic locations
- Monitor cache hit ratio for first week
- Optimize TTLs based on content update frequency
- Set up billing alerts
- Explore Compute@Edge for advanced features
- Set up origin shield for high-traffic deployments

📊 **Expected results**:
- 76-86% reduction in latency for global viewers
- 92%+ cache hit ratio for static content
- <150ms purge time for content updates
- Real-time analytics (no log delay)
- Reduced origin server load
- Improved viewer experience with instant updates

🚀 **Fastly advantages**:
- **Instant purges** - Update content in real-time
- **Real-time analytics** - No waiting for log processing
- **Edge computing** - Run custom logic at the edge
- **Developer-friendly** - Easy API and VCL configuration
- **Great for dynamic content** - Frequent updates are no problem
