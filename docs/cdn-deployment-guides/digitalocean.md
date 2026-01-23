# DigitalOcean CDN Deployment Guide

**Last Updated:** 2026-01-23

This guide explains how to deploy the Telegram Video Streamer with DigitalOcean Spaces CDN for global content delivery, edge caching of video assets, and optimized viewer experience worldwide.

## Overview

DigitalOcean Spaces is an object storage service with built-in CDN integration, powered by a **global network of edge locations** worldwide. Integrating DigitalOcean Spaces CDN with your video streaming application provides:

- **Global edge caching** - Video assets cached closer to viewers
- **Reduced latency** - Content served from nearby edge locations
- **Simple pricing** - Flat rate across all regions
- **S3-compatible API** - Easy migration from AWS S3
- **Built-in CDN** - One-click CDN enablement
- **Free SSL certificates** - Automatic HTTPS support
- **Developer-friendly** - Simple setup and management

## Architecture

```
Viewer → DigitalOcean Edge Location → Spaces Origin (CDN enabled) → Backend
                ↓ (cache hit)
           Return cached video
```

### DigitalOcean Edge Locations by Region

| Region | Cities | Edge Locations |
|--------|--------|----------------|
| North America | 8+ | New York, San Francisco, Toronto, Chicago, Atlanta, Dallas, Los Angeles, Miami |
| Europe | 6+ | Amsterdam, Frankfurt, London, Paris, Stockholm, Brussels |
| Asia | 5+ | Singapore, Bangalore, Tokyo, Seoul, Hong Kong |
| Oceania | 2+ | Sydney, Melbourne |
| South America | 2+ | São Paulo, Buenos Aires |

## Prerequisites

### DigitalOcean Account Requirements

- **DigitalOcean Account** with billing enabled
- **Personal Access Token** (API token) with appropriate permissions
- **Spaces bucket** (for video asset storage)
- **Custom domain** (optional, for CDN CNAME)

### API Token Permissions

Your DigitalOcean API token needs these permissions:

- **Spaces**: Full access (read/write)
- **CDN**: Full access (enable/disable, purge cache)
- **DNS**: Write access (if using custom domain)

Create token at: https://cloud.digitalocean.com/account/api/tokens

### Application Requirements

- Backend service with CDN integration code (already implemented in `backend/src/infrastructure/external/spaces_client.py`)
- Environment variables configured for DigitalOcean credentials
- Existing video streaming infrastructure

## Step 1: Create DigitalOcean API Token

### 1.1 Generate Personal Access Token

1. Go to **DigitalOcean Control Panel** → **API** → **Tokens/Keys**
2. Click **Generate New Token**
3. Token name: `tg-video-streamer-cdn`
4. Scopes: Select **Write** (or **Read/Write** for full access)
5. Expiration: Set expiration or leave blank for no expiration
6. Click **Generate Token**

### 1.2 Save Token

⚠️ **IMPORTANT**: Copy the token immediately - you won't be able to see it again!

Example token format:
```
dop_v1_your_actual_token_here_replace_with_real_token
```

Store securely in your environment variables or secrets manager.

## Step 2: Create Spaces Bucket

### 2.1 Create Spaces Bucket via Console

1. Go to **Spaces** → **Create Spaces Bucket**
2. **Choose a region**:
   - Select region closest to your viewers or origin server
   - For global audience, choose **New York (nyc3)** or **Amsterdam (ams3)** for best connectivity
3. **Choose a unique name**: `tg-video-streamer-assets-<unique-id>`
4. **Select a project**: Assign to your project
5. Click **Create Spaces Bucket**

### 2.2 Enable CDN

1. Go to your newly created Space
2. Click the **Settings** tab
3. Find **CDN** section
4. Click **Enable CDN**
5. Note your **CDN endpoint**: `https://<space-name>.<region>.cdn.digitaloceanspaces.com`

Example:
```
https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com
```

### 2.3 Create Spaces Bucket via API

