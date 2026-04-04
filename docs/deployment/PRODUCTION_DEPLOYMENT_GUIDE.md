# Production Deployment Guide

**Last Updated**: January 24, 2026
**Status**: ✅ Production Ready
**Deployment Time**: 5-10 minutes
**Supported Environments**: Docker, Bare-metal (systemd)

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Pre-flight Validation](#pre-flight-validation)
4. [Secrets Management](#secrets-management)
5. [Deployment Methods](#deployment-methods)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Health Monitoring](#health-monitoring)
8. [Backup Configuration](#backup-configuration)
9. [Maintenance Operations](#maintenance-operations)
10. [Troubleshooting](#troubleshooting)
11. [Rollback Procedures](#rollback-procedures)

---

## 🚀 Quick Start

### One-Command Deployment (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd <project-directory>

# Run installation wizard
bash scripts/install.sh

# Deploy (auto-detects Docker vs bare-metal)
bash scripts/deploy-unified.sh
```

**Estimated Time**: 5-10 minutes

### Quick Verification

```bash
# Check health endpoint
curl http://localhost:8000/api/health

# Check monitoring dashboards
# Open browser: http://localhost:3001
```

---

## ✅ Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Disk | 20 GB | 50+ GB SSD |
| OS | Linux (Ubuntu 20.04+, Debian 11+) | Ubuntu 22.04 LTS |

### Software Requirements

#### For Docker Deployment (Recommended)
```bash
# Docker 20.10+
docker --version

# Docker Compose v2 (plugin) or v1.29+
docker compose version
# OR
docker-compose --version
```

#### For Bare-Metal Deployment
```bash
# Python 3.11+
python3 --version

# systemd (init system)
systemctl --version

# PostgreSQL client
psql --version

# Redis client
redis-cli --version
```

### Network Requirements

- **Ports**: 8000 (backend), 3000 (frontend), 3001 (Grafana), 9090 (Prometheus)
- **Outbound**: Internet access for package installation
- **Inbound**: Configure firewall for required ports

---

## 🔍 Pre-Flight Validation

### Run All Checks

```bash
# Validate secrets, Docker, and dependencies
bash scripts/preflight-env.sh --check-all

# Expected output: All checks passed ✅
```

### Individual Checks

#### 1. Secrets Validation
```bash
bash scripts/preflight-env.sh

# Checks:
# ✓ sops command available
# ✓ age command available
# ✓ .env.enc file exists
# ✓ age key available
# ✓ .env.enc decrypts successfully
```

#### 2. Docker Validation
```bash
bash scripts/preflight-env.sh --check-docker

# Checks:
# ✓ docker command available
# ✓ docker daemon running
# ✓ docker compose available
```

#### 3. Dependencies Validation
```bash
bash scripts/preflight-env.sh --check-deps

# Checks:
# ✓ PostgreSQL client (psql)
# ✓ Redis client (redis-cli)
# ✓ FFmpeg
```

### Troubleshooting Pre-Flight Failures

| Issue | Solution |
|-------|----------|
| `sops: command not found` | Install: `pip install sops` or `brew install sops` |
| `age: command not found` | Install: `https://github.com/FiloSottile/age` |
| `.env.enc not found` | Run: `./scripts/encrypt-secrets.sh .env.master` |
| `docker daemon not running` | Start: `sudo systemctl start docker` |
| `psql: command not found` | Install: `sudo apt-get install postgresql-client` |

---

## 🔐 Secrets Management

### Initial Setup (One-Time)

#### 1. Generate Age Key

```bash
# Generate age key pair
age-keygen -o .internal/age.key

# Keep private key secure! ⚠️
# Public key is in .internal/age.key (line starting with #)
```

#### 2. Encrypt Environment Variables

```bash
# Create master environment file
cat > .env.master <<EOF
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=tg_video_streamer

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys (example)
TELEGRAM_BOT_TOKEN=your_bot_token
EOF

# Encrypt with SOPS
SOPS_AGE_KEY_FILE=.internal/age.key ./scripts/encrypt-secrets.sh .env.master

# Result: .env.enc created ✅
# Delete .env.master after verification!
```

#### 3. Deploy Encrypted Secrets

```bash
# Local deployment (automatic decrypt on deploy)
bash scripts/deploy-unified.sh

# Remote deployment: copy age key first
scp -i ~/.ssh/id_rsa .internal/age.key root@server:/opt/app/.age.key
ssh root@server "chmod 600 /opt/app/.age.key"
```

### Decrypting Secrets

```bash
# Manual decrypt (for debugging)
SOPS_AGE_KEY_FILE=.internal/age.key sops --decrypt --input-type dotenv --output-type dotenv .env.enc > .env

# Automatic decrypt (used by deployment scripts)
./scripts/decrypt-secrets.sh --force
```

### Best Practices

- ✅ **DO**: Commit `.env.enc` to git
- ❌ **DON'T**: Commit `.env.master` or `.env` to git
- ✅ **DO**: Store age key in secure location (password manager)
- ✅ **DO**: Use different keys for dev/staging/production
- ✅ **DO**: Rotate secrets periodically

---

## 🚢 Deployment Methods

### Method 1: Docker Deployment (Recommended)

#### Advantages
- ✅ Isolated environment
- ✅ Easy rollback
- ✅ Reproducible builds
- ✅ Resource limits

#### Steps

```bash
# 1. Validate configuration
bash scripts/deploy-unified.sh --validate

# 2. Deploy with auto-detection
bash scripts/deploy-unified.sh

# OR force Docker mode
bash scripts/deploy-unified.sh --docker
```

#### What Happens
1. Validates Docker daemon and compose
2. Decrypts secrets (.env.enc → .env)
3. Builds Docker images (if needed)
4. Starts all services (backend, frontend, db, redis, monitoring)
5. Waits for health checks
6. Displays service status

#### Verify Deployment
```bash
# Check all services running
docker compose ps

# Expected output:
# NAME                 STATUS              PORTS
# backend              Up (healthy)        0.0.0.0:8000->8000
# frontend             Up                  0.0.0.0:3000->3000
# db                   Up (healthy)        5432
# redis                Up (healthy)        6379
# prometheus           Up                  0.0.0.0:9090->9090
# grafana              Up                  0.0.0.0:3001->3001
```

---

### Method 2: Bare-Metal Deployment (systemd)

#### Advantages
- ✅ Native performance
- ✅ No Docker overhead
- ✅ System-level integration
- ✅ Familiar for sysadmins

#### Prerequisites
- Python 3.11+ installed
- systemd init system
- PostgreSQL and Redis running (or managed externally)

#### Steps

```bash
# 1. Install dependencies
bash scripts/install.sh --bare-metal

# 2. Deploy with bare-metal mode
bash scripts/deploy-unified.sh --bare-metal

# 3. Enable and start services
sudo systemctl enable sattva-streamer
sudo systemctl start sattva-streamer
sudo systemctl enable automated-backup
sudo systemctl start automated-backup
```

#### What Happens
1. Validates Python and systemd
2. Creates Python virtual environment
3. Installs dependencies from requirements.txt
4. Decrypts secrets
5. Creates systemd service files
6. Enables and starts services

#### Verify Deployment
```bash
# Check service status
sudo systemctl status sattva-streamer

# Check logs
sudo journalctl -u sattva-streamer -f

# Check process
ps aux | grep streamer
```

---

### Method 3: Remote Deployment

#### Deploy to Remote Server via SSH

```bash
# Set environment variables
export REMOTE_USER=root
export REMOTE_HOST=192.168.1.100
export SSH_KEY=~/.ssh/id_rsa

# Deploy remotely
bash scripts/deploy-unified.sh --remote $REMOTE_HOST
```

#### What Happens
1. Creates deployment archive (tar.gz)
2. Transfers archive via SSH/SCP
3. Extracts on remote server
4. Auto-detects environment (Docker vs bare-metal)
5. Executes deployment
6. Reports status

---

## ✅ Post-Deployment Verification

### 1. Health Endpoint Check

```bash
# Should return 200 with detailed status
curl http://localhost:8000/api/health | jq .

# Expected output:
{
  "status": "healthy",
  "timestamp": "2026-01-24T10:00:00Z",
  "dependencies": [
    {
      "name": "database",
      "status": "up",
      "latency_ms": 2
    },
    {
      "name": "redis",
      "status": "up",
      "latency_ms": 1
    }
  ],
  "stream_details": {
    "total_streams": 5,
    "active_streams": 3,
    "healthy_streams": 3,
    "unhealthy_streams": 0
  },
  "system_metrics": {
    "cpu_percent": 15.2,
    "memory_percent": 45.3,
    "memory_used_mb": 724,
    "memory_total_mb": 16000
  }
}
```

### 2. Readiness Probe Check

```bash
# For Kubernetes/container orchestration
curl http://localhost:8000/api/health/ready

# Expected output:
{
  "status": "ready",
  "reason": "All dependencies healthy"
}
```

### 3. Service Verification

```bash
# Backend API
curl http://localhost:8000/api/v1/streams

# Frontend
# Open browser: http://localhost:3000

# Grafana Dashboards
# Open browser: http://localhost:3001
# Default credentials: admin / admin (change on first login)
```

### 4. Database Migration Check

```bash
# Check Alembic version
cd backend
alembic current

# Expected: Output shows latest revision
```

### 5. Logs Verification

```bash
# Docker logs
docker compose logs --tail=100 -f backend

# Bare-metal logs
sudo journalctl -u sattva-streamer -n 100 -f

# Check for errors
# Expected: No ERROR or CRITICAL messages
```

---

## 📊 Health Monitoring

### Grafana Dashboards

Access dashboards at: http://localhost:3001

#### Available Dashboards

| Dashboard | Purpose | URL |
|-----------|---------|-----|
| **Deployment Health** | System uptime, CPU, memory, HTTP metrics | `/d/deployment-health` |
| **Backend Overview** | API performance, database queries | `/d/backend-overview` |
| **Backup Monitoring** | Backup status, storage usage, retention | `/d/backup-monitoring` |
| **System Advanced** | Detailed system metrics | `/d/system-advanced` |
| **Streamer Overview** | Stream status, listener count | `/d/streamer-overview` |

### Prometheus Metrics

Access Prometheus at: http://localhost:9090

#### Key Metrics

```promql
# System uptime
sattva_app_uptime_seconds

# HTTP request rate
rate(sattva_http_requests_total[5m])

# HTTP error rate
rate(sattva_http_requests_total{status=~"5.."}[5m])

# Active streams
sattva_active_streams

# CPU usage
rate(node_cpu_seconds_total{mode!="idle"}[5m]) * 100

# Memory usage
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100
```

### Alerting

AlertManager is available at: http://localhost:9093

#### Configured Alerts

| Alert | Severity | Trigger |
|-------|----------|---------|
| DeploymentFailed | Critical | Deployment fails to complete |
| DeploymentStuck | Critical | Deployment in progress >15min |
| ServiceDown | Critical | Service unreachable >5min |
| HighMemoryUsage | Warning | Memory >80% for 5min |
| HighCPUUsage | Warning | CPU >80% for 5min |
| BackupFailed | Critical | Backup fails to complete |

---

## 💾 Backup Configuration

### Automated Backups (systemd)

#### Enable Automatic Backups

```bash
# Copy systemd timer file
sudo cp config/systemd/automated-backup.timer /etc/systemd/system/
sudo cp config/systemd/automated-backup.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable timer (runs daily at 02:00 UTC)
sudo systemctl enable automated-backup.timer
sudo systemctl start automated-backup.timer

# Verify schedule
sudo systemctl list-timers | grep automated-backup
```

#### Backup Schedule

- **Frequency**: Daily at 02:00 UTC
- **Retention**: 30 days (configurable)
- **Location**: `/opt/backups/` (configurable)
- **Includes**: Database, configuration files, Redis data

### Manual Backup

#### Trigger Backup via API

```bash
# Trigger immediate backup
curl -X POST http://localhost:8000/api/v1/backup/trigger \
  -H "Content-Type: application/json" \
  -d '{"include_database": true, "include_config": true, "include_redis": true}'

# Response:
{
  "backup_id": "backup_20260124_020000",
  "status": "in_progress",
  "estimated_completion": "2026-01-24T02:05:00Z"
}
```

#### Trigger Backup via Script

```bash
# Run backup script manually
bash scripts/backup-schedule.sh --now

# Dry-run (validate without creating backup)
bash scripts/backup-schedule.sh --dry-run
```

### Restore Procedures

#### Restore Database

```bash
# List available backups
curl http://localhost:8000/api/v1/backup/list

# Restore specific backup
curl -X POST http://localhost:8000/api/v1/backup/restore \
  -H "Content-Type: application/json" \
  -d '{"backup_id": "backup_20260124_020000"}'

# Response:
{
  "status": "success",
  "restored_backup": "backup_20260124_020000",
  "timestamp": "2026-01-24T10:30:00Z"
}
```

#### Manual Restore (PostgreSQL)

```bash
# Stop services
docker compose stop backend

# Restore database
docker compose exec -T db psql -U postgres -d tg_video_streamer < /opt/backups/backup_20260124_020000.sql

# Start services
docker compose start backend
```

### Backup Verification

```bash
# Check backup status
curl http://localhost:8000/api/v1/backup/status

# Check backup files
ls -lah /opt/backups/

# Verify backup integrity
# (Check file size, test restore on staging)
```

---

## 🔧 Maintenance Operations

### Update Application

```bash
# 1. Pull latest code
git pull origin main

# 2. Run pre-flight checks
bash scripts/preflight-env.sh --check-all

# 3. Backup before update
curl -X POST http://localhost:8000/api/v1/backup/trigger

# 4. Deploy update
bash scripts/deploy-unified.sh --docker

# 5. Verify deployment
curl http://localhost:8000/api/health
```

### Database Migrations

```bash
# Navigate to backend directory
cd backend

# Check current version
alembic current

# Upgrade to latest
alembic upgrade head

# Verify tables created
# (connect to database and check schema)
```

### Log Rotation

#### Docker Log Rotation

```bash
# Docker Compose automatically rotates logs
# Configuration in docker-compose.yml:
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-files: "3"

# Manual log cleanup
docker compose logs --tail=0 -f backend  # Clear logs
```

#### Bare-Metal Log Rotation

```bash
# systemd automatically rotates logs via journald
# Configure rotation:
sudo journalctl --vacuum-size=100M
sudo journalctl --vacuum-time=30d
```

### Resource Cleanup

```bash
# Clean Docker resources
docker system prune -a --volumes

# Clean old backups (older than 30 days)
find /opt/backups/ -name "*.sql" -mtime +30 -delete
```

---

## 🚨 Troubleshooting

### Common Issues and Solutions

#### Issue: Deployment Fails - "Port Already in Use"

**Symptoms**:
```
Error: bind: address already in use
```

**Solution**:
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
kill -9 <PID>

# OR change port in .env
PORT=8001
```

---

#### Issue: Health Check Returns "Unhealthy"

**Symptoms**:
```json
{"status": "unhealthy", "dependencies": [{"name": "database", "status": "down"}]}
```

**Solution**:
```bash
# Check database connection
docker compose ps db

# Check database logs
docker compose logs db

# Restart database
docker compose restart db

# Verify connection string in .env
DATABASE_URL=postgresql://user:password@db:5432/dbname
```

---

#### Issue: Secrets Decryption Fails

**Symptoms**:
```
Error: failed to decrypt .env.enc
```

**Solution**:
```bash
# Verify age key exists
ls -la .internal/age.key

# Verify key permissions
chmod 600 .internal/age.key

# Test decryption manually
SOPS_AGE_KEY_FILE=.internal/age.key sops --decrypt .env.enc

# If key lost: regenerate and re-encrypt .env.master
```

---

#### Issue: High Memory Usage

**Symptoms**:
- Grafana shows memory >80%
- Services killed by OOM killer

**Solution**:
```bash
# Check memory usage
docker stats

# Adjust limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G  # Increase if needed

# Restart services
docker compose up -d
```

---

#### Issue: Backup Fails

**Symptoms**:
```
Error: Backup failed - database connection timeout
```

**Solution**:
```bash
# Check database is running
docker compose ps db

# Check backup logs
docker compose logs backend | grep -i backup

# Verify backup directory exists and is writable
ls -la /opt/backups/
sudo chown -R $(whoami):$(whoami) /opt/backups/

# Manually test backup
pg_dump -U postgres -h localhost tg_video_streamer > test.sql
```

---

#### Issue: Monitoring Dashboards Show No Data

**Symptoms**:
- Grafana panels are empty
- "No data" query errors

**Solution**:
```bash
# Check Prometheus is running
curl http://localhost:9090/-/healthy

# Check Prometheus targets
# Open: http://localhost:9090/targets
# All targets should be "UP"

# Check metrics endpoint
curl http://localhost:8000/metrics | head -20

# Restart Prometheus
docker compose restart prometheus
```

### Debug Mode

#### Enable Debug Logging

```bash
# Add to .env
LOG_LEVEL=DEBUG

# Restart services
docker compose restart backend

# View detailed logs
docker compose logs -f backend | grep DEBUG
```

#### Database Connection Debug

```bash
# Test connection
psql -U postgres -h localhost -d tg_video_streamer -c "SELECT 1;"

# Check connection count
psql -U postgres -h localhost -d tg_video_streamer -c "SELECT count(*) FROM pg_stat_activity;"
```

### Emergency Procedures

#### Emergency Stop All Services

```bash
# Docker
docker compose down

# Bare-metal
sudo systemctl stop sattva-streamer automated-backup
```

#### Emergency Rollback

```bash
# 1. Stop services
docker compose down

# 2. Restore previous git commit
git reset --hard HEAD~1

# 3. Restore database backup
psql -U postgres -h localhost tg_video_streamer < backup_pre_deployment.sql

# 4. Restart services
docker compose up -d
```

---

## 🔄 Rollback Procedures

### Automated Rollback

```bash
# Rollback to previous deployment
# (Note: This feature requires deployment tracking)

# 1. List deployments
curl http://localhost:8000/api/v1/deployments

# 2. Rollback to specific version
curl -X POST http://localhost:8000/api/v1/deployments/rollback \
  -H "Content-Type: application/json" \
  -d '{"target_version": "v1.2.3"}'
```

### Manual Rollback

#### Docker Rollback

```bash
# 1. Stop services
docker compose down

# 2. Checkout previous commit
git checkout <previous-commit-hash>

# 3. Restart with previous version
docker compose up -d --build

# 4. Verify
curl http://localhost:8000/api/health
```

#### Database Rollback

```bash
# 1. Navigate to backend
cd backend

# 2. Check current version
alembic current

# 3. Downgrade to previous version
alembic downgrade -1

# 4. Verify tables
alembic history
```

#### Bare-Metal Rollback

```bash
# 1. Stop service
sudo systemctl stop sattva-streamer

# 2. Checkout previous commit
git checkout <previous-commit-hash>

# 3. Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

# 4. Restart service
sudo systemctl start sattva-streamer

# 5. Verify
sudo systemctl status sattva-streamer
```

### Rollback Verification

```bash
# Check version
curl http://localhost:8000/api/v1/version

# Check health
curl http://localhost:8000/api/health

# Check logs
docker compose logs -f backend
# OR
sudo journalctl -u sattva-streamer -f
```

---

## 📞 Support and Resources

### Documentation

- **Main Documentation**: `docs/`
- **Deployment Checklist**: `docs/deployment/DEPLOYMENT_CHECKLIST.md`
- **Troubleshooting Guide**: `docs/deployment/TROUBLESHOOTING.md`
- **Backup/Restore**: `docs/deployment/BACKUP_RESTORE.md`

### Monitoring

- **Grafana Dashboards**: http://localhost:3001
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### Logs

```bash
# Docker logs
docker compose logs -f [service]

# Bare-metal logs
sudo journalctl -u [service] -f

# Backend logs
tail -f backend/logs/*.log
```

### Health Checks

```bash
# Main health endpoint
curl http://localhost:8000/api/health

# Readiness probe
curl http://localhost:8000/api/health/ready

# Metrics endpoint
curl http://localhost:8000/metrics
```

---

## ✅ Deployment Checklist Summary

### Pre-Deployment
- [ ] Pre-flight checks passed
- [ ] Secrets encrypted (.env.enc exists)
- [ ] Age key securely stored
- [ ] Backup created
- [ ] Documentation reviewed

### Deployment
- [ ] Deployment script executed successfully
- [ ] All services started
- [ ] Health checks passing
- [ ] No errors in logs

### Post-Deployment
- [ ] Health endpoint returns 200
- [ ] Grafana dashboards accessible
- [ ] Database migrations applied
- [ ] Automated backups scheduled
- [ ] Monitoring alerts configured

---

## 🎉 Success!

Your deployment is now complete and production-ready!

**What's Next**:
1. Configure monitoring alerts (AlertManager)
2. Set up log aggregation (Loki)
3. Schedule regular maintenance windows
4. Document any custom configurations
5. Train team on deployment procedures

**Need Help?**
- Check troubleshooting section above
- Review logs: `docker compose logs` or `journalctl`
- Check health: `curl http://localhost:8000/api/health`
- Monitor dashboards: http://localhost:3001

---

**Version**: 1.0
**Last Updated**: January 24, 2026
**Maintained By**: DevOps Team
