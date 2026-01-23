# Cloudflare CDN Deployment Guide

**Last Updated:** 2026-01-23

This guide explains how to deploy the Telegram Video Streamer with Cloudflare CDN for global content delivery, edge caching of video assets, and optimized viewer experience worldwide.

## Overview

Cloudflare is a content delivery network (CDN) with **330+ data centers** in **100+ countries** across **300+ cities** worldwide. Integrating Cloudflare with your video streaming application provides:

- **Global edge caching** - Video assets cached closer to viewers
- **Reduced latency** - Content served from nearby edge locations
- **Automatic failover** - Built-in anycast network redundancy
- **DDoS protection** - Unmetered DDoS mitigation included
- **HTTPS support** - Free SSL certificates (Universal SSL)
- **Real-time metrics** - Cloudflare Analytics for performance monitoring
- **Edge computing** - Cloudflare Workers for serverless logic at the edge

## Architecture

```
Viewer → Cloudflare Edge → Cloudflare Cache → Origin Server (Your Backend)
                ↓ (cache hit)
           Return cached video
```

### Cloudflare Edge Locations by Region

| Region | Countries | Data Centers |
|--------|-----------|--------------|
| North America | US, Canada | 50+ locations including New York, Los Angeles, Chicago, Toronto, Miami, Dallas |
| Europe | 30+ countries | 80+ locations including London, Amsterdam, Frankfurt, Paris, Madrid, Milan |
| Asia | 20+ countries | 70+ locations including Tokyo, Singapore, Hong Kong, Seoul, Mumbai, Bangkok |
| South America | 10+ countries | 20+ locations including São Paulo, Buenos Aires, Bogotá, Lima, Santiago |
| Oceania | Australia, New Zealand | 15+ locations including Sydney, Melbourne, Auckland, Perth |
| Middle East | 10+ countries | 15+ locations including Dubai, Doha, Riyadh, Manama, Tel Aviv |
| Africa | 15+ countries | 25+ locations including Johannesburg, Cape Town, Cairo, Lagos, Nairobi |

## Prerequisites

### Cloudflare Account Requirements

- **Cloudflare Account** (free tier available)
- **Domain** added to Cloudflare DNS
- **API Token** with appropriate permissions
- **Zone ID** of your domain

### API Token Permissions

Your Cloudflare API Token needs these permissions:

1. Go to **Cloudflare Dashboard** → **My Profile** → **API Tokens**
2. Click **Create Token**
3. Use template **Custom token** or **Edit Cloudflare Workers**

Required permissions:

```yaml
# Zone - Zone
Zone - Zone - Read
Zone - DNS - Read
Zone - Cache Tags - Edit

# Account - Account Settings (optional, for advanced features)
Account - Account Settings - Read

# Zone - Page Rules (for cache configuration)
Zone - Page Rules - Edit
```

**Zone Resources**: Include → **Specific zone** → **Select your domain**

### Application Requirements

- Backend service with CDN integration code (already implemented in `backend/src/infrastructure/external/cloudflare_client.py`)
- Environment variables configured for Cloudflare credentials
- Existing video streaming infrastructure

## Step 1: Create Cloudflare Account and Add Domain

### 1.1 Create Cloudflare Account

