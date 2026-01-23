# IP Whitelisting Configuration Guide

## Overview

This guide provides comprehensive instructions for configuring IP whitelisting for the Telegram Streamer platform. IP whitelisting restricts system access to trusted IP addresses and networks, providing enterprise-grade network security.

**Last Updated:** 2026-01-23
**Feature Status:** Production Ready
**Supported IP Versions:** IPv4 and IPv6

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding IP Whitelisting](#understanding-ip-whitelisting)
3. [Configuration Overview](#configuration-overview)
4. [Setup Instructions](#setup-instructions)
5. [Common Use Cases](#common-use-cases)
6. [Testing and Verification](#testing-and-verification)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Security Best Practices](#security-best-practices)

---

## Prerequisites

### Required Access

- **Administrator Account**: You must have admin or superadmin privileges
- **Backend Configuration**: Access to backend environment variables
- **Network Information**: Knowledge of your organization's network infrastructure

### Information to Gather

Before configuring IP whitelisting, collect the following:

- **Office IP Ranges**: Your organization's public IP addresses
- **VPN Exit IPs**: IP addresses used by your VPN service
- **Data Center IPs**: IP ranges for your hosting infrastructure
- **Cloud Service IPs**: Static IPs from cloud providers (if applicable)
- **Partner Networks**: Trusted third-party network IPs (if applicable)

---

## Understanding IP Whitelisting

### How IP Whitelisting Works

```
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│ Client  │                    │  App    │                    │ Database│
└────┬────┘                    └────┬────┘                    └────┬────┘
     │                              │                              │
     │ 1. HTTP Request              │                              │
     ├─────────────────────────────>│                              │
     │                              │                              │
     │                              │ 2. Extract Client IP         │
     │                              │ 3. Check Whitelist           │
     │                              │                              │
     │ 4a. IP Whitelisted           │                              │
     │<─────────────────────────────┤                              │
     │                              │                              │
     │ 5. Process Request           │                              │
     │                              ├─────────────────────────────>│
     │                              │                              │
     │ 4b. IP NOT Whitelisted       │                              │
     │<─────────────────────────────┤                              │
     │    (403 Forbidden)           │                              │
     │                              │                              │
```

### Key Components

1. **CIDR Notation**: Classless Inter-Domain Routing format for IP ranges (e.g., `192.168.1.0/24`)
2. **Middleware**: FastAPI middleware that intercepts all incoming requests
3. **Database Storage**: Whitelist entries stored in `ip_whitelist` table
4. **Client IP Extraction**: Handles X-Forwarded-For for proxy/load balancer scenarios
5. **Strict Mode**: Configurable behavior when whitelist is empty

### IP Detection Methods

The system extracts client IPs in the following order:

1. **X-Forwarded-For header**: For requests through proxies/load balancers (first IP)
2. **X-Real-IP header**: Alternative proxy header
3. **Direct connection IP**: From the TCP connection

---

## Configuration Overview

### Environment Variables

Configure IP whitelisting behavior in `backend/.env`:

```bash
# Enable/disable IP whitelisting feature
IP_WHITELIST_ENABLED=true

# Strict mode: if true, block all non-whitelisted IPs
# if false, allow all IPs when whitelist is empty
IP_WHITELIST_STRICT_MODE=false

# Allow loopback addresses (127.0.0.1, ::1, localhost)
# Recommended: true for development, false for production
IP_WHITELIST_ALLOW_LOOPBACK=true
```

### Whitelist Entry Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| **cidr** | string | Yes | IP address or CIDR range | `"192.168.1.0/24"` |
| **description** | string | No | Human-readable description | `"Office Network"` |
| **is_active** | boolean | No | Whether entry is enforced | `true` |

### CIDR Format Examples

| Type | Single IP | Range |
|------|-----------|-------|
| **IPv4** | `192.168.1.100` | `192.168.1.0/24` |
| **IPv6** | `2001:db8::1` | `2001:db8::/32` |

**Common CIDR Prefix Lengths:**

- `/32`: Single IPv4 address
- `/24`: 256 IPv4 addresses (common for office networks)
- `/16`: 65,536 IPv4 addresses (large organizations)
- `/128`: Single IPv6 address
- `/64`: Standard IPv6 subnet

---

## Setup Instructions

### Step 1: Enable IP Whitelisting

1. Open `backend/.env`
2. Set `IP_WHITELIST_ENABLED=true`
3. Configure strict mode based on your requirements:

```bash
# Recommended for initial setup
IP_WHITELIST_ENABLED=true
IP_WHITELIST_STRICT_MODE=false  # Don't block until whitelist is configured
IP_WHITELIST_ALLOW_LOOPBACK=true  # Allow local development
```

4. Restart the backend service

### Step 2: Add Whitelist Entries via Admin Panel

#### Method 1: Using the Web UI

1. Navigate to **Admin** → **Security** → **IP Whitelist**
2. Click **Add Entry**
3. Fill in the form:
   - **CIDR**: Enter IP address or range (e.g., `203.0.113.0/24`)
   - **Description**: Add a description (e.g., "San Francisco Office")
4. Click **Add Entry**

#### Method 2: Using the API

```bash
curl -X POST https://streamer.example.com/api/admin/ip-whitelist/entries \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "cidr": "203.0.113.0/24",
    "description": "San Francisco Office Network",
    "is_active": true
  }'
```

### Step 3: Verify Configuration

1. Navigate to **Admin** → **Security** → **IP Whitelist**
2. Verify your entries appear in the list
3. Check the status indicators:
   - **Total Entries**: All entries in database
   - **Active**: Entries currently being enforced
   - **IPv4/IPv6**: Breakdown by IP version

### Step 4: Test Access

#### Test from Whitelisted IP

```bash
# From an IP in your whitelist
curl https://streamer.example.com/api/health
# Expected: 200 OK
```

#### Test from Non-Whitelisted IP

```bash
# From an IP NOT in your whitelist
curl https://streamer.example.com/api/health
# Expected (strict_mode=true): 403 Forbidden
# Expected (strict_mode=false): 200 OK
```

### Step 5: Enable Strict Mode (Optional)

Once you've verified your whitelist is working correctly:

1. Add all necessary IP ranges
2. Test access from each network
3. Enable strict mode in `backend/.env`:
   ```bash
   IP_WHITELIST_STRICT_MODE=true
   ```
4. Restart the backend service
5. Verify access is restricted to whitelisted IPs only

**⚠️ Warning**: Enabling strict mode without proper whitelist entries will block all access except loopback (if allowed).

---

## Common Use Cases

### Use Case 1: Office Network Access

**Scenario**: Allow access only from your corporate office network.

**Configuration**:

1. Determine your office's public IP:
   ```bash
   curl ifconfig.me
   # Output: 203.0.113.42
   ```

2. Add the IP or network range:
   ```json
   {
     "cidr": "203.0.113.0/24",
     "description": "Corporate Office Network",
     "is_active": true
   }
   ```

### Use Case 2: VPN Access

**Scenario**: Allow users connected via corporate VPN.

**Configuration**:

1. Get your VPN exit IPs (from your IT department or VPN provider)
2. Add each VPN exit node:
   ```json
   {
     "cidr": "198.51.100.0/24",
     "description": "VPN Exit Nodes - US East",
     "is_active": true
   }
   ```

### Use Case 3: Multiple Office Locations

**Scenario**: Multiple offices need access.

**Configuration**:

Add entries for each location:
```json
[
  {
    "cidr": "203.0.113.0/24",
    "description": "San Francisco Office",
    "is_active": true
  },
  {
    "cidr": "198.51.100.0/24",
    "description": "New York Office",
    "is_active": true
  },
  {
    "cidr": "192.0.2.0/24",
    "description": "London Office",
    "is_active": true
  }
]
```

### Use Case 4: Cloud Services with Static IPs

**Scenario**: Allow access from cloud services with static IPs (e.g., AWS, GCP).

**Configuration**:

1. Obtain static IPs from your cloud provider
2. Add the IP ranges:
   ```json
   {
     "cidr": "52.0.0.0/16",
     "description": "AWS us-east-1",
     "is_active": true
   }
   ```

### Use Case 5: Development Environment

**Scenario**: Allow access from development machines and CI/CD systems.

**Configuration**:

```json
[
  {
    "cidr": "127.0.0.1",
    "description": "Localhost (development)",
    "is_active": true
  },
  {
    "cidr": "10.0.0.0/8",
    "description": "Internal VPC",
    "is_active": true
  }
]
```

**Note**: Ensure `IP_WHITELIST_ALLOW_LOOPBACK=true` is set for development.

### Use Case 6: Partner Integration

**Scenario**: Third-party partners need API access.

**Configuration**:

1. Create a dedicated API endpoint
2. Add partner's static IPs:
   ```json
   {
     "cidr": "203.0.113.50/32",
     "description": "Partner API Integration - Acme Corp",
     "is_active": true
   }
   ```

### Use Case 7: Temporary Access

**Scenario**: Grant temporary access for contractors or audits.

**Configuration**:

1. Add the IP with a description:
   ```json
   {
     "cidr": "198.51.100.75/32",
     "description": "Temporary Access - Security Audit 2026-01-23",
     "is_active": true
   }
   ```

2. **Remember to deactivate or delete after access period**:
   ```bash
   curl -X POST https://streamer.example.com/api/admin/ip-whitelist/entries/{id}/deactivate \
     -H "Authorization: Bearer <admin-token>"
   ```

---

## Testing and Verification

### Test 1: Verify Whitelist Entry Creation

**API Request**:
```bash
curl -X POST https://streamer.example.com/api/admin/ip-whitelist/entries \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "cidr": "192.0.2.100",
    "description": "Test Entry",
    "is_active": true
  }'
```

**Expected Response** (201 Created):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "cidr": "192.0.2.100",
  "description": "Test Entry",
  "is_active": true,
  "is_ipv4": true,
  "is_ipv6": false,
  "created_by_id": "...",
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": "2026-01-23T10:00:00Z"
}
```

### Test 2: Check IP Status

**API Request**:
```bash
curl -X POST "https://streamer.example.com/api/admin/ip-whitelist/check?ip=192.0.2.100" \
  -H "Authorization: Bearer <admin-token>"
```

**Expected Response**:
```json
{
  "ip": "192.0.2.100",
  "is_whitelisted": true
}
```

### Test 3: Test Access from Whitelisted IP

```bash
# From IP 192.0.2.100
curl -i https://streamer.example.com/api/health
```

**Expected Response** (200 OK):
```
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "healthy"}
```

### Test 4: Test Access from Non-Whitelisted IP (Strict Mode)

```bash
# From IP 198.51.100.50 (not in whitelist)
curl -i https://streamer.example.com/api/health
```

**Expected Response** (403 Forbidden):
```
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": "Access denied from IP: 198.51.100.50",
  "error_type": "ip_whitelist_restricted"
}
```

### Test 5: Verify CIDR Range Matching

Add a CIDR range:
```bash
curl -X POST https://streamer.example.com/api/admin/ip-whitelist/entries \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "cidr": "192.0.2.0/24",
    "description": "Test Range",
    "is_active": true
  }'
```

Test IPs within the range:
```bash
# Test multiple IPs in the range
for ip in 192.0.2.1 192.0.2.100 192.0.2.254; do
  echo "Testing $ip:"
  curl -s "https://streamer.example.com/api/admin/ip-whitelist/check?ip=$ip" \
    -H "Authorization: Bearer <admin-token>" | jq '.'
done
```

**Expected Output**:
```json
{"ip": "192.0.2.1", "is_whitelisted": true}
{"ip": "192.0.2.100", "is_whitelisted": true}
{"ip": "192.0.2.254", "is_whitelisted": true}
```

### Test 6: Verify IPv6 Support

```bash
curl -X POST https://streamer.example.com/api/admin/ip-whitelist/entries \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "cidr": "2001:db8::/32",
    "description": "Test IPv6 Range",
    "is_active": true
  }'