```bash
# Install doctl (DigitalOcean CLI)
# Linux
curl -sL https://github.com/digitalocean/doctl/releases/download/v1.100.0/doctl-1.100.0-linux-amd64.tar.gz | tar xz
sudo mv doctl /usr/local/bin

# macOS
brew install doctl

# Windows
choco install doctl

# Authenticate
doctl auth init
# Enter your Personal Access Token

# Create Space
doctl spaces create tg-video-streamer-assets --region nyc3

# Enable CDN
doctl spaces cdn enable tg-video-streamer-assets --region nyc3
```

### 2.4 Note Your CDN Details

After enabling CDN, note:
- **Space Name**: `tg-video-streamer-assets`
- **Region**: `nyc3`
- **CDN Endpoint**: `https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com`
- **Origin Endpoint**: `https://tg-video-streamer-assets.nyc3.digitaloceanspaces.com`

## Step 3: Configure Custom Domain (Optional)

### 3.1 Add CNAME Record

If using custom domain for CDN:

1. Go to your DNS provider (or DigitalOcean DNS)
2. Add CNAME record:

```
Type: CNAME
Name: cdn
Value: tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com
TTL: 300
```

3. Wait for DNS propagation (5-30 minutes)

### 3.2 Verify Custom Domain

```bash
# Verify DNS resolution
dig cdn.yourdomain.com

# Should resolve to DigitalOcean CDN IP
```

### 3.3 Free SSL Certificate

DigitalOcean automatically provisions SSL certificates for custom domains:

1. Go to **Spaces** → Your Space → **Settings** → **CDN**
2. Add custom domain: `cdn.yourdomain.com`
3. DigitalOcean automatically provisions Let's Encrypt certificate
4. Wait for certificate status: **Certificate Status: Active**

⚠️ **Note**: SSL certificate provisioning can take 10-30 minutes.

## Step 4: Configure Application

### 4.1 Set Environment Variables

Add to your `.env` file:

```env
# Enable CDN
CDN_ENABLED=true
CDN_PROVIDER=digitalocean

# DigitalOcean Spaces Configuration
SPACES_ACCESS_KEY_ID=DO_ACCESS_KEY_123456
SPACES_SECRET_ACCESS_KEY=SECRET_KEY_HERE
SPACES_REGION=nyc3
SPACES_BUCKET_NAME=tg-video-streamer-assets
SPACES_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com

# CDN Configuration
CDN_ENDPOINT_URL=https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com
CDN_CUSTOM_DOMAIN=cdn.yourdomain.com  # Optional
```

### 4.2 Get Spaces Access Keys

1. Go to **API** → **Tokens/Keys** in DigitalOcean Control Panel
2. Scroll to **Spaces Access Keys**
3. Click **Generate New Key**
4. Note your **Access Key** and **Secret Key**
5. Save these securely

### 4.3 Docker Compose / Systemd Service

If using Docker Compose:

```yaml
services:
  backend:
    environment:
      - CDN_ENABLED=true
      - CDN_PROVIDER=digitalocean
      - SPACES_ACCESS_KEY_ID=${SPACES_ACCESS_KEY_ID}
      - SPACES_SECRET_ACCESS_KEY=${SPACES_SECRET_ACCESS_KEY}
      - SPACES_REGION=nyc3
      - SPACES_BUCKET_NAME=tg-video-streamer-assets
      - SPACES_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
      - CDN_ENDPOINT_URL=${CDN_ENDPOINT_URL}
```

If using systemd:

```ini
[Service]
Environment="CDN_ENABLED=true"
Environment="CDN_PROVIDER=digitalocean"
Environment="SPACES_ACCESS_KEY_ID=DO_ACCESS_KEY_123456"
Environment="SPACES_SECRET_ACCESS_KEY=SECRET_KEY_HERE"
Environment="SPACES_REGION=nyc3"
Environment="SPACES_BUCKET_NAME=tg-video-streamer-assets"
Environment="SPACES_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com"
Environment="CDN_ENDPOINT_URL=https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com"
```

