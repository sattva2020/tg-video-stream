# Deployment Troubleshooting Guide

**Last Updated**: January 24, 2026
**Version**: 1.0
**Related Docs**: [PRODUCTION_DEPLOYMENT_GUIDE.md](./PRODUCTION_DEPLOYMENT_GUIDE.md) | [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

---

## 📋 Table of Contents

1. [Quick Diagnosis](#quick-diagnosis)
2. [Secrets & Encryption Issues](#secrets--encryption-issues)
3. [Docker Deployment Issues](#docker-deployment-issues)
4. [Bare-Metal (systemd) Deployment Issues](#bare-metal-systemd-deployment-issues)
5. [Database Connectivity](#database-connectivity)
6. [Redis Connectivity](#redis-connectivity)
7. [Health Check Failures](#health-check-failures)
8. [Backup & Restore Issues](#backup--restore-issues)
9. [Monitoring Stack Issues](#monitoring-stack-issues)
10. [Network & Firewall Issues](#network--firewall-issues)
11. [Performance Issues](#performance-issues)
12. [Stream Quality Issues](#stream-quality-issues)
13. [Getting Help](#getting-help)

---

## 🔍 Quick Diagnosis

### Health Check First

**Always start with the health check endpoint**:

```bash
# Check overall system health
curl http://localhost:8000/api/health | jq .

# Check readiness (for Kubernetes/probes)
curl http://localhost:8000/api/health/ready | jq .
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-24T10:30:00Z",
  "dependencies": [
    {"name": "database", "status": "up", "latency_ms": 5},
    {"name": "redis", "status": "up", "latency_ms": 1}
  ],
  "stream_details": {
    "active_streams": 0,
    "total_listeners": 0
  }
}
```

### Check Service Status

```bash
# Docker deployment
docker compose ps

# Bare-metal deployment
systemctl status sattva-streamer.service
systemctl status sattva-backend.service
```

### Check Logs

```bash
# Docker logs (last 100 lines)
docker compose logs --tail=100 backend

# Follow logs in real-time
docker compose logs -f backend

# Bare-metal logs
journalctl -u sattva-streamer -n 100 -f
```

### Common Error Patterns

| Error Pattern | Likely Cause | Quick Fix |
|--------------|--------------|-----------|
| `Connection refused` | Service not running | Start service |
| `Address already in use` | Port conflict | Kill process or change port |
| `Permission denied` | File permissions | `chmod` or `chown` |
| `No such file` | Missing file/directory | Create or restore |
| `failed to decrypt` | Secrets issue | Check age key |

---

## 🔐 Secrets & Encryption Issues

### Issue: SOPS Decryption Fails

**Symptoms**:
```
Error: failed to decrypt .env.enc with SOPS
Error: could not decrypt file
```

**Diagnosis**:
```bash
# Check if age key exists
ls -la .internal/age.key

# Check SOPS_AGE_KEY_FILE environment variable
echo $SOPS_AGE_KEY_FILE

# Try manual decryption
SOPS_AGE_KEY_FILE=.internal/age.key sops --decrypt .env.enc
```

**Solutions**:

**Solution 1: Key File Missing or Wrong Path**
```bash
# If key file doesn't exist locally
ls -la .internal/

# Copy from secure backup
scp /secure/backup/age.key .internal/

# Set correct permissions
chmod 600 .internal/age.key
```

**Solution 2: Environment Variable Not Set**
```bash
# For current session
export SOPS_AGE_KEY_FILE=$(pwd)/.internal/age.key

# For persistence (add to ~/.bashrc or ~/.zshrc)
echo 'export SOPS_AGE_KEY_FILE=/opt/tg_video_streamer/.age.key' >> ~/.bashrc
source ~/.bashrc
```

**Solution 3: Key File Corrupted**
```bash
# Check if key file is valid text
cat .internal/age.key

# Should show: AGE-SECRET-KEY-1XXXXX...

# If corrupted, restore from backup
# You MUST have the original key saved securely
```

**Solution 4: Wrong Key Used for Encryption**
```bash
# Check which key was used for encryption
sops --decrypt .env.enc 2>&1 | grep "age"

# Re-encrypt with correct key
SOPS_AGE_KEY_FILE=.internal/age.key ./scripts/encrypt-secrets.sh .env.master
```

---

### Issue: `.env` Missing After Deployment

**Symptoms**:
```
Error: .env file not found
Environment variables not loaded
```

**Diagnosis**:
```bash
# Check if .env.enc exists
ls -la .env.enc

# Check if .env exists
ls -la .env

# Check decryption script logs
./scripts/decrypt-secrets.sh --dry-run
```

**Solutions**:

**Solution 1: Decrypt Manually**
```bash
cd /opt/tg_video_streamer/current

# Force decryption
SOPS_AGE_KEY_FILE=/opt/tg_video_streamer/.age.key \
  ./scripts/decrypt-secrets.sh --force

# Verify .env created
ls -la .env
```

**Solution 2: Fix Deployment Script**
```bash
# Check deployment script includes decryption step
grep -n "decrypt-secrets" scripts/deploy-unified.sh

# Add decryption if missing
# Add after deployment:
# ./scripts/decrypt-secrets.sh
```

**Solution 3: Check Permissions**
```bash
# .env should be readable by service user
ls -la .env

# Fix permissions
chmod 600 .env
chown $(whoami):$(whoami) .env
```

---

## 🐳 Docker Deployment Issues

### Issue: Container Won't Start

**Symptoms**:
```
Error: Container exited with code 1
docker compose ps shows "Exit 1"
```

**Diagnosis**:
```bash
# Check container status
docker compose ps

# Inspect container
docker compose inspect backend

# Check logs
docker compose logs backend
```

**Solutions**:

**Solution 1: Missing Environment Variables**
```bash
# Check if .env exists
ls -la .env

# Restart with environment
docker compose down
docker compose up -d
```

**Solution 2: Port Already in Use**
```bash
# Find what's using the port
sudo lsof -i :8000
sudo netstat -tulpn | grep 8000

# Kill the process
kill -9 <PID>

# Or change port in .env
PORT=8001
```

**Solution 3: Volume Mount Issues**
```bash
# Check volume mounts
docker compose config | grep -A 10 volumes

# Ensure directories exist
mkdir -p logs data

# Fix permissions
chmod 755 logs data
```

**Solution 4: Resource Limits Too Low**
```bash
# Check resource limits in docker-compose.yml
grep -A 5 "resources:" docker-compose.yml

# Increase limits if needed
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G  # Was 1G
          cpus: '2'   # Was '1'
```

---

### Issue: Docker Compose Fails with "Network Error"

**Symptoms**:
```
Error: Failed to connect to network
Error: Network creation failed
```

**Diagnosis**:
```bash
# Check Docker networks
docker network ls

# Check existing network
docker network inspect tg_video_streamer_default
```

**Solutions**:

**Solution 1: Remove Stale Networks**
```bash
# Stop all containers
docker compose down

# Remove unused networks
docker network prune

# Recreate
docker compose up -d
```

**Solution 2: Fix Network Conflicts**
```bash
# Check network in docker-compose.yml
grep -A 10 "networks:" docker-compose.yml

# Use custom network to avoid conflicts
networks:
  default:
    name: sattva-network
    external: false
```

---

### Issue: Container Keeps Restarting (Restart Loop)

**Symptoms**:
```
docker compose ps shows "Restarting (1) X seconds ago"
```

**Diagnosis**:
```bash
# Check restart count
docker compose ps

# Check recent logs
docker compose logs --tail=50 backend

# Check container exit code
docker compose ps | awk '{print $5}'
```

**Solutions**:

**Solution 1: Application Crash**
```bash
# Check logs for stack trace
docker compose logs backend | grep -i "error\|traceback"

# Common causes:
# - Missing dependencies
# - Database connection failed
# - Configuration error
```

**Solution 2: Health Check Failing**
```bash
# Check health check configuration
docker compose config | grep -A 10 healthcheck

# Test health check manually
docker compose exec backend curl http://localhost:8000/api/health

# Adjust health check if too strict
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 30s    # Was 10s
  timeout: 10s     # Was 5s
  retries: 3       # Was 5
```

**Solution 3: Resource Exhaustion**
```bash
# Check container stats
docker stats

# Increase limits
# See "Container Won't Start > Solution 4"
```

---

## 🖥️ Bare-Metal (systemd) Deployment Issues

### Issue: Service Fails to Start

**Symptoms**:
```
systemctl status shows "failed"
journalctl shows error
```

**Diagnosis**:
```bash
# Check service status
systemctl status sattva-streamer.service

# Check detailed logs
journalctl -u sattva-streamer -n 100 --no-pager

# Check service file
systemctl cat sattva-streamer.service
```

**Solutions**:

**Solution 1: Missing Executable**
```bash
# Verify Python/Node executables exist
which python3
which node

# Update paths in service file
ExecStart=/usr/bin/python3 /opt/tg_video_streamer/backend/run.py
```

**Solution 2: Wrong Working Directory**
```bash
# Check WorkingDirectory in service file
grep WorkingDirectory /etc/systemd/system/sattva-streamer.service

# Update to correct path
WorkingDirectory=/opt/tg_video_streamer/backend
```

**Solution 3: Environment Variables Not Loaded**
```bash
# Check if EnvironmentFile is specified
grep EnvironmentFile /etc/systemd/system/sattva-streamer.service

# Ensure .env exists at path
ls -la /opt/tg_video_streamer/.env

# Add EnvironmentFile if missing
[Service]
EnvironmentFile=/opt/tg_video_streamer/.env
```

**Solution 4: Permission Issues**
```bash
# Check file ownership
ls -la /opt/tg_video_streamer/

# Fix ownership
sudo chown -R sattva:sattva /opt/tg_video_streamer/

# Fix permissions
sudo chmod -R 755 /opt/tg_video_streamer/
```

---

### Issue: Service Starts But Stops Immediately

**Symptoms**:
```
systemctl status shows "Active: inactive (dead)"
```

**Diagnosis**:
```bash
# Enable service for auto-start
systemctl enable sattva-streamer.service

# Check if service is enabled
systemctl is-enabled sattva-streamer.service

# Check for Type=oneshot (runs once and exits)
grep Type /etc/systemd/system/sattva-streamer.service
```

**Solutions**:

**Solution 1: Change Service Type**
```bash
# Edit service file
sudo nano /etc/systemd/system/sattva-streamer.service

# Change Type to simple or forking
[Service]
Type=simple  # Not oneshot

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl restart sattva-streamer
```

**Solution 2: Add Restart Policy**
```bash
# Add restart configuration to service file
[Service]
Restart=always
RestartSec=10
```

---

## 💾 Database Connectivity

### Issue: "Database Connection Refused"

**Symptoms**:
```
psycopg2.OperationalError: could not connect to server
Connection refused
```

**Diagnosis**:
```bash
# Check if PostgreSQL is running
docker compose ps db
# OR
systemctl status postgresql

# Check PostgreSQL logs
docker compose logs db
# OR
tail -f /var/log/postgresql/postgresql-*.log

# Test connection
psql -h localhost -U postgres -d tg_video_streamer
```

**Solutions**:

**Solution 1: PostgreSQL Not Running**
```bash
# Start PostgreSQL
docker compose up -d db
# OR
sudo systemctl start postgresql

# Verify it's running
docker compose ps db
# OR
systemctl status postgresql
```

**Solution 2: Wrong Connection String**
```bash
# Check DATABASE_URL in .env
grep DATABASE_URL .env

# Correct format:
# Docker: postgresql://postgres:password@db:5432/tg_video_streamer
# Bare-metal: postgresql://postgres:password@localhost:5432/tg_video_streamer

# Update .env if wrong
nano .env
```

**Solution 3: Database Not Initialized**
```bash
# Run migrations
cd backend
alembic upgrade head

# Verify tables created
psql -h localhost -U postgres -d tg_video_streamer -c "\dt"
```

**Solution 4: Hostname Resolution (Docker)**
```bash
# Check if backend can reach db container
docker compose exec backend ping -c 3 db

# If fails, check network
docker network inspect tg_video_streamer_default

# Ensure both services on same network
docker compose config | grep -A 5 networks
```

---

### Issue: "Database Locked" or "Connection Pool Exhausted"

**Symptoms**:
```
Error: database is locked
psycopg2.OperationalError: server closed the connection unexpectedly
```

**Diagnosis**:
```bash
# Check active connections
psql -h localhost -U postgres -d tg_video_streamer -c "SELECT count(*) FROM pg_stat_activity;"

# Check max connections setting
psql -h localhost -U postgres -d tg_video_streamer -c "SHOW max_connections;"
```

**Solutions**:

**Solution 1: Increase Connection Pool**
```bash
# In backend config (config.py or .env)
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

**Solution 2: Reduce Connection Usage**
```bash
# Check for connection leaks in application
# Review code to ensure connections are closed

# Use connection pooling decorator
# in backend code
```

**Solution 3: Restart Database**
```bash
# Last resort - restart PostgreSQL
docker compose restart db
# OR
sudo systemctl restart postgresql
```

---

## 🔴 Redis Connectivity

### Issue: "Redis Connection Refused"

**Symptoms**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Diagnosis**:
```bash
# Check if Redis is running
docker compose ps redis
# OR
systemctl status redis

# Test connection
redis-cli -h localhost ping
# Should return: PONG
```

**Solutions**:

**Solution 1: Redis Not Running**
```bash
# Start Redis
docker compose up -d redis
# OR
sudo systemctl start redis
```

**Solution 2: Wrong Connection String**
```bash
# Check REDIS_URL in .env
grep REDIS_URL .env

# Correct format:
# Docker: redis://redis:6379/0
# Bare-metal: redis://localhost:6379/0
```

**Solution 3: Redis Protected Mode**
```bash
# If using bare-metal Redis
redis-cli CONFIG SET protected-mode no

# Or bind to correct interface
# In /etc/redis/redis.conf
bind 127.0.0.1
```

---

## 🏥 Health Check Failures

### Issue: Health Check Returns "Degraded"

**Symptoms**:
```json
{"status": "degraded", "dependencies": [{"name": "redis", "status": "slow"}]}
```

**Diagnosis**:
```bash
# Check which dependency is degraded
curl http://localhost:8000/api/health | jq .

# Check dependency latency
curl http://localhost:8000/api/health | jq '.dependencies[] | select(.status != "up")'
```

**Solutions**:

**Solution 1: Slow Database Queries**
```bash
# Check database query performance
# Enable slow query logging in PostgreSQL

# In postgresql.conf
log_min_duration_statement = 1000  # Log queries > 1s

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check logs
tail -f /var/log/postgresql/postgresql-*.log
```

**Solution 2: High Latency Network**
```bash
# Check latency to dependencies
ping -c 10 db  # Docker
ping -c 10 localhost  # Bare-metal

# Check for network congestion
iftop
```

**Solution 3: Adjust Health Check Thresholds**
```bash
# In health.py (backend)
# Adjust thresholds for degraded status
DEGRADED_THRESHOLD_MS = 500  # Was 200
```

---

### Issue: Health Check Returns "Unhealthy"

**Symptoms**:
```json
{"status": "unhealthy", "dependencies": [{"name": "database", "status": "down"}]}
```

**Diagnosis & Solutions**:

**Follow dependency-specific troubleshooting**:
- **Database down**: See [Database Connectivity](#database-connectivity)
- **Redis down**: See [Redis Connectivity](#redis-connectivity)
- **Streams down**: Check streamer service status

---

## 💾 Backup & Restore Issues

### Issue: Backup Fails - "Permission Denied"

**Symptoms**:
```
Error: Permission denied when writing backup
```

**Diagnosis**:
```bash
# Check backup directory permissions
ls -la /opt/backups/

# Check who runs the backup service
ps aux | grep backup
```

**Solutions**:

**Solution 1: Fix Directory Permissions**
```bash
# Create backup directory with correct permissions
sudo mkdir -p /opt/backups
sudo chown -R sattva:sattva /opt/backups
sudo chmod 755 /opt/backups
```

**Solution 2: Run Backup as Correct User**
```bash
# In systemd service file
[Service]
User=sattva
Group=sattva
```

---

### Issue: Backup Fails - "Database Connection Timeout"

**Symptoms**:
```
Error: Backup failed - database connection timeout
pg_dump: server closed the connection unexpectedly
```

**Diagnosis**:
```bash
# Check if database is under heavy load
psql -h localhost -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Check long-running queries
psql -h localhost -U postgres -c "SELECT pid, query, state FROM pg_stat_activity WHERE state != 'idle';"
```

**Solutions**:

**Solution 1: Run Backup During Low Traffic**
```bash
# Schedule backup for 2-3 AM
# In automated-backup.timer
OnCalendar=*-*-* 02:00:00
```

**Solution 2: Increase Statement Timeout**
```bash
# In backup script
export PGSTATEDOUT=600  # 10 minutes

pg_dump -U postgres -h localhost tg_video_streamer > backup.sql
```

---

### Issue: Restore Fails - "Version Mismatch"

**Symptoms**:
```
Error: Database version mismatch
Restore failed: schema version conflict
```

**Diagnosis**:
```bash
# Check current database version
psql -h localhost -U postgres -c "SELECT version FROM alembic_version;"

# Check backup version
grep "alembic_version" backup.sql
```

**Solutions**:

**Solution 1: Downgrade Database First**
```bash
# Rollback to backup's version
cd backend
alembic downgrade <backup-version>

# Then restore
psql -h localhost -U postgres tg_video_streamer < backup.sql
```

**Solution 2: Upgrade Backup**
```bash
# Restore to temporary database
psql -h localhost -U postgres tg_video_streamer_temp < backup.sql

# Run migrations
cd backend
DATABASE_URL=postgresql://postgres@localhost/tg_video_streamer_temp \
  alembic upgrade head

# Export and import to production
pg_dump -h localhost -U postgres tg_video_streamer_temp > upgraded_backup.sql
psql -h localhost -U postgres tg_video_streamer < upgraded_backup.sql
```

---

## 📊 Monitoring Stack Issues

### Issue: Prometheus Not Scraping Metrics

**Symptoms**:
- Grafana dashboards show "No data"
- Prometheus targets page shows "DOWN"

**Diagnosis**:
```bash
# Check Prometheus is running
curl http://localhost:9090/-/healthy

# Check targets status
# Open: http://localhost:9090/targets

# Check metrics endpoint
curl http://localhost:8000/metrics
```

**Solutions**:

**Solution 1: Metrics Endpoint Not Accessible**
```bash
# Check if /metrics endpoint exists
curl http://localhost:8000/metrics

# If 404, enable Prometheus metrics
# In backend dependencies (requirements.txt)
# prometheus-fastapi-instrumentator==6.0.0

# In backend code (main.py)
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

**Solution 2: Wrong Target Configuration**
```bash
# Check prometheus.yml
scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']  # Docker
      # OR
      - targets: ['localhost:8000']  # Bare-metal

# Reload Prometheus
docker compose restart prometheus
# OR
kill -HUP $(cat /var/run/prometheus.pid)
```

**Solution 3: Network/Firewall Blocking**
```bash
# Check if Prometheus can reach backend
docker compose exec prometheus ping -c 3 backend

# Check firewall
sudo ufw status
sudo iptables -L -n | grep 9090

# Allow Prometheus port
sudo ufw allow 9090
```

---

### Issue: Grafana Dashboards Not Loading

**Symptoms**:
- Grafana shows "Dashboard not found"
- Dashboards not auto-provisioned

**Diagnosis**:
```bash
# Check Grafana logs
docker compose logs grafana | grep -i dashboard

# Check provisioning config
cat config/monitoring/grafana/provisioning/dashboards.yml

# Check dashboard files exist
ls -la config/monitoring/grafana/dashboards/
```

**Solutions**:

**Solution 1: Fix Provisioning Config**
```bash
# Ensure dashboards.yml points to correct path
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards  # Must match volume mount
```

**Solution 2: Check Volume Mount**
```bash
# In docker-compose.yml
services:
  grafana:
    volumes:
      - ./config/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro

# Restart Grafana
docker compose restart grafana
```

**Solution 3: Manually Import Dashboard**
```bash
# Open Grafana: http://localhost:3001

# Go to: Dashboards > Import
# Upload JSON file from: config/monitoring/grafana/dashboards/
```

---

## 🌐 Network & Firewall Issues

### Issue: "Connection Timeout" from External

**Symptoms**:
- Can access locally but not from other machines
- `curl` from remote host times out

**Diagnosis**:
```bash
# Check if listening on all interfaces (0.0.0.0)
netstat -tulpn | grep 8000

# Check firewall
sudo ufw status
sudo iptables -L -n
```

**Solutions**:

**Solution 1: Service Listening on Localhost Only**
```bash
# In .env or config
HOST=0.0.0.0  # Not 127.0.0.1

# Restart service
docker compose restart backend
```

**Solution 2: Firewall Blocking Ports**
```bash
# Allow backend port
sudo ufw allow 8000/tcp

# Allow frontend port
sudo ufw allow 3000/tcp

# Allow Grafana (if needed)
sudo ufw allow 3001/tcp

# Check rules
sudo ufw status numbered
```

**Solution 3: Cloud Provider Security Group**
```bash
# If on AWS/AWS/GCP, check security groups
# Allow inbound TCP on ports:
# - 8000 (backend)
# - 3000 (frontend)
# - 3001 (Grafana)
```

---

### Issue: Nginx Reverse Proxy Errors

**Symptoms**:
```
502 Bad Gateway
504 Gateway Timeout
```

**Diagnosis**:
```bash
# Check Nginx status
systemctl status nginx

# Check Nginx error log
tail -f /var/log/nginx/error.log

# Test upstream directly
curl http://localhost:8000/api/health
```

**Solutions**:

**Solution 1: Backend Not Running**
```bash
# Start backend
docker compose up -d backend
# OR
systemctl start sattva-backend

# Verify
curl http://localhost:8000/api/health
```

**Solution 2: Wrong Upstream Configuration**
```bash
# Check nginx config
grep -A 10 "upstream" /etc/nginx/sites-available/tg_video_streamer

# Should point to correct backend
upstream backend {
    server localhost:8000;  # Docker: 127.0.0.1:8000
    # OR
    server 127.0.0.1:8000;  # Bare-metal
}

# Reload Nginx
sudo nginx -t
sudo systemctl reload nginx
```

**Solution 3: Timeout Too Short**
```bash
# In nginx config
location / {
    proxy_pass http://backend;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
}
```

---

## ⚡ Performance Issues

### Issue: High CPU Usage

**Symptoms**:
- `top` shows 100% CPU
- Services slow to respond

**Diagnosis**:
```bash
# Check CPU usage
docker stats
# OR
top

# Check process count
ps aux | grep python | wc -l

# Check for infinite loops
ps aux | sort -rk 3 | head -10
```

**Solutions**:

**Solution 1: Too Many Worker Processes**
```bash
# In backend config
# Reduce workers
WORKERS=2  # Was 4

# OR set to CPU count
WORKERS=$(nproc)
```

**Solution 2: Inefficient Queries**
```bash
# Enable query logging
# In .env
DATABASE_LOG_QUERIES=true

# Check slow queries
# See "Health Check Failures > Solution 1"
```

**Solution 3: Add CPU Limits**
```bash
# In docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'  # Limit to 2 CPUs
```

---

### Issue: High Memory Usage

**Symptoms**:
- OOM killer killing processes
- Memory usage >90%

**Diagnosis**:
```bash
# Check memory usage
free -h

# Check container memory
docker stats --format "table {{.Name}}\t{{.MemUsage}}"

# Check for memory leaks
# Monitor over time
watch -n 5 'docker stats --no-stream'
```

**Solutions**:

**Solution 1: Memory Leak**
```bash
# Restart service periodically
# In docker-compose.yml
deploy:
  restart_policy:
    condition: on-failure
    max_attempts: 3
```

**Solution 2: Increase Memory Limits**
```bash
# In docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G  # Increase
```

**Solution 3: Optimize Application**
```bash
# Profile memory usage
# In Python
import tracemalloc
tracemalloc.start()

# Check for large objects
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
```

---

### Issue: Disk Space Full

**Symptoms**:
```
Error: No space left on device
```

**Diagnosis**:
```bash
# Check disk usage
df -h

# Check large files
du -sh /var/log/* | sort -rh | head -10

# Check Docker disk usage
docker system df
```

**Solutions**:

**Solution 1: Clean Docker Resources**
```bash
# Remove unused containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Clean everything
docker system prune -a --volumes -f
```

**Solution 2: Rotate Logs**
```bash
# Configure logrotate
sudo nano /etc/logrotate.d/tg_video_streamer

/opt/tg_video_streamer/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

**Solution 3: Clean Backups**
```bash
# Remove old backups
# Keep only last 7 days
find /opt/backups -name "backup_*.sql" -mtime +7 -delete

# Use backup rotation in backup service
# Already implemented with 30-day retention
```

---

## 📺 Stream Quality Issues

### Issue: Stream Buffering/Freezing

**Symptoms**:
- Video stops playing
- "Buffering..." message

**Diagnosis**:
```bash
# Check stream health
curl http://localhost:8000/api/health | jq .stream_details

# Check active streams
curl http://localhost:8000/api/streams

# Check FFmpeg processes
ps aux | grep ffmpeg
```

**Solutions**:

**Solution 1: Insufficient Bandwidth**
```bash
# Check available bandwidth
speedtest-cli

# Check stream bitrate
curl http://localhost:8000/api/streams | jq '.[0].bitrate'

# Reduce stream quality
# In stream configuration
VIDEO_BITRATE=1000  # Reduce from 2000
```

**Solution 2: FFmpeg Issues**
```bash
# Check FFmpeg logs
docker compose logs streamer | grep ffmpeg

# Restart streamer
docker compose restart streamer

# Check FFmpeg installation
ffmpeg -version
```

**Solution 3: Database Slow Queries**
```bash
# Stream metadata queries might be slow
# See "High CPU Usage > Solution 2"
```

---

### Issue: Poor Stream Quality

**Symptoms**:
- Low resolution
- Blurry video

**Diagnosis**:
```bash
# Check stream quality metrics
curl http://localhost:8000/api/admin/stream/quality/current/test | jq .
```

**Solutions**:

**Solution 1: Adjust Quality Settings**
```bash
# In stream configuration
VIDEO_QUALITY=high  # Was medium
VIDEO_RESOLUTION=1280x720  # Was 854x480
VIDEO_BITRATE=2500  # Increase
```

**Solution 2: Check Source Quality**
```bash
# Test source URL
curl -I <source-url>

# Download and test locally
ffmpeg -i <source-url> -f null -
```

---

## 🆘 Getting Help

### Before Asking for Help

1. **Gather Diagnostic Information**:
```bash
# Save diagnostic output
bash scripts/gather-diagnostics.sh > diagnostics.txt

# Or manually collect:
{
  echo "=== System Info ==="
  uname -a
  free -h
  df -h

  echo "=== Docker Status ==="
  docker compose ps

  echo "=== Service Logs ==="
  docker compose logs --tail=100 backend

  echo "=== Health Check ==="
  curl -s http://localhost:8000/api/health | jq .
} > diagnostics.txt
```

2. **Check Recent Changes**:
```bash
# Git log
git log --oneline -10

# Recent config changes
git diff HEAD~1 .env
```

3. **Search Existing Issues**:
- GitHub issues
- Documentation
- This troubleshooting guide

### Reporting Issues

When reporting issues, include:

**Essential Information**:
- Deployment method: Docker or bare-metal
- OS and version
- Error messages (full output)
- Steps to reproduce
- Diagnostic output

**Issue Template**:
```
**Description**: Brief description of the problem

**Deployment Method**: Docker / Bare-metal

**Environment**:
- OS: Ubuntu 22.04
- Python: 3.11
- Docker: 24.0

**Error Message**:
```
Paste error here
```

**Steps to Reproduce**:
1. Run this command
2. Do this
3. See error

**Diagnosis Output**:
```
Paste diagnostics.txt output
```

**What You've Tried**:
- Tried X, didn't work
- Tried Y, didn't work
```

### Community Resources

- **Documentation**: `docs/`
- **GitHub Issues**: [repository-url]/issues
- **Deployment Guide**: `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
- **Deployment Checklist**: `docs/deployment/DEPLOYMENT_CHECKLIST.md`

### Emergency Recovery

If everything fails and system is down:

```bash
# 1. Stop all services
docker compose down
# OR
sudo systemctl stop sattva-*

# 2. Restore from last known good backup
# See: docs/deployment/BACKUP_RESTORE.md

# 3. Restart services
docker compose up -d
# OR
sudo systemctl start sattva-*

# 4. Verify health
curl http://localhost:8000/api/health
```

---

## 📞 Support Contacts

| Issue Type | Contact | Response Time |
|------------|---------|---------------|
| Critical (system down) | on-call | < 1 hour |
| High (degraded service) | Slack #support | < 4 hours |
| Medium (non-blocking) | GitHub Issues | < 24 hours |
| Low (documentation) | GitHub Issues | < 1 week |

---

**Troubleshooting Guide Version**: 1.0
**Created**: January 24, 2026
**Related**: [PRODUCTION_DEPLOYMENT_GUIDE.md](./PRODUCTION_DEPLOYMENT_GUIDE.md) | [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

---

## 🔗 Quick Reference

### Essential Commands

```bash
# Health check
curl http://localhost:8000/api/health | jq .

# Service status
docker compose ps
systemctl status sattva-streamer

# Logs
docker compose logs -f backend
journalctl -u sattva-streamer -f

# Restart
docker compose restart backend
systemctl restart sattva-streamer

# Database
psql -h localhost -U postgres -d tg_video_streamer

# Backup
pg_dump -U postgres -h localhost tg_video_streamer > backup.sql

# Restore
psql -h localhost -U postgres tg_video_streamer < backup.sql
```

### Common Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| Frontend | 3000 | http://localhost:3000 |
| Grafana | 3001 | http://localhost:3001 |
| Prometheus | 9090 | http://localhost:9090 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |

---

**End of Troubleshooting Guide**