```

Check IPv6 IP:
```bash
curl -s "https://streamer.example.com/api/admin/ip-whitelist/check?ip=2001:db8::1" \
  -H "Authorization: Bearer <admin-token>"
```

**Expected Response**:
```json
{
  "ip": "2001:db8::1",
  "is_whitelisted": true
}
```

### Test 7: Verify Activation/Deactivation

**Deactivate Entry**:
```bash
curl -X POST https://streamer.example.com/api/admin/ip-whitelist/entries/{id}/deactivate \
  -H "Authorization: Bearer <admin-token>"
```

**Verify Inactive IP is Blocked** (in strict mode):
```bash
curl -s "https://streamer.example.com/api/admin/ip-whitelist/check?ip=192.0.2.100" \
  -H "Authorization: Bearer <admin-token>"
```

**Expected Response**:
```json
{
  "ip": "192.0.2.100",
  "is_whitelisted": false
}
```

### Test 8: Verify Audit Logging

1. Navigate to **Admin** → **Audit Logs**
2. Filter by event type: `ip_whitelist_created`, `ip_whitelist_updated`, `ip_whitelist_deleted`
3. Verify each IP whitelist change is logged with:
   - User who made the change
   - IP address/range affected
   - Timestamp
   - Change details

---

## Advanced Configuration

### CIDR Notation Deep Dive

#### Understanding CIDR

CIDR (Classless Inter-Domain Routing) notation: `IP_ADDRESS/PREFIX_LENGTH`

- **Prefix Length**: Number of bits in the network portion
- **Host Bits**: Remaining bits for individual hosts
- **Total Hosts**: 2^(32 - prefix_length) for IPv4

**Examples**:

| CIDR | Network Bits | Host Bits | Total IPs | Usable IPs |
|------|--------------|-----------|-----------|------------|
| `192.0.2.0/32` | 32 | 0 | 1 | 1 |
| `192.0.2.0/24` | 24 | 8 | 256 | 254 |
| `192.0.2.0/16` | 16 | 16 | 65,536 | 65,534 |
| `2001:db8::/128` | 128 | 0 | 1 | 1 |
| `2001:db8::/64` | 64 | 64 | 2^64 | ~2^64 |

#### Calculating CIDR Ranges

**Python Example**:
```python
import ipaddress