## Step 5: Configure Cache Behaviors

### 5.1 Cache Behavior for Video Files

DigitalOcean Spaces CDN automatically caches content based on HTTP headers. Optimize cache settings for video content:

| File Type | Pattern | TTL | Compress |
|-----------|---------|-----|----------|
| MP4 Video | `*.mp4` | 86400s (24h) | No |
| HLS Segments | `*.ts` | 3600s (1h) | No |
| Playlists | `*.m3u8` | 300s (5min) | Yes |
| Thumbnails | `*.jpg`, `*.png` | 604800s (7d) | Yes |
| JSON Metadata | `*.json` | 300s (5min) | Yes |

### 5.2 Set Cache-Control Headers

When uploading files, set appropriate `Cache-Control` headers:

```bash
# Using s3cmd (S3-compatible tool)
s3cmd put video1.mp4 s3://tg-video-streamer-assets/videos/ \
  --add-header="Cache-Control: public, max-age=86400"

# Using AWS CLI (S3-compatible)
aws s3 cp video1.mp4 s3://tg-video-streamer-assets/videos/ \
  --endpoint-url=https://nyc3.digitaloceanspaces.com \
  --cache-control "public, max-age=86400"

# Using Python (boto3)
import boto3

s3 = boto3.client('s3',
    endpoint_url='https://nyc3.digitaloceanspaces.com',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY'
)

s3.upload_file(
    'video1.mp4',
    'tg-video-streamer-assets',
    'videos/video1.mp4',
    ExtraArgs={'CacheControl': 'public, max-age=86400'}
)
```

### 5.3 Configure via Backend API

The application supports dynamic cache rule configuration:

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

### 6.1 Verify CDN Status

```bash
# Using doctl
doctl spaces cdn list tg-video-streamer-assets --region nyc3

# Check CDN is enabled and endpoint is active
```

### 6.2 Test CDN Backend Integration

```bash
# Test connection from backend
curl -X GET http://localhost:8000/api/v1/cdn/status

# Expected response:
{
  "provider": "digitalocean",
  "status": "healthy",
  "spaces": [
    {
      "name": "tg-video-streamer-assets",
      "region": "nyc3",
      "cdn_enabled": true,
      "cdn_endpoint": "https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com",
      "custom_domain": "cdn.yourdomain.com"
    }
  ],
  "edge_locations": 23
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
      "https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com/video1.mp4"
    ]
  }'

# Purge all cache (entire Space)
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "purge_all": true
  }'
```

### 6.4 Test Edge Access

```bash
# Access content via CDN endpoint
curl -I https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com/video1.mp4

# Check response headers for cache status:
# X-Cache: HIT (from cloudfront) (cache hit)
# X-Cache: MISS (from cloudfront) (cache miss)
# Age: 12345 (indicates cached content age)
```

### 6.5 Upload Test File

```bash
# Upload test file
echo "Test video content" > test.mp4
aws s3 cp test.mp4 s3://tg-video-streamer-assets/test.mp4 \
  --endpoint-url=https://nyc3.digitaloceanspaces.com \
  --cache-control "public, max-age=86400"

# Access via CDN
curl -I https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com/test.mp4
```

## Step 7: Monitor Performance

### 7.1 DigitalOcean Metrics

DigitalOcean provides built-in metrics:

1. Go to **Spaces** → Your Space → **Metrics**
2. View metrics:
   - **Bandwidth usage** (GB in/out)
   - **Request count** (GET, PUT, DELETE)
   - **CDN bandwidth** (CDN served vs origin served)
   - **Storage usage**

### 7.2 Application Metrics

The backend collects CDN metrics accessible via API:

```bash
# Get CDN usage metrics
curl -X GET "http://localhost:8000/api/v1/cdn/metrics?start_date=2026-01-20&end_date=2026-01-23" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Expected response:
{
  "total_bandwidth_gb": 850.5,
  "total_requests": 32000,
  "cache_hit_ratio": 0.89,
  "average_response_time_ms": 52.3,
  "by_region": {
    "North America": {"requests": 15000, "bandwidth_gb": 400.2},
    "Europe": {"requests": 10000, "bandwidth_gb": 280.1},
    "Asia": {"requests": 5000, "bandwidth_gb": 140.5},
    "South America": {"requests": 1500, "bandwidth_gb": 25.3},
    "Oceania": {"requests": 500, "bandwidth_gb": 4.4}
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
- Storage usage tracking
- CDN bandwidth vs origin bandwidth

## Step 8: Cost Optimization

### 8.1 DigitalOcean Spaces Pricing (2026)

**Storage**:
- $0.023 per GB/month

**Bandwidth**:
- **First 1 TB**: Free
- **Beyond 1 TB**: $0.01 per GB (egress)

**CDN**:
- **First 1 TB**: Free
- **Beyond 1 TB**: $0.005 per GB (CDN egress)

**Requests**:
- **Class A (PUT, POST, DELETE)**: $0.005 per 1,000 requests
- **Class B (GET, LIST)**: $0.0004 per 1,000 requests

### 8.2 Cost Comparison with AWS CloudFront

| Service | DigitalOcean | AWS CloudFront | Savings |
|---------|--------------|----------------|---------|
| Storage | $0.023/GB | $0.023/GB | Same |
| CDN Bandwidth | $0.005/GB* | $0.085-0.17/GB | **94-97%** |
| Requests (GET) | $0.0004/1K | $0.0075/10K | **47%** |

*After free tier (1 TB/month)

**Example Monthly Cost for 10 TB CDN bandwidth**:
- DigitalOcean: $45 (9 TB × $0.005)
- AWS CloudFront: $850 (9 TB × $0.085, US/Europe)
- **Savings: $805/month (95%)**

### 8.3 Cost Saving Strategies

1. **Optimize Cache TTLs**:
   - Longer TTL = fewer origin requests = lower costs
   - Set `Cache-Control: public, max-age=86400` (24 hours) or higher

2. **Use Free Tier**:
   - First 1 TB/month CDN bandwidth is free
   - First 1 TB/month standard egress is free

3. **Compress Content**:
   - Enable compression for text-based files (JSON, playlists)
   - Reduces bandwidth usage

4. **Optimize File Sizes**:
   - Use appropriate video encoding settings
   - Consider multiple quality levels (adaptive streaming)

5. **Monitor Usage**:
   - Set up bandwidth alerts
   - Review cost reports regularly

### 8.4 Cost Monitoring

Set up monitoring alerts:

```bash
# Check current usage
doctl projects resources-list --format Name,URN

# Monitor storage usage
aws s3 ls s3://tg-video-streamer-assets --recursive --summarize \
  --endpoint-url=https://nyc3.digitaloceanspaces.com

# Expected output:
# Total Objects: 1500
# Total Size: 5234567890 bytes (4.87 GB)
```

## Step 9: Security Best Practices

### 9.1 Use Spaces Access Keys

Create dedicated access keys for the application:

1. Go to **API** → **Spaces Access Keys**
2. Click **Generate New Key**
3. Name: `tg-video-streamer-prod`
4. Save **Access Key** and **Secret Key**
5. Restrict key to specific Space if possible

### 9.2 Set Bucket Policies

Restrict access to your Space:

```bash
# Create bucket policy
cat > bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadForVideoBucket",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::tg-video-streamer-assets/*"
    }
  ]
}
EOF

# Apply policy
aws s3api put-bucket-policy \
  --bucket tg-video-streamer-assets \
  --policy file://bucket-policy.json \
  --endpoint-url=https://nyc3.digitaloceanspaces.com