1. Go to [Cloudflare Signup](https://dash.cloudflare.com/sign-up)
2. Enter your email address and create a password
3. Verify your email address

### 1.2 Add Your Domain

1. Click **Add a Site**
2. Enter your domain name (e.g., `yourdomain.com`)
3. Select the **Free plan** (sufficient for most use cases) or upgrade to **Pro** for additional features
4. Click **Continue**

### 1.3 Update Nameservers

Cloudflare will provide two nameservers:

```
Example:
  alice.ns.cloudflare.com
  bob.ns.cloudflare.com
```

Update your domain's nameservers at your registrar:
1. Log in to your domain registrar (GoDaddy, Namecheap, etc.)
2. Replace existing nameservers with Cloudflare nameservers
3. Save changes

⚠️ **NOTE**: Nameserver changes can take 2-48 hours to propagate globally.

### 1.4 Verify Domain Activation

Wait for Cloudflare to detect the nameserver change:
- Status changes from **Pending** to **Active**
- Usually takes 15-30 minutes, but can take up to 24 hours

## Step 2: Configure Cloudflare DNS and SSL

### 2.1 Configure DNS Records

Add DNS records for your application:

1. Go to **DNS** → **Records**
2. Add records:

```
Type: A
Name: @ (or your subdomain like 'stream')
IPv4 address: YOUR_SERVER_IP
Proxy status: Proxied (orange cloud) ✓
TTL: Auto
```

```
Type: CNAME
Name: cdn (optional, for dedicated CDN subdomain)
Target: yourdomain.com
Proxy status: Proxied (orange cloud) ✓
TTL: Auto
```

**Important**: Ensure **Proxy status** is **Proxied** (orange cloud icon) to enable CDN.

### 2.2 Configure SSL/TLS

1. Go to **SSL/TLS** → **Overview**
2. Select encryption mode:

   - **Flexible SSL** (if your origin doesn't have SSL):
     - Cloudflare → Visitor: HTTPS ✓
     - Cloudflare → Origin: HTTP

   - **Full SSL** (if your origin has self-signed cert):
     - Cloudflare → Visitor: HTTPS ✓
     - Cloudflare → Origin: HTTPS (no cert validation)

   - **Full (strict) SSL** (recommended):
     - Cloudflare → Visitor: HTTPS ✓
     - Cloudflare → Origin: HTTPS (valid cert required)

3. Enable **Always Use HTTPS**:
   - Go to **SSL/TLS** → **Edge Certificates**
   - Toggle **Always Use HTTPS** to **On**

4. Enable **Automatic HTTPS Rewrites**:
   - Toggle **Automatic HTTPS Rewrites** to **On**

### 2.3 Verify SSL Certificate

For Free plan, Cloudflare automatically issues a Universal SSL certificate:
- Certificate is issued automatically (can take 15 minutes)
- No validation required
- Supports `yourdomain.com` and `*.yourdomain.com`

## Step 3: Create API Token

### 3.1 Generate API Token

1. Go to **Cloudflare Dashboard** → **My Profile** → **API Tokens**
2. Click **Create Token**
3. Click **Create Custom Token**
4. Configure permissions:

```
Permissions:
  Zone - Zone - Read
  Zone - DNS - Read
  Zone - Cache Tags - Edit
  Zone - Page Rules - Edit

Zone Resources:
  Include - Specific zone
  - Select: yourdomain.com

Client IP Address Filtering (optional):
  Add your server IP for additional security

TTL:
  Leave blank (or set expiration date)
```

5. Click **Continue to summary** → **Create Token**
6. **Copy the token** - you won't see it again!

⚠️ **IMPORTANT**: Save your API token securely - it grants access to your Cloudflare account.

### 3.2 Get Your Zone ID

1. Go to **Cloudflare Dashboard** → **Select your domain**
2. On the right sidebar, find **Zone ID**
3. Copy the Zone ID (e.g., `abc123def456789`)

## Step 4: Configure Application

### 4.1 Set Environment Variables

Add to your `.env` file:

```env
# Enable CDN
CDN_ENABLED=true
CDN_PROVIDER=cloudflare

# Cloudflare Configuration
CLOUDFLARE_API_TOKEN=your_api_token_here
CLOUDFLARE_ZONE_ID=abc123def456789
CLOUDFLARE_ACCOUNT_ID=optional_account_id
```

### 4.2 Docker Compose / Systemd Service

If using Docker Compose, add to your compose file:

```yaml
services:
  backend:
    environment:
      - CDN_ENABLED=true
      - CDN_PROVIDER=cloudflare
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - CLOUDFLARE_ZONE_ID=${CLOUDFLARE_ZONE_ID}
```

If using systemd, add to your service file:

```ini
[Service]
Environment="CDN_ENABLED=true"
Environment="CDN_PROVIDER=cloudflare"
Environment="CLOUDFLARE_API_TOKEN=your_api_token_here"
Environment="CLOUDFLARE_ZONE_ID=abc123def456789"
```

### 4.3 Configure CNAME for CDN (Optional)

If using a dedicated CDN subdomain:

1. Go to **DNS** → **Records**
2. Add CNAME record:

```
Type: CNAME
Name: cdn
Target: yourdomain.com
Proxy status: Proxied (orange cloud) ✓
```

3. Wait for DNS propagation (5-30 minutes)

## Step 5: Configure Cache Behaviors

### 5.1 Cache Behavior for Video Files

Optimize cache settings for video content:

| File Type | Pattern | Browser TTL | Edge TTL | Cache Level |
|-----------|---------|-------------|----------|-------------|
| MP4 Video | `*.mp4` | 1 hour | 24 hours | Cache Everything |
| HLS Segments | `*.ts` | 5 min | 1 hour | Cache Everything |
| Playlists | `*.m3u8` | 1 min | 5 min | Standard |
| Thumbnails | `*.jpg`, `*.png` | 4 hours | 7 days | Cache Everything |
| JSON Metadata | `*.json` | 5 min | 5 min | Standard |

### 5.2 Configure via Cloudflare Dashboard

**Option A: Using Cache Rules (Recommended)**

1. Go to **Cache** → **Configuration**
2. Set **Browser Cache TTL** to **Respect Existing Headers**
3. Set **Caching Level** to **Standard**

**Option B: Using Page Rules**

1. Go to **Rules** → **Page Rules**
2. Create page rule for each file type:

**For MP4 files**:
```
URL pattern: *yourdomain.com/*.mp4

Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 24 hours
  - Browser Cache TTL: 1 hour
```

**For HLS segments**:
```
URL pattern: *yourdomain.com/*.ts

Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 hour
  - Browser Cache TTL: 5 minutes
```

### 5.3 Configure via Backend API

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

## Step 6: Test Deployment

### 6.1 Verify Cloudflare Proxy Status

```bash
# Check if domain is proxied by Cloudflare
curl -I https://yourdomain.com/video1.mp4

# Look for Cloudflare headers:
# CF-Cache-Status: HIT (cache hit)
# CF-Cache-Status: MISS (cache miss)
# CF-Ray: 1234567890abcde-ORD (edge location: ORD = Chicago)
# CF-IPCountry: US
```

### 6.2 Test CDN Backend Integration

```bash
# Test connection from backend
curl -X GET http://localhost:8000/api/v1/cdn/status

# Expected response:
{
  "provider": "cloudflare",
  "status": "healthy",
  "zone_id": "abc123def456789",
  "domain": "yourdomain.com",
  "edge_locations": 330
}
```

### 6.3 Test Cache Purging

```bash
# Purge specific URLs
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://yourdomain.com/video1.mp4"
    ]
  }'

# Purge all cache
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "purge_all": true
  }'
```

### 6.4 Test Edge Access

```bash
# Access content via Cloudflare
curl -I https://yourdomain.com/video1.mp4

# Check response headers:
# CF-Cache-Status: HIT (cache hit)
# CF-Cache-Status: MISS (cache miss)
# CF-Ray: 1234567890abcde-ORD (edge location)
```

### 6.5 Test Geographic Distribution

Use tools to verify content is served from edge locations:

```bash
# From different regions
curl -I https://yourdomain.com/video1.mp4

# Check CF-Ray header:
# CF-Ray: 1234567890abcde-ORD (Chicago, USA)
# CF-Ray: 1234567890abcde-LHR (London, UK)
# CF-Ray: 1234567890abcde-NRT (Tokyo, Japan)
```

Common edge location codes:
- `ORD`: Chicago, USA
- `LHR`: London, UK
- `FRA`: Frankfurt, Germany
- `NRT`: Tokyo, Japan
- `SYD`: Sydney, Australia
- `SIN`: Singapore

## Step 7: Monitor Performance

### 7.1 Cloudflare Analytics

Access Cloudflare Analytics in the dashboard:

1. Go to **Analytics & Logs** → **Traffic**
2. View metrics:
   - Total requests
   - Cached vs uncached requests
   - Bandwidth usage
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
  "cache_hit_ratio": 0.92,
  "average_response_time_ms": 45.2,
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
- Cache hit ratio charts
- Geographic distribution map
- Bandwidth usage graphs
- Error rate monitoring

### 7.4 Cloudflare Logs

Enable logging for detailed analytics:

1. Go to **Analytics & Logs** → **Log Storage**
2. Enable **Log Storage** (requires Enterprise plan or Cloudflare Logpush)
3. Configure log retention period
4. Set up Logpush to export logs to your storage (S3, GCS, Azure)

## Step 8: Cost Optimization

### 8.1 Cloudflare Pricing (2026)

| Plan | Monthly Cost | Features |
|------|-------------|----------|
| Free | $0 | Basic CDN, DDoS protection, Universal SSL |
| Pro | $20 | Additional WAF, Image optimization, Mobile optimization |
| Business | $200 | Image resizing, SSL custom, 20 Page Rules |
| Enterprise | Custom | Advanced WAF, PCI DSS, dedicated support |

### 8.2 Cost Saving Strategies

1. **Use Free Plan**:
   - Sufficient for most video streaming use cases
   - Unlimited bandwidth for proxied traffic
   - Basic DDoS protection included

2. **Optimize Cache Hit Ratio**:
   - Higher cache hit ratio = fewer origin requests = lower costs
   - Set appropriate Edge Cache TTL values
   - Use cache rules for static content

3. **Enable Compression**:
   - Enable **Auto Minify** for CSS, JS, HTML
   - Reduces bandwidth usage
   - Faster content delivery

4. **Use Brotli Compression**:
   - Go to **Network** → **Optimization**
   - Enable **Brotli** compression

5. **Optimize Images**:
   - Enable **Polish** (Image optimization) on Pro plan
   - Use **Mirage** for mobile image optimization

### 8.3 Bandwidth Monitoring

Monitor your usage to avoid unexpected costs:

```bash
# Cloudflare free plan includes unmetered bandwidth
# However, monitor origin server bandwidth usage

# Check origin bandwidth
curl -X GET http://localhost:8000/api/v1/cdn/metrics?start_date=2026-01-01&end_date=2026-01-31
```

## Step 9: Security Best Practices

### 9.1 Enable All Security Features

1. Go to **Security** → **Settings**
2. Enable features:
   - **Security Level**: Medium or High
   - **Bot Fight Mode** (free): Block malicious bots
   - **Challenge Passage**: 30 minutes

### 9.2 Configure Firewall Rules

1. Go to **Security** → **WAF**
2. Create firewall rules:

```
Rule 1: Block known malicious IPs
Expression: (ip.geoip.never_threat_list eq true)
Action: Block

Rule 2: Rate limiting for video endpoints
Expression: (http.request.uri.path matches "*/video*")
Action: Rate limit - 100 requests per minute
```

### 9.3 Use API Token Restrictions

1. Go to **API Tokens** → **Edit Token**
2. Add **Client IP Address Filtering**:
   - Only allow requests from your server IP
3. Set **TTL** to limit token lifespan

### 9.4 Enable Cloudflare SSL/TLS Best Practices

1. Set **Minimum TLS Version** to **TLS 1.2** or higher:
   - Go to **SSL/TLS** → **Edge Certificates**
   - Set **Minimum TLS Version**: TLS 1.2

2. Enable ** Opportunistic Encryption**:
   - Go to **Network** → **Opportunistic Encryption**
   - Enable **HTTP/2** and **HTTP/3 (with QUIC)**

### 9.5 Hide Origin Server

1. Go to **Network** → **Origin Security**
2. Enable **Hide Origin Server**:
   - Prevents exposing your origin server IP
   - All traffic goes through Cloudflare

### 9.6 Use Page Rules for Access Control

Create page rules for premium content:

```
URL pattern: *yourdomain.com/premium/*

Settings:
  - Cache Level: Bypass (for dynamic content)
  - Security Level: High
  - Browser Integrity Check: On
```

### 9.7 Enable Argo Smart Routing (Optional)

For additional performance improvement:
- Go to **Traffic** → **Argo Smart Routing**
- Enable **Argo** (additional $5/month)
- Routes traffic through Cloudflare's optimized global network

## Troubleshooting

### Issue 1: Content Not Caching

**Symptoms**: `CF-Cache-Status: MISS` on all requests

**Solutions**:
1. Check cache level:
   - Go to **Cache** → **Configuration**
   - Set **Caching Level** to **Standard** or **Cache Everything**

2. Verify response headers from origin:
   ```bash
   curl -I https://your-origin.com/video1.mp4

   # Check for:
   # Cache-Control: max-age=... (should be set)
   # Expires: ... (optional)
   # Vary: ... (can prevent caching if varies by headers)
   ```

3. Check Page Rules order:
   - Page rules are processed top-to-bottom
   - More specific rules should be higher

4. Disable features that bypass cache:
   - **Browser Integrity Check**: Can prevent caching
   - **Security Level**: Set to Medium or Low for static content

### Issue 2: High Origin Load

**Symptoms**: Origin server receiving too many requests

**Solutions**:
1. Increase Edge Cache TTL:
   - Go to **Cache** → **Configuration**
   - Set **Browser Cache TTL** appropriately

2. Create Page Rules for static content:
   ```
   URL pattern: *yourdomain.com/*.mp4
   Settings:
     - Cache Level: Cache Everything
     - Edge Cache TTL: 7 days
   ```

3. Check cache hit ratio:
   - Go to **Analytics** → **Caching**
   - Target: >90% cache hit ratio

### Issue 3: SSL Certificate Errors

**Symptoms**: Browser SSL warnings, certificate errors

**Solutions**:
1. Verify SSL/TLS mode:
   - Go to **SSL/TLS** → **Overview**
   - For origins with valid SSL: **Full (strict)**
   - For origins without SSL: **Flexible**

2. Check origin certificate:
   ```bash
   # Test origin SSL
   openssl s_client -connect your-origin.com:443 -servername your-origin.com
   ```

3. Wait for certificate propagation:
   - Universal SSL certificates can take 15 minutes to issue

4. Clear Cloudflare cache:
   - Go to **Caching** → **Configuration**
   - Click **Purge Everything**

### Issue 4: High Latency

**Symptoms**: Slow content delivery despite CDN

**Solutions**:
1. Enable Argo Smart Routing:
   - Go to **Traffic** → **Argo Smart Routing**
   - Enable for optimized routing

2. Check origin response time:
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s https://your-origin.com/video1.mp4
   ```

3. Enable HTTP/3 (QUIC):
   - Go to **Network** → **Optimization**
   - Enable **HTTP/3**

4. Enable compression:
   - Go to **Network** → **Content Optimization**
   - Enable **Auto Minify** for JS, CSS, HTML

5. Test from different locations:
   - Use tools like WebPageTest, GTmetrix
   - Compare performance with and without Cloudflare

### Issue 5: API Authentication Errors

**Symptoms**: `401 Unauthorized`, `403 Forbidden` from API calls

**Solutions**:
1. Verify API token:
   - Go to **API Tokens**
   - Check token is not expired
   - Verify token has correct permissions

2. Check Zone ID:
   - Go to **Dashboard** → **Your Domain**
   - Copy correct Zone ID

3. Check IP restrictions:
   - If token has IP filtering, ensure requests come from allowed IP

4. Test token manually:
   ```bash
   curl -X GET "https://api.cloudflare.com/client/v4/zones/YOUR_ZONE_ID" \
     -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json"
   ```

### Issue 6: Cache Not Invalidating

**Symptoms**: Old content served after purge

**Solutions**:
1. Wait for propagation:
   - Cache purge can take up to 30 seconds globally

2. Verify purge success:
   ```bash
   # Check purge response
   curl -X POST http://localhost:8000/api/v1/cdn/purge \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"urls": ["https://yourdomain.com/video1.mp4"]}'

   # Should return: {"success": true}
   ```

3. Check if URL is correct:
   - Ensure URL matches exactly (including protocol)
   - Check for query parameters

4. Clear all cache:
   - Go to **Caching** → **Configuration**
   - Click **Purge Everything** (use sparingly)

### Issue 7: DDoS Attacks

**Symptoms**: Massive traffic spikes, service degradation

**Solutions**:
1. Enable **Under Attack Mode**:
   - Go to **Security** → **Settings**
   - Toggle **Under Attack Mode** (adds CAPTCHA challenge)

2. Check Security Level:
   - Set to **High** during attack
   - Set to **Medium** normally

3. Enable **Rate Limiting**:
   - Go to **Security** → **WAF** → **Rate Limiting Rules**
   - Create rate limit rules for sensitive endpoints

4. Monitor Analytics:
   - Go to **Security** → **Overview**
   - Check for attack patterns

## Advanced Configuration

### Cloudflare Workers for Edge Logic

Run code at edge locations for custom logic:

```javascript
// Worker: Add security headers
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const response = await fetch(request)

  // Add security headers
  const newResponse = new Response(response.body, response)
  newResponse.headers.set('Strict-Transport-Security', 'max-age=63072000; includeSubdomains; preload')
  newResponse.headers.set('X-Content-Type-Options', 'nosniff')
  newResponse.headers.set('X-Frame-Options', 'DENY')

  return newResponse
}
```

Deploy Worker:
1. Go to **Workers** → **Create Worker**
2. Paste code
3. Deploy
4. Add route: `*yourdomain.com/*`

### Cloudflare Images (Optional)

Optimize image delivery:
1. Go to **Images**
2. Enable **Image Resizing**
3. Use in URLs:
   ```
   https://yourdomain.com/cdn-cgi/image/width=800,quality=80/thumbnail.jpg
   ```

### Cloudflare Stream (Optional)

For specialized video streaming:
1. Go to **Stream**
2. Upload videos directly to Cloudflare
3. Cloudflare handles transcoding, delivery, DRM

## Maintenance

### Regular Tasks

**Daily**:
- Monitor cache hit ratio (target >90%)
- Check error rates (4xx, 5xx)
- Review security events

**Weekly**:
- Review Cloudflare Analytics
- Analyze geographic performance
- Check firewall rules logs

**Monthly**:
- Review and update cache rules
- Audit API tokens (rotate if needed)
- Update SSL/TLS configuration
- Review Page Rules

### Cache Invalidation Strategy

```bash
# Invalidate specific files
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://yourdomain.com/playlist.m3u8",
      "https://yourdomain.com/video1.mp4"
    ]
  }'

# Invalidate by wildcard (via API only)
# Cloudflare API supports wildcard purging

# Purge entire zone cache
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"purge_all": true}'
```

⚠️ **Note**: Cache purging is unlimited on Free plan. On paid plans, check limits.

### Performance Benchmarks

### Expected Latency Improvements

| Viewer Location | Direct Origin (ms) | Cloudflare (ms) | Improvement |
|-----------------|-------------------|-----------------|-------------|
| Same region | 50 | 20 | 60% faster |
| Different continent | 300 | 60 | 80% faster |
| Remote location | 500 | 100 | 80% faster |

### Cache Hit Ratio Targets

| Content Type | Target Cache Hit Ratio |
|--------------|------------------------|
| Static videos (MP4) | >95% |
| HLS segments (.ts) | >90% |
| Playlists (.m3u8) | >80% |
| Thumbnails | >95% |
| API responses | >70% |

## Related Documentation

- [AWS CloudFront Deployment Guide](./aws-cloudfront.md) - Alternative CDN provider
- [Fastly Deployment Guide](./fastly.md) - Another CDN option
- [Regional Deployment Guide](./regional-deployment.md) - Multi-region setup
- [Backend CDN API](../api/cdn.md) - API reference
- [Architecture Overview](../architecture/DEPLOYMENT_ARCHITECTURE.md) - System architecture

## Support

- **Cloudflare Documentation**: https://developers.cloudflare.com/
- **Cloudflare Community**: https://community.cloudflare.com/
- **Cloudflare Support**: https://support.cloudflare.com/
- **Cloudflare Status**: https://www.cloudflarestatus.com/

## Summary

✅ **You now have**:
- Cloudflare CDN configured for your domain
- Application integrated with Cloudflare CDN
- Cache rules optimized for video streaming
- Monitoring and metrics in place
- Security best practices applied

🎯 **Next steps**:
- Test from multiple geographic locations
- Monitor cache hit ratio for first week
- Optimize TTLs based on content update frequency
- Set up Cloudflare Analytics dashboards
- Consider Cloudflare Workers for advanced edge logic
- Explore Argo Smart Routing for additional performance

📊 **Expected results**:
- 60-80% reduction in latency for global viewers
- 90%+ cache hit ratio for static content
- Reduced origin server load
- Improved viewer experience
- Automatic DDoS protection
- Free SSL certificates

🚀 **Cloudflare advantages**:
- Easy setup (DNS change only)
- Free tier with unlimited bandwidth
- Global anycast network (330+ PoPs)
- Automatic DDoS mitigation
- Free SSL certificates
- Edge computing with Workers
- Developer-friendly API