# Create network
network = ipaddress.ip_network("192.0.2.0/24")

print(f"Network: {network.network_address}")
print(f"Broadcast: {network.broadcast_address}")
print(f"First usable: {list(network.hosts())[0]}")
print(f"Last usable: {list(network.hosts())[-1]}")
print(f"Total hosts: {network.num_addresses}")
```

**Output**:
```
Network: 192.0.2.0
Broadcast: 192.0.2.255
First usable: 192.0.2.1
Last usable: 192.0.2.254
Total hosts: 256
```

#### Common CIDR Mistakes

❌ **Incorrect**:
```json
{"cidr": "192.0.2.0/33"}  // Invalid: prefix > 32 for IPv4
{"cidr": "192.0.2.256"}    // Invalid: octet > 255
{"cidr": "192.0.2"}        // Missing prefix for range
```

✅ **Correct**:
```json
{"cidr": "192.0.2.0/24"}   // Valid IPv4 range
{"cidr": "192.0.2.100/32"} // Valid single IPv4
{"cidr": "2001:db8::/32"}  // Valid IPv6 range
```

### Proxy and Load Balancer Configuration

When your application is behind a proxy or load balancer (nginx, AWS ALB, Cloudflare), the client IP is in the `X-Forwarded-For` header.

**nginx Configuration**:
```nginx
location / {
    proxy_pass http://backend:8000;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**AWS ALB Configuration**:
```python
# The middleware automatically handles X-Forwarded-For from ALB
# Ensure ALB target group attributes:
# load_balancing.cross_zone.enabled = true
```

**Trusted Proxy Configuration**:

If you need to trust specific proxy IPs:

```python
# In backend/src/frameworks/http/middleware/ip_whitelist.py
# Modify _get_client_ip to validate X-Forwarded-For only from trusted proxies
TRUSTED_PROXIES = ["10.0.0.0/8", "172.16.0.0/12"]
```

### Skipping IP Whitelist for Specific Paths

Certain endpoints should skip IP whitelist checking:

**Currently Excluded Paths**:
- `/health` - Health checks
- `/metrics` - Monitoring metrics
- `/api/health` - API health endpoint
- `/api/auth/login` - Login endpoint
- `/docs` - API documentation
- `/redoc` - Alternative API docs
- `/openapi.json` - OpenAPI schema

**To Add More Exemptions**:

Edit `backend/src/frameworks/http/middleware/ip_whitelist.py`:

```python
def _should_skip_whitelist(self, path: str) -> bool:
    skip_paths = [
        "/health",
        "/metrics",
        "/api/health",
        "/api/auth/login",
        "/api/webhooks",  # Add webhook endpoint
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    return any(path.startswith(p) for p in skip_paths)
```

### Performance Optimization

#### Database Indexing

The `cidr` field is already indexed in the database model:

```python
# backend/src/models/ip_whitelist.py
cidr = Column(String(45), nullable=False, unique=True, index=True)
```

This ensures fast lookups when checking IPs.

#### Caching Strategy

For high-traffic applications, consider caching whitelist entries:

```python
# Example: Redis caching (to be implemented)
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_whitelist():
    # Fetch and cache whitelist entries
    pass
```

#### Minimize Database Queries

The middleware queries the database on every request. To optimize:

1. **Enable Strict Mode**: Only check when whitelist is non-empty
2. **Use Read Replicas**: Offload reads to read replica
3. **Implement Cache**: Cache whitelist entries in Redis (TTL: 5 minutes)

### Multi-Region Deployment

For applications deployed across multiple regions:

#### Strategy 1: Regional Whitelists

```json
[
  {
    "cidr": "203.0.113.0/24",
    "description": "US-East Office",
    "is_active": true
  },
  {
    "cidr": "198.51.100.0/24",
    "description": "EU-West Office",
    "is_active": true
  }
]
```

#### Strategy 2: Global Whitelist with Regional Exceptions

1. **Global whitelist**: Common IPs (VPNs, data centers)
2. **Regional overrides**: Location-specific entries

#### Strategy 3: DNS-Based Routing

Combine IP whitelisting with DNS routing:
- Use GeoDNS to route users to nearest region
- Apply region-specific IP whitelists

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "Access denied from IP" Error

**Symptoms**:
- 403 Forbidden response
- Error: `"Access denied from IP: X.X.X.X"`

**Possible Causes**:
- IP not in whitelist
- Strict mode enabled and whitelist is empty
- Entry is inactive

**Solutions**:

1. Check if IP is whitelisted:
   ```bash
   curl -s "https://streamer.example.com/api/admin/ip-whitelist/check?ip=YOUR_IP" \
     -H "Authorization: Bearer <admin-token>"
   ```

2. Verify entry is active:
   ```bash
   curl https://streamer.example.com/api/admin/ip-whitelist/entries \
     -H "Authorization: Bearer <admin-token>" | jq '.[] | select(.cidr == "YOUR_IP")'
   ```

3. If not whitelisted, add the IP:
   ```bash
   curl -X POST https://streamer.example.com/api/admin/ip-whitelist/entries \
     -H "Authorization: Bearer <admin-token>" \
     -H "Content-Type: application/json" \
     -d '{"cidr": "YOUR_IP", "is_active": true}'
   ```

#### 2. "Invalid CIDR format" Error

**Symptoms**:
- 400 Bad Request
- Error: `"Invalid CIDR format: X.X.X.X/XX"`

**Possible Causes**:
- Typos in CIDR notation
- Prefix length out of range
- Invalid IP address

**Solutions**:

1. **Validate CIDR format**:
   - IPv4: `X.X.X.X/PREFIX` (prefix: 0-32)
   - IPv6: `X:X::X/PREFIX` (prefix: 0-128)

2. **Common mistakes**:
   - ❌ `192.168.1.0/33` (prefix > 32)
   - ❌ `192.168.1.256` (octet > 255)
   - ❌ `192.168.1` (missing prefix for range)

3. **Use a CIDR calculator**: https://www.cidrcalc.org/

#### 3. IPs Behind Proxy Not Detected Correctly

**Symptoms**:
- Whitelist blocking proxy IP instead of client IP
- All requests appear from same IP

**Possible Causes**:
- X-Forwarded-For header not configured
- Proxy not forwarding client IP
- Multiple proxy layers

**Solutions**:

1. **Check proxy configuration**:
   ```nginx
   # nginx
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header X-Real-IP $remote_addr;
   ```

2. **Verify header is being sent**:
   ```bash
   curl -I https://streamer.example.com
   # Check response for X-Forwarded-For
   ```

3. **Debug IP extraction**:
   - Enable debug logging in middleware
   - Check backend logs for detected IP

#### 4. Loopback Access Blocked

**Symptoms**:
- Cannot access application from localhost
- 127.0.0.1 blocked

**Possible Causes**:
- `IP_WHITELIST_ALLOW_LOOPBACK=false`
- Loopback not in whitelist

**Solutions**:

1. **Check environment variable**:
   ```bash
   # backend/.env
   IP_WHITELIST_ALLOW_LOOPBACK=true
   ```

2. **Or add loopback to whitelist**:
   ```bash
   curl -X POST https://streamer.example.com/api/admin/ip-whitelist/entries \
     -H "Authorization: Bearer <admin-token>" \
     -H "Content-Type: application/json" \
     -d '{"cidr": "127.0.0.1", "description": "Localhost", "is_active": true}'
   ```

#### 5. Performance Degradation

**Symptoms**:
- Slow response times
- Increased database load

**Possible Causes**:
- Database query on every request
- No caching
- Large number of whitelist entries

**Solutions**:

1. **Enable strict mode only when needed**:
   ```bash
   IP_WHITELIST_STRICT_MODE=false  # Allow all when empty
   ```

2. **Implement caching** (Redis):
   ```python
   # Cache whitelist entries for 5 minutes
   @cache(ttl=300)
   def get_whitelist_entries():
       return db.query(IPWhitelist).filter_by(is_active=True).all()
   ```

3. **Use read replicas** for database queries

#### 6. Whitelist Entry Not Working

**Symptoms**:
- Entry added but IP still blocked
- CIDR looks correct but doesn't match

**Possible Causes**:
- Entry inactive
- Typo in CIDR
- IP address format mismatch

**Solutions**:

1. **Verify entry is active**:
   ```bash
   curl https://streamer.example.com/api/admin/ip-whitelist/entries \
     -H "Authorization: Bearer <admin-token>" | jq '.[] | {cidr, is_active}'
   ```

2. **Test IP check endpoint**:
   ```bash
   curl "https://streamer.example.com/api/admin/ip-whitelist/check?ip=TEST_IP" \
     -H "Authorization: Bearer <admin-token>"
   ```

3. **Normalize CIDR**:
   - The system automatically normalizes CIDR (e.g., `192.168.001.001` → `192.168.1.1`)
   - Check the actual CIDR stored in database

#### 7. All Users Locked Out

**Symptoms**:
- Everyone blocked including admins
- Cannot access admin panel to fix

**Possible Causes**:
- Strict mode enabled with no whitelist
- All whitelist entries deactivated
- Network configuration changed

**Solutions**:

1. **Access from loopback** (if allowed):
   ```bash
   # From server itself
   curl https://localhost/api/admin/ip-whitelist/entries \
     -H "Authorization: Bearer <admin-token>"
   ```

2. **Disable IP whitelisting via environment**:
   ```bash
   # backend/.env
   IP_WHITELIST_ENABLED=false
   ```

   Then restart backend and fix whitelist via admin panel.

3. **Direct database access** (last resort):
   ```sql
   -- Deactivate IP whitelist via database
   UPDATE ip_whitelist SET is_active = false;

   -- Or disable feature in config
   -- Edit environment variable and restart service
   ```

### Debug Logging

Enable detailed IP whitelist logging:

```bash
# backend/.env
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

Debug logs will include:
- Client IP detected
- X-Forwarded-For header value
- Whitelist check result
- Database queries
- Match/decision details

### Test Tools

#### Test IP from CIDR Range

```python
import ipaddress

def ip_in_cidr(ip, cidr):
    """Test if IP is in CIDR range."""
    network = ipaddress.ip_network(cidr, strict=False)
    addr = ipaddress.ip_address(ip)
    return addr in network

# Usage
print(ip_in_cidr("192.0.2.100", "192.0.2.0/24"))  # True
print(ip_in_cidr("192.0.3.100", "192.0.2.0/24"))  # False
```

#### List All IPs in CIDR Range

```python
import ipaddress

def list_ips_in_cidr(cidr):
    """List all IPs in a CIDR range."""
    network = ipaddress.ip_network(cidr, strict=False)
    return [str(host) for host in network.hosts()]

# Usage
ips = list_ips_in_cidr("192.0.2.0/30")  # Small range for demo
print(ips)  # ['192.0.2.1', '192.0.2.2']
```

---

## Security Best Practices

### 1. Principle of Least Privilege

**Recommendation**: Whitelist only necessary IP ranges.

- ✅ Whitelist specific office networks: `203.0.113.0/24`
- ❌ Whitelist entire internet: `0.0.0.0/0`

**Rationale**: Minimizing the attack surface reduces risk of unauthorized access.

### 2. Regular Whitelist Audits

**Schedule**: Quarterly reviews of IP whitelist entries.

**Audit Checklist**:
- [ ] Remove inactive entries
- [ ] Verify descriptions are accurate
- [ ] Check for overly broad ranges
- [ ] Remove temporary access that's no longer needed
- [ ] Validate business justification for each entry

**Automation**:
```python
# Example: Audit script to find stale entries
stale_entries = db.query(IPWhitelist).filter(
    IPWhitelist.created_at < datetime.now() - timedelta(days=90)
).all()
```

### 3. Document Whitelist Entries

**Best Practice**: Always include descriptive descriptions.

✅ **Good**:
```json
{
  "cidr": "203.0.113.0/24",
  "description": "San Francisco Office - ISP: Comcast - Contact: IT Dept (ext. 1234)",
  "is_active": true
}
```

❌ **Poor**:
```json
{
  "cidr": "203.0.113.0/24",
  "description": "Office",
  "is_active": true
}
```

### 4. Use Specific Ranges

**Recommendation**: Prefer specific ranges over broad ones.

| Priority | CIDR | Use Case |
|----------|------|----------|
| ⭐ Best | `/32` (IPv4) or `/128` (IPv6) | Single IP |
| ⭐ Good | `/24` | Small office (256 IPs) |
| ⚠️ Caution | `/16` | Large organization (65K IPs) |
| ❌ Avoid | `/8` | Entire ISP (16M IPs) |

### 5. Monitor IP Whitelist Events

**Log Types**:
- `ip_whitelist_created` - New entry added
- `ip_whitelist_updated` - Entry modified
- `ip_whitelist_deleted` - Entry removed
- `ip_whitelist_activated` - Entry enabled
- `ip_whitelist_deactivated` - Entry disabled

**Monitoring Recommendations**:
- Set up alerts for whitelist modifications
- Review audit logs weekly
- Investigate unexpected changes

### 6. Disable Feature When Not Needed

**Recommendation**: If IP whitelisting is not required, disable it.

```bash
# backend/.env
IP_WHITELIST_ENABLED=false
```

**Benefits**:
- Reduced database load
- Faster response times
- Simplified access management

### 7. Secure Admin Access

**Recommendation**: Protect IP whitelist management endpoints.

**Implementation**:
- Require admin role for all IP whitelist API endpoints
- Use 2FA for admin accounts
- Log all whitelist changes
- Consider IP-based restrictions on admin endpoints (double protection)

### 8. Plan for Changes

**Scenario**: ISP changes or office relocation.

**Mitigation**:
1. **Monitor**: Track expiry of current IP allocations
2. **Test**: Add new IPs before removing old ones
3. **Overlap**: Keep old and new entries active during transition
4. **Verify**: Test access from new IPs before removing old entries

### 9. Use Environment-Specific Settings

**Development**:
```bash
IP_WHITELIST_ENABLED=true
IP_WHITELIST_STRICT_MODE=false
IP_WHITELIST_ALLOW_LOOPBACK=true
```

**Staging**:
```bash
IP_WHITELIST_ENABLED=true
IP_WHITELIST_STRICT_MODE=false
IP_WHITELIST_ALLOW_LOOPBACK=true
```

**Production**:
```bash
IP_WHITELIST_ENABLED=true
IP_WHITELIST_STRICT_MODE=true
IP_WHITELIST_ALLOW_LOOPBACK=false
```

### 10. Implement Backup Access Methods

**Scenario**: Locked out due to IP whitelist misconfiguration.

**Recovery Options**:

1. **Loopback Access**:
   - Direct server access
   - SSH into server
   - Access via localhost

2. **Database Access**:
   - Direct database connection
   - Disable whitelist entries
   - Reset configuration

3. **Environment Variables**:
   - SSH into server
   - Edit `.env` file
   - Set `IP_WHITELIST_ENABLED=false`
   - Restart service

4. **Emergency Disable Script**:
   ```bash
   #!/bin/bash
   # Emergency IP whitelist disable
   ssh production-server "cd /app && sed -i 's/IP_WHITELIST_ENABLED=true/IP_WHITELIST_ENABLED=false/' .env && systemctl restart backend"
   ```

### 11. Compliance Considerations

#### SOC 2 Compliance

IP whitelisting contributes to SOC 2 compliance:

- **Access Control**: Restricts system access to authorized networks
- **Monitoring**: All whitelist changes are logged
- **Audit Trail**: Complete history of access control modifications

**Evidence for Auditors**:
- IP whitelist entry logs from audit table
- Configuration documentation
- Access review reports

#### GDPR Compliance

IP whitelisting supports GDPR:

- **Data Protection**: Limits access to personal data
- **Access Control**: Implements technical safeguards for data
- **Accountability**: Logs provide evidence of access control

**Note**: IP addresses can be considered personal data under GDPR. Handle whitelist entries with appropriate data protection measures.

### 12. Rate Limiting Combination

**Recommendation**: Combine IP whitelisting with rate limiting.

**Architecture**:
```
Request → IP Whitelist → Rate Limiter → Application
           (allow/block)    (throttle)
```

**Benefits**:
- Defense in depth
- Protection from whitelist abuse
- DDoS mitigation

---

## API Reference

### IP Whitelist Management Endpoints

#### List All Entries

```http
GET /api/admin/ip-whitelist/entries
Authorization: Bearer <admin-token>

Query Parameters:
  - active_only: boolean (default: false)
  - ipv4_only: boolean (default: false)
  - ipv6_only: boolean (default: false)
```

**Response** (200 OK):
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "cidr": "192.0.2.0/24",
    "description": "Office Network",
    "is_active": true,
    "is_ipv4": true,
    "is_ipv6": false,
    "created_by_id": "abc-123",
    "created_at": "2026-01-23T10:00:00Z",
    "updated_at": "2026-01-23T10:00:00Z"
  }
]
```

#### Get Whitelist Info

```http
GET /api/admin/ip-whitelist/entries/info
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "total_entries": 10,
  "active_entries": 8,
  "inactive_entries": 2,
  "ipv4_entries": 9,
  "ipv6_entries": 1
}
```

#### Get Single Entry

```http
GET /api/admin/ip-whitelist/entries/{entry_id}
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "cidr": "192.0.2.0/24",
  "description": "Office Network",
  "is_active": true,
  "is_ipv4": true,
  "is_ipv6": false,
  "created_by_id": "abc-123",
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": "2026-01-23T10:00:00Z"
}
```

#### Create Entry

```http
POST /api/admin/ip-whitelist/entries
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "cidr": "192.0.2.0/24",
  "description": "Office Network",
  "is_active": true
}
```

**Response** (201 Created):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "cidr": "192.0.2.0/24",
  "description": "Office Network",
  "is_active": true,
  "is_ipv4": true,
  "is_ipv6": false,
  "created_by_id": "abc-123",
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": "2026-01-23T10:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid CIDR format
- `409 Conflict`: CIDR already exists

#### Update Entry

```http
PUT /api/admin/ip-whitelist/entries/{entry_id}
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "description": "Updated description",
  "is_active": false
}
```

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "cidr": "192.0.2.0/24",
  "description": "Updated description",
  "is_active": false,
  "is_ipv4": true,
  "is_ipv6": false,
  "created_by_id": "abc-123",
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": "2026-01-23T11:00:00Z"
}
```

#### Delete Entry

```http
DELETE /api/admin/ip-whitelist/entries/{entry_id}
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "IP whitelist entry deleted",
  "id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### Activate Entry