```

### 9.3 Enable CORS

Configure CORS for web access:

```bash
# Create CORS configuration
cat > cors-config.json <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://yourdomain.com", "https://www.yourdomain.com"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

# Apply CORS configuration
aws s3api put-bucket-cors \
  --bucket tg-video-streamer-assets \
  --cors-configuration file://cors-config.json \
  --endpoint-url=https://nyc3.digitaloceanspaces.com
```

### 9.4 Use Pre-Signed URLs for Private Content

For premium or private content, use pre-signed URLs:

```python
# Example using boto3
import boto3
from botocore.client import Config

s3 = boto3.client('s3',
    endpoint_url='https://nyc3.digitaloceanspaces.com',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    config=Config(signature_version='s3v4')
)

# Generate pre-signed URL (valid for 1 hour)
url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'tg-video-streamer-assets', 'Key': 'premium/video1.mp4'},
    ExpiresIn=3600
)
```

### 9.5 Enable CDN Access Logs

Monitor access patterns:

```bash
# Note: DigitalOcean Spaces CDN doesn't support access logs
# Use application-level logging instead
# Or consider using CloudFlare in front for analytics
```

## Troubleshooting

### Issue 1: CDN Not Working

**Symptoms**: Content not served from CDN, direct origin access

**Solutions**:
1. Verify CDN is enabled:
   ```bash
   doctl spaces cdn list tg-video-streamer-assets --region nyc3
   ```
2. Check CDN endpoint is correct
3. Verify DNS is propagated (if using custom domain)
4. Clear local browser cache
5. Check `Cache-Control` headers on objects

### Issue 2: High Origin Load

**Symptoms**: Many requests hitting origin despite CDN

**Solutions**:
1. Check `Cache-Control` headers:
   ```bash
   aws s3api head-object \
     --bucket tg-video-streamer-assets \
     --key video1.mp4 \
     --endpoint-url=https://nyc3.digitaloceanspaces.com
   ```
2. Ensure `Cache-Control: public, max-age=...` is set
3. Increase cache TTL values
4. Check if cache is being purged frequently

### Issue 3: SSL Certificate Errors

**Symptoms**: Certificate validation errors

**Solutions**:
1. For custom domains, wait for Let's Encrypt certificate (10-30 minutes)
2. Verify domain DNS is correct:
   ```bash
   dig cdn.yourdomain.com
   ```
3. Check certificate status in DigitalOcean control panel
4. Ensure custom domain is added to CDN settings

### Issue 4: Slow Uploads

**Symptoms**: Slow file uploads to Spaces

**Solutions**:
1. Use multipart upload for large files:
   ```python
   # Example using boto3
   s3.upload_file(
       'large-video.mp4',
       'tg-video-streamer-assets',
       'videos/large-video.mp4',
       Config=boto3.s3.transfer.TransferConfig(
           multipart_threshold=100 * 1024 * 1024,  # 100MB
           max_concurrency=10
       )
   )
   ```
2. Check network connectivity
3. Try uploading from different region (consider multiple Spaces)

### Issue 5: 403 Forbidden Errors

**Symptoms**: Access denied when accessing objects

**Solutions**:
1. Check bucket policy allows public read
2. Verify access keys are correct
3. Check Space permissions
4. Ensure object exists:
   ```bash
   aws s3 ls s3://tg-video-streamer-assets/ \
     --endpoint-url=https://nyc3.digitaloceanspaces.com
   ```

### Issue 6: Cache Not Purging

**Symptoms**: Old content served after purge

**Solutions**:
1. Wait 5-15 minutes for CDN purge to propagate
2. Verify purge request succeeded:
   ```bash
   curl -X POST http://localhost:8000/api/v1/cdn/purge \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"urls": ["https://.../video1.mp4"]}'
   ```
3. Check response for success status
4. Clear browser cache
5. Verify URL is correct

### Issue 7: High Costs

**Symptoms**: Unexpectedly high bills

**Solutions**:
1. Review bandwidth usage:
   ```bash
   doctl spaces cdn list tg-video-streamer-assets --region nyc3
   ```
2. Monitor storage usage
3. Check request counts
4. Optimize cache TTLs
5. Use DigitalOcean cost dashboard

## Advanced Configuration

### Multi-Region Setup

Deploy multiple Spaces in different regions:

```bash
# Create Space in multiple regions
doctl spaces create tg-video-streamer-assets-us --region nyc3
doctl spaces create tg-video-streamer-assets-eu --region ams3
doctl spaces create tg-video-streamer-assets-asia --region sgp1

# Enable CDN on each
doctl spaces cdn enable tg-video-streamer-assets-us --region nyc3
doctl spaces cdn enable tg-video-streamer-assets-eu --region ams3
doctl spaces cdn enable tg-video-streamer-assets-asia --region sgp1
```

Configure geo-routing in your application:

```python
# Example: Route to nearest Space based on viewer location
regional_spaces = {
    'US': 'tg-video-streamer-assets-us.nyc3.cdn.digitaloceanspaces.com',
    'EU': 'tg-video-streamer-assets-eu.ams3.cdn.digitaloceanspaces.com',
    'ASIA': 'tg-video-streamer-assets-asia.sgp1.cdn.digitaloceanspaces.com'
}

def get_nearest_space(viewer_country):
    return regional_spaces.get(viewer_country, regional_spaces['US'])
```

### Lifecycle Policies

Automatically transition old content to lower-cost storage:

```bash
# Note: DigitalOcean Spaces doesn't support lifecycle policies yet
# Implement in application layer instead
```

### Versioning

Enable versioning to protect against accidental deletions:

```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket tg-video-streamer-assets \
  --versioning-configuration Status=Enabled \
  --endpoint-url=https://nyc3.digitaloceanspaces.com

# Check versioning status
aws s3api get-bucket-versioning \
  --bucket tg-video-streamer-assets \
  --endpoint-url=https://nyc3.digitaloceanspaces.com
```

### Replication

Sync data between multiple Spaces:

```python
# Example: Sync between regions
import boto3

source_s3 = boto3.client('s3',
    endpoint_url='https://nyc3.digitaloceanspaces.com',
    aws_access_key_id='ACCESS_KEY',
    aws_secret_access_key='SECRET_KEY'
)

dest_s3 = boto3.client('s3',
    endpoint_url='https://ams3.digitaloceanspaces.com',
    aws_access_key_id='ACCESS_KEY',
    aws_secret_access_key='SECRET_KEY'
)

# List objects
objects = source_s3.list_objects_v2(
    Bucket='tg-video-streamer-assets'
)

# Copy each object
for obj in objects.get('Contents', []):
    source_key = obj['Key']
    copy_source = {
        'Bucket': 'tg-video-streamer-assets',
        'Key': source_key
    }
    dest_s3.copy_object(
        CopySource=copy_source,
        Bucket='tg-video-streamer-assets-eu',
        Key=source_key
    )
```

## Maintenance

### Regular Tasks

**Daily**:
- Monitor cache hit ratio (target >85%)
- Check error rates

**Weekly**:
- Review bandwidth usage
- Analyze geographic performance
- Check storage usage

**Monthly**:
- Review and update cache rules
- Audit access keys
- Clean up old/unneeded files

### Cache Purging Strategy

```bash
# Purge specific files
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com/playlist.m3u8",
      "https://tg-video-streamer-assets.nyc3.cdn.digitaloceanspaces.com/video1.mp4"
    ]
  }'

# Purge entire Space (use sparingly)
curl -X POST http://localhost:8000/api/v1/cdn/purge \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"purge_all": true}'
```

⚠️ **Note**: Cache purging is instant but may take 5-15 minutes to propagate to all edge locations.

### Storage Cleanup

Remove old or unused files:

```bash
# List all objects
aws s3 ls s3://tg-video-streamer-assets --recursive \
  --endpoint-url=https://nyc3.digitaloceanspaces.com