```http
POST /api/admin/ip-whitelist/entries/{entry_id}/activate
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "IP whitelist entry activated",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "is_active": true
}
```

#### Deactivate Entry

```http
POST /api/admin/ip-whitelist/entries/{entry_id}/deactivate
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "IP whitelist entry deactivated",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "is_active": false
}
```

#### Check IP Status

```http
POST /api/admin/ip-whitelist/check?ip={ip_address}
Authorization: Bearer <admin-token>
```

**Response** (200 OK):
```json
{
  "ip": "192.0.2.100",
  "is_whitelisted": true
}
```

---

## Glossary

| Term | Definition |
|------|------------|
| **CIDR** | Classless Inter-Domain Routing - notation for IP ranges (e.g., `192.168.1.0/24`) |
| **IP Whitelisting** | Security practice of allowing access only from specific IP addresses |
| **IPv4** | Internet Protocol version 4 - 32-bit IP addresses (e.g., `192.168.1.1`) |
| **IPv6** | Internet Protocol version 6 - 128-bit IP addresses (e.g., `2001:db8::1`) |
| **Prefix Length** | Number of bits in network portion of CIDR (e.g., `/24`) |
| **Strict Mode** | Configuration where all non-whitelisted IPs are blocked |
| **Loopback** | Local interface for testing (127.0.0.1 for IPv4, ::1 for IPv6) |
| **X-Forwarded-For** | HTTP header containing original client IP when behind proxy |
| **X-Real-IP** | Alternative HTTP header for client IP |
| **Middleware** | Software component that processes requests before they reach the application |
| **ACL** | Access Control List - rules controlling network access |
| **VPN** | Virtual Private Network - encrypted tunnel for remote access |

---

## Related Documentation

### Internal Resources

- **Security Dashboard**: `/admin/security` - Compliance and security overview
- **SSO Setup Guide**: `docs/security/SSO_SETUP_GUIDE.md` - SAML configuration
- **2FA Enforcement Guide**: `docs/security/2FA_ENFORCEMENT_GUIDE.md` - Two-factor authentication
- **SOC 2 Compliance**: `docs/compliance/SOC2_README.md` - Compliance documentation
- **GDPR Compliance**: `docs/compliance/GDPR_README.md` - Data protection documentation

### External Resources

- **CIDR Calculator**: https://www.cidrcalc.org/
- **IP Address Info**: https://ipinfo.io/
- **Network Calculators**: https://www.subnet-calculator.com/
- **nginx Proxy Headers**: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-23 | Initial release with IPv4/IPv6 support, CIDR validation, and proxy handling |

---

**Document ID:** IP_WHITELIST_GUIDE
**Status:** Active
**Classification:** Public Documentation