# Delete specific object
aws s3 rm s3://tg-video-streamer-assets/old-video.mp4 \
  --endpoint-url=https://nyc3.digitaloceanspaces.com

# Delete multiple objects
aws s3 rm s3://tg-video-streamer-assets/old-videos/ --recursive \
  --endpoint-url=https://nyc3.digitaloceanspaces.com
```

## Performance Benchmarks

### Expected Latency Improvements

| Viewer Location | Direct Origin (ms) | DigitalOcean CDN (ms) | Improvement |
|-----------------|-------------------|----------------------|-------------|
| Same region | 50 | 20 | 60% faster |
| Different continent | 300 | 60 | 80% faster |
| Remote location | 500 | 100 | 80% faster |

### Cache Hit Ratio Targets

| Content Type | Target Cache Hit Ratio |
|--------------|------------------------|
| Static videos (MP4) | >90% |
| HLS segments (.ts) | >85% |
| Playlists (.m3u8) | >75% |
| Thumbnails | >90% |
| API responses | >65% |

### Cost Comparison (10 TB/month)

| Provider | Monthly Cost | Annual Cost |
|----------|--------------|-------------|
| DigitalOcean | $45 | $540 |
| AWS CloudFront | $850 | $10,200 |
| Cloudflare | $0 (free tier) | $0+ |

**Savings with DigitalOcean: $805/month (95%)**

## Migration Guide

### From AWS S3 to DigitalOcean Spaces

```bash
# Using rclone (recommended)
rclone config
# Create remote for S3 (source)
# Create remote for Spaces (destination)

# Sync data
rclone sync s3-source:bucket spaces-dest:space-name

# Using AWS CLI
aws s3 sync s3://source-bucket s3://tg-video-streamer-assets \
  --endpoint-url=https://nyc3.digitaloceanspaces.com

# Update application configuration
# Change CDN_PROVIDER from "cloudfront" to "digitalocean"
# Update endpoints and credentials
```

### From Cloudflare to DigitalOcean

```bash
# 1. Export content from Cloudflare R2
# 2. Import to DigitalOcean Spaces
# 3. Update DNS records
# 4. Update application configuration
# 5. Test CDN endpoint
```

## Related Documentation

- [AWS CloudFront Deployment Guide](./aws-cloudfront.md) - Alternative CDN provider
- [Cloudflare Deployment Guide](./cloudflare.md) - Free CDN option
- [Regional Deployment Guide](./regional-deployment.md) - Multi-region setup
- [Backend CDN API](../api/cdn.md) - API reference
- [Architecture Overview](../architecture/DEPLOYMENT_ARCHITECTURE.md) - System architecture

## Support

- **DigitalOcean Documentation**: https://docs.digitalocean.com/products/spaces/
- **DigitalOcean Community**: https://www.digitalocean.com/community/
- **DigitalOcean Support**: https://www.digitalocean.com/support/
- **Spaces CDN Guide**: https://docs.digitalocean.com/products/spaces/how-to/use-cdn/

## Summary

✅ **You now have**:
- DigitalOcean Space with CDN enabled
- Application integrated with DigitalOcean CDN
- Cache rules optimized for video streaming
- Monitoring and metrics in place
- Security best practices applied

🎯 **Next steps**:
- Test from multiple geographic locations
- Monitor cache hit ratio for first week
- Optimize TTLs based on content update frequency
- Set up cost monitoring
- Consider multi-region setup for global audience

📊 **Expected results**:
- 80% reduction in latency for global viewers
- 85%+ cache hit ratio for static content
- 95% cost savings vs AWS CloudFront
- Reduced origin server load
- Improved viewer experience

💰 **Cost benefits**:
- $0.005/GB CDN bandwidth (vs $0.085-0.17/GB for AWS)
- 95% cost savings on CDN bandwidth
- Predictable flat-rate pricing
- Free 1 TB/month CDN bandwidth
