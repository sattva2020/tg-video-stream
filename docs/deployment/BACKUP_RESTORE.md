# Backup & Restore Procedures

**Last Updated**: January 24, 2026
**Status**: ✅ Production Ready
**Backup Retention**: 30 days
**Automated Backups**: Daily at 02:00 UTC

---

## 📋 Quick Reference

| Task | Command | Time |
|------|---------|------|
| **Manual Backup** | `curl -X POST http://localhost:8000/api/v1/backup/trigger` | 2-5 min |
| **List Backups** | `curl http://localhost:8000/api/v1/backup/list` | < 1 min |
| **Restore Backup** | `curl -X POST http://localhost:8000/api/v1/backup/restore -d '{"backup_id":"..."}'` | 5-10 min |
| **Setup Automated** | `bash scripts/backup-schedule.sh` | 5 min |
| **Check Status** | `systemctl status automated-backup.timer` | < 1 min |

---

## 💾 Backup Overview

### What Gets Backed Up?

1. **PostgreSQL Database**
   - All tables: streams, sessions, quality metrics, alerts
   - Users and authentication data
   - Application settings

2. **Configuration Files**
   - `.env` (decrypted secrets)
   - `docker-compose.yml`
   - `config/` directory
   - Systemd service files

3. **Redis Data**
   - Active stream sessions
   - Cache data
   - Real-time metrics

4. **Application Data**
   - Stream logs
   - Quality history snapshots
   - Alert configurations

### Backup Locations

- **Local**: `./backups/` (default)
- **Format**: `database_YYYYMMDD_HHMMSS.sql.gz`
- **Retention**: 30 days (configurable)
- **Rotation**: Keeps last 10 backups

---

## 🔄 Manual Backup Procedures

### Option 1: API Endpoint (Recommended)

#### Trigger Full Backup
```bash
curl -X POST http://localhost:8000/api/v1/backup/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "include_database": true,
    "include_config": true,
    "include_redis": true
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "backup_id": "database_20260124_020000",
  "files": [
    "backups/database_20260124_020000.sql.gz",
    "backups/config_20260124_020000.tar.gz",
    "backups/redis_20260124_020000.rdb.gz"
  ],
  "size_mb": 145.2,
  "duration_seconds": 23.5
}
```

#### Backup Database Only
```bash
curl -X POST http://localhost:8000/api/v1/backup/trigger \
  -H "Content-Type: application/json" \
  -d '{"include_database": true}'
```

#### Backup Configuration Only
```bash
curl -X POST http://localhost:8000/api/v1/backup/trigger \
  -H "Content-Type: application/json" \
  -d '{"include_config": true}'
```

---

### Option 2: Direct PostgreSQL Backup

```bash
# Set environment variables
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="tg_video_streamer"
export DB_USER="postgres"
export PGPASSWORD="your_password"

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="./backups/manual_db_${TIMESTAMP}.sql.gz"

# Run backup
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME | gzip > $BACKUP_FILE

# Verify backup
ls -lah $BACKUP_FILE

# Expected: File size > 0
```

**Time**: 1-3 minutes (depending on database size)

---

### Option 3: Docker Database Backup

```bash
# Backup PostgreSQL running in Docker
docker exec tg_video_streamer-db-1 pg_dump -U postgres tg_video_streamer | gzip > ./backups/docker_db_$(date +%Y%m%d_%H%M%S).sql.gz

# Verify
ls -lah ./backups/docker_db_*.sql.gz
```

---

### Option 4: Configuration Backup

```bash
# Create configuration archive
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
tar -czf ./backups/config_${TIMESTAMP}.tar.gz \
  .env \
  docker-compose.yml \
  config/ \
  .internal/ \
  scripts/

# List contents
tar -tzf ./backups/config_${TIMESTAMP}.tar.gz
```

---

## 📋 List and Verify Backups

### List All Backups (API)
```bash
curl http://localhost:8000/api/v1/backup/list | jq .
```

**Expected Response:**
```json
{
  "backups": [
    {
      "backup_id": "database_20260124_020000",
      "type": "database",
      "created_at": "2026-01-24T02:00:00Z",
      "size_mb": 125.4,
      "status": "completed"
    },
    {
      "backup_id": "database_20260123_020000",
      "type": "database",
      "created_at": "2026-01-23T02:00:00Z",
      "size_mb": 124.8,
      "status": "completed"
    }
  ],
  "total_count": 8,
  "total_size_mb": 950.2
}
```

---

### List Local Backups
```bash
# List all backups
ls -lah ./backups/

# Sort by date (newest first)
ls -lt ./backups/*.sql.gz | head -10

# Check backup sizes
du -sh ./backups/* | sort -h
```

---

### Verify Backup Integrity

```bash
# Test gzip integrity
gzip -t ./backups/database_20260124_020000.sql.gz

# Check backup file header
zcat ./backups/database_20260124_020000.sql.gz | head -20

# Expected: PostgreSQL dump header
-- PostgreSQL database dump
-- Dumped from database version 15.x
-- Started on 2026-01-24 02:00:00 UTC
```

---

## 🚀 Automated Backup Setup

### Option 1: Systemd Timer (Recommended for Linux)

#### Setup Automated Backup Timer
```bash
# Run the setup script
cd /path/to/project
bash scripts/backup-schedule.sh

# Script will:
# 1. Copy systemd service files
# 2. Enable the timer
# 3. Schedule daily backups at 02:00 UTC
# 4. Configure retention policy
```

#### Verify Timer is Active
```bash
# Check timer status
systemctl status automated-backup.timer

# Expected output:
# ● automated-backup.timer - Automated Backup Service
#    Loaded: loaded (/etc/systemd/system/automated-backup.timer)
#    Active: active (waiting) since ...
```

#### View Next Backup Time
```bash
systemctl list-timers automated-backup.timer

# Expected:
# NEXT                         LEFT          LAST                         PASSED    UNIT                      ACTIVATES
# Thu 2026-01-25 02:00:00 UTC  21h left      Wed 2026-01-24 02:00:00 UTC  3h ago    automated-backup.timer   automated-backup.service
```

#### View Backup Logs
```bash
# View last backup logs
journalctl -u automated-backup.service -n 50

# Follow live logs
journalctl -u automated-backup.service -f

# View backup history
journalctl -u automated-backup.service --since "7 days ago"
```

---

### Option 2: Cron Job (Alternative)

```bash
# Open crontab
crontab -e

# Add daily backup at 02:00 UTC
0 2 * * * cd /opt/tg_video_streamer && /usr/bin/curl -X POST http://localhost:8000/api/v1/backup/trigger -H "Content-Type: application/json" -d '{"include_database":true,"include_config":true,"include_redis":true}' >> /var/log/backup.log 2>&1

# Verify cron job
crontab -l
```

---

### Option 3: Docker Container Cron

```bash
# Add to docker-compose.yml
services:
  backup:
    image: alpine:latest
    container_name: tg_video_streamer-backup
    volumes:
      - ./scripts:/scripts
      - ./backups:/backups
      - /var/run/docker.sock:/var/run/docker.sock
    command: /bin/sh -c 'crond -f -l 2'
    restart: unless-stopped
```

---

## 📥 Restore Procedures

### ⚠️ Pre-Restore Checklist

- [ ] **Stop all services** to prevent data conflicts
- [ ] **Verify backup file** exists and is not corrupted
- [ ] **Check available disk space** (2x backup size minimum)
- [ ] **Notify users** of scheduled downtime
- [ ] **Have rollback plan** ready if restore fails

---

### Restore Full Backup (API)

#### Step 1: Stop Services
```bash
# Docker deployment
docker compose stop backend frontend streamer

# Bare-metal (systemd)
sudo systemctl stop tg-video-streamer-backend
sudo systemctl stop tg-video-streamer-streamer
```

#### Step 2: Trigger Restore
```bash
curl -X POST http://localhost:8000/api/v1/backup/restore \
  -H "Content-Type: application/json" \
  -d '{
    "backup_id": "database_20260124_020000",
    "components": ["database", "config", "redis"]
  }'
```

**Expected Response:**
```json
{
  "status": "in_progress",
  "restore_id": "restore_20260124_150000",
  "backup_id": "database_20260124_020000",
  "estimated_time_seconds": 300
}
```

#### Step 3: Monitor Restore Progress
```bash
curl http://localhost:8000/api/v1/backup/restore/restore_20260124_150000/status
```

#### Step 4: Start Services
```bash
# Docker deployment
docker compose start backend frontend streamer

# Bare-metal (systemd)
sudo systemctl start tg-video-streamer-backend
sudo systemctl start tg-video-streamer-streamer
```

#### Step 5: Verify Restore
```bash
# Check backend health
curl http://localhost:8000/api/health

# Verify database
psql -U postgres -d tg_video_streamer -c "SELECT COUNT(*) FROM streams;"

# Check logs
docker compose logs --tail=50 backend
```

---

### Restore Database Only (Manual)

```bash
# Set environment variables
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="tg_video_streamer"
export DB_USER="postgres"
export PGPASSWORD="your_password"
BACKUP_FILE="./backups/database_20260124_020000.sql.gz"

# 1. Drop existing database (CAUTION!)
psql -h $DB_HOST -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -h $DB_HOST -U $DB_USER -c "CREATE DATABASE $DB_NAME;"

# 2. Restore from backup
gunzip -c $BACKUP_FILE | psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# 3. Verify restore
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\dt"

# Expected: List of all tables
```

**Time**: 5-15 minutes (depending on database size)

---

### Restore Docker Database

```bash
# Stop database container
docker stop tg_video_streamer-db-1

# Remove volume (WARNING: Deletes all data!)
docker volume rm tg_video_streamer_pgdata

# Recreate volume
docker volume create tg_video_streamer_pgdata

# Start database container
docker start tg_video_streamer-db-1

# Wait for database to be ready (10-20 seconds)
sleep 20

# Restore backup
gunzip -c ./backups/database_20260124_020000.sql.gz | \
  docker exec -i tg_video_streamer-db-1 psql -U postgres -d tg_video_streamer

# Verify
docker exec -it tg_video_streamer-db-1 psql -U postgres -d tg_video_streamer -c "\dt"
```

---

### Restore Configuration Files

```bash
# Extract configuration backup
tar -xzf ./backups/config_20260124_020000.tar.gz -C /

# This restores:
# - .env
# - docker-compose.yml
# - config/
# - .internal/

# Verify files
ls -la .env
cat docker-compose.yml
```

---

### Restore Redis Data

```bash
# Stop Redis
docker stop tg_video_streamer-redis-1

# Copy backup to Redis data directory
cp ./backups/redis_20260124_020000.rdb.gz /var/lib/redis/
gunzip /var/lib/redis/redis_20260124_020000.rdb.gz
mv /var/lib/redis/redis_20260124_020000.rdb /var/lib/redis/dump.rdb

# Start Redis
docker start tg_video_streamer-redis-1

# Verify
redis-cli ping
# Expected: PONG
```

---

## 🚨 Disaster Recovery

### Complete System Recovery

#### Scenario: Server Disk Failure

**Prerequisites:**
- Fresh server with same OS
- Backup files available (local or cloud)
- PostgreSQL, Redis, Docker installed

**Steps:**

1. **Install Dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install -y postgresql redis-server docker.io docker-compose

   # Verify versions
   psql --version    # Should be 15.x
   redis-cli --version
   docker --version
   ```

2. **Restore Configuration**
   ```bash
   # Create project directory
   mkdir -p /opt/tg_video_streamer
   cd /opt/tg_video_streamer

   # Copy configuration backup
   scp user@backup-server:/backups/config_20260124_020000.tar.gz .

   # Extract
   tar -xzf config_20260124_020000.tar.gz

   # Setup environment
   export SOPS_AGE_KEY_FILE=/opt/tg_video_streamer/.age.key
   SOPS_AGE_KEY_FILE=/opt/tg_video_streamer/.age.key ./scripts/decrypt-secrets.sh
   ```

3. **Restore Database**
   ```bash
   # Start database
   docker compose up -d db

   # Wait for ready
   sleep 20

   # Restore from backup
   gunzip -c ./backups/database_20260124_020000.sql.gz | \
     docker exec -i tg_video_streamer-db-1 psql -U postgres -d tg_video_streamer
   ```

4. **Start All Services**
   ```bash
   docker compose up -d

   # Verify all services running
   docker compose ps

   # Check health
   curl http://localhost:8000/api/health
   ```

**Time**: 30-60 minutes

---

#### Scenario: Database Corruption

**Detection:**
```bash
# Check database logs
docker logs tg_video_streamer-db-1 | grep -i error

# Test connection
psql -U postgres -d tg_video_streamer -c "SELECT 1;"
# Expected: ERROR: relation "xxx" does not exist
```

**Recovery:**
```bash
# 1. Stop backend to prevent writes
docker compose stop backend

# 2. Identify last good backup
ls -lt ./backups/database_*.sql.gz | head -5

# 3. Restore database (see "Restore Database Only" above)

# 4. Start backend
docker compose start backend

# 5. Verify
curl http://localhost:8000/api/health
```

---

#### Scenario: Accidental Data Deletion

**Recovery Options:**

1. **Point-in-Time Recovery (if WAL archives enabled)**
   ```bash
   # This requires WAL archiving to be configured
   # See PostgreSQL documentation for setup
   ```

2. **Restore from Latest Backup**
   ```bash
   # Follow database restore procedures
   # Data since last backup will be lost
   ```

3. **Partial Table Restore**
   ```bash
   # Extract specific table from backup
   gunzip -c ./backups/database_20260124_020000.sql.gz | \
     grep -A 1000 "COPY TABLE public.streams" | \
     psql -U postgres -d tg_video_streamer
   ```

---

## 🧪 Backup Testing & Validation

### Monthly Backup Verification

```bash
#!/bin/bash
# Monthly backup validation script

# 1. Create test backup
echo "Creating test backup..."
curl -X POST http://localhost:8000/api/v1/backup/trigger \
  -H "Content-Type: application/json" \
  -d '{"include_database":true}' > /tmp/backup_test.json

BACKUP_ID=$(jq -r '.backup_id' /tmp/backup_test.json)
echo "Backup created: $BACKUP_ID"

# 2. Verify backup file exists
if [ -f "./backups/${BACKUP_ID}.sql.gz" ]; then
  echo "✓ Backup file exists"
else
  echo "✗ Backup file missing!"
  exit 1
fi

# 3. Test gzip integrity
if gzip -t "./backups/${BACKUP_ID}.sql.gz"; then
  echo "✓ Backup file integrity OK"
else
  echo "✗ Backup file corrupted!"
  exit 1
fi

# 4. Test restore to temp database
echo "Testing restore..."
createdb -U postgres test_restore 2>/dev/null || true
gunzip -c "./backups/${BACKUP_ID}.sql.gz" | psql -U postgres -d test_restore > /dev/null

if [ $? -eq 0 ]; then
  echo "✓ Restore test successful"
  dropdb -U postgres test_restore
else
  echo "✗ Restore test failed!"
  exit 1
fi

echo "✅ All backup tests passed!"
```

**Run Monthly:**
```bash
# Add to crontab
0 0 1 * * /path/to/backup-validation-test.sh
```

---

## 🔍 Troubleshooting

### Issue: Backup Fails with "Out of Disk Space"

**Symptoms:**
```json
{
  "status": "failed",
  "error": "No space left on device"
}
```

**Diagnosis:**
```bash
# Check disk space
df -h

# Check backup directory size
du -sh ./backups/

# List old backups
ls -lh ./backups/*.sql.gz
```

**Solution:**
```bash
# 1. Clean old backups manually
find ./backups/ -name "*.sql.gz" -mtime +30 -delete

# 2. Or use API cleanup
curl -X POST http://localhost:8000/api/v1/backup/cleanup \
  -H "Content-Type: application/json" \
  -d '{"retention_days": 30}'

# 3. Verify space available
df -h
```

---

### Issue: Restore Fails with "Version Mismatch"

**Symptoms:**
```
ERROR: could not load version "15.x"
```

**Solution:**
```bash
# 1. Check PostgreSQL versions
psql --version

# 2. If versions differ, use pg_upgrade
# Or manually migrate schema

# 3. For minor version differences, try:
pg_restore --if-exists -d tg_video_streamer backup.dump
```

---

### Issue: Automated Backup Not Running

**Diagnosis:**
```bash
# Check timer status
systemctl status automated-backup.timer

# Check last run
systemctl list-timers automated-backup.timer

# Check service logs
journalctl -u automated-backup.service -n 50
```

**Solution:**
```bash
# 1. Restart timer
sudo systemctl restart automated-backup.timer

# 2. Verify timer is enabled
sudo systemctl enable automated-backup.timer

# 3. Manually trigger to test
sudo systemctl start automated-backup.service

# 4. Check logs
journalctl -u automated-backup.service -f
```

---

### Issue: Backup File is Corrupted

**Diagnosis:**
```bash
gzip -t ./backups/database_20260124_020000.sql.gz
# Output: gzip: ./backups/...: unexpected end of file
```

**Solution:**
```bash
# 1. Try to recover partial data
gunzip -c ./backups/database_20260124_020000.sql.gz > /tmp/partial.sql

# 2. Check if SQL is valid
head -100 /tmp/partial.sql

# 3. If header is OK, try restore
psql -U postgres -d tg_video_streamer < /tmp/partial.sql

# 4. If corrupted, use previous backup
gunzip -c ./backups/database_20260123_020000.sql.gz | psql -U postgres -d tg_video_streamer
```

---

## 📊 Backup Monitoring

### Grafana Dashboard

Access: `http://localhost:3001/d/backup-monitoring`

**Metrics Tracked:**
- Last backup status (Success/Failed/Pending)
- Total backups count
- Storage usage (MB)
- Backup duration trends
- Success rate (%)
- Restore operations

**Alerts Configured:**
- **Critical**: Backup failed
- **Warning**: Backup storage > 5GB
- **Warning**: Backup success rate < 95%

---

### Prometheus Metrics

```bash
# Query backup metrics
curl http://localhost:9090/api/v1/query?query=sattva_backup_last_status

# Query backup count
curl http://localhost:9090/api/v1/query?query=sattva_backup_count

# Query backup size
curl http://localhost:9090/api/v1/query?query=sattva_backup_storage_bytes
```

---

## 🎯 Best Practices

### Backup Frequency

| Environment | Frequency | Retention |
|-------------|-----------|-----------|
| **Production** | Daily | 30 days |
| **Staging** | Weekly | 14 days |
| **Development** | On-demand | 7 days |

### Backup Storage

```bash
# Local storage (default)
BACKUP_DIR="./backups"

# Remote storage (optional)
# Configure S3 in .env:
AWS_S3_BUCKET="s3://my-backups/tg-video-streamer"
AWS_ACCESS_KEY_ID="..."
AWS_SECRET_ACCESS_KEY="..."
```

### Backup Security

```bash
# Encrypt backups before offsite storage
gpg --encrypt --recipient admin@example.com ./backups/database_20260124_020000.sql.gz

# Upload to remote
scp ./backups/database_20260124_020000.sql.gz.gpg user@backup-server:/backups/

# Decrypt when needed
gpg --decrypt ./backups/database_20260124_020000.sql.gz.gpg | gunzip | psql -U postgres -d tg_video_streamer
```

### Pre-Deployment Backup

```bash
# ALWAYS backup before deployment
./scripts/backup-schedule.sh --pre-deploy

# Or via API:
curl -X POST http://localhost:8000/api/v1/backup/trigger \
  -H "Content-Type: application/json" \
  -d '{"tags": ["pre-deployment", "$(git rev-parse --short HEAD)"]}'
```

---

## 📅 Maintenance Schedule

### Daily (Automated)
- ✅ Automated backup runs at 02:00 UTC
- ✅ Old backups cleaned up (retention policy)
- ✅ Backup status logged to systemd journal

### Weekly (Manual)
- [ ] Check backup logs: `journalctl -u automated-backup.service --since "7 days ago"`
- [ ] Verify backup count: `ls ./backups/*.sql.gz | wc -l`
- [ ] Check storage usage: `du -sh ./backups/`

### Monthly (Manual)
- [ ] Run backup validation test (see above)
- [ ] Test restore procedure in staging environment
- [ ] Review Grafana dashboard for trends
- [ ] Update this document if procedures change

### Quarterly (Manual)
- [ ] Review retention policy (adjust if needed)
- [ ] Test disaster recovery procedure
- [ ] Audit backup security (encryption, access controls)
- [ ] Verify offsite backup copies (if configured)

---

## 📞 Support & Resources

**During Backup/Restore Issues:**
- Backend logs: `docker logs tg_video_streamer-backend-1`
- Systemd logs: `journalctl -u automated-backup.service -f`
- PostgreSQL logs: `docker logs tg_video_streamer-db-1`

**Related Documentation:**
- Production Deployment Guide: `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
- Troubleshooting Guide: `docs/deployment/TROUBLESHOOTING.md`
- Deployment Checklist: `docs/deployment/DEPLOYMENT_CHECKLIST.md`

**Getting Help:**
1. Check logs (above)
2. Review troubleshooting section
3. Consult TROUBLESHOOTING.md
4. Create GitHub issue with logs attached

---

## ✅ Backup Verification Checklist

Use this checklist after every restore operation:

- [ ] **Database restored successfully**
  ```bash
  psql -U postgres -d tg_video_streamer -c "SELECT COUNT(*) FROM streams;"
  # Expected: Number > 0
  ```

- [ ] **Configuration files present**
  ```bash
  ls -la .env docker-compose.yml config/
  # Expected: All files exist
  ```

- [ ] **Services start without errors**
  ```bash
  docker compose ps
  # Expected: All services "Up" or "running"
  ```

- [ ] **Backend health check passes**
  ```bash
  curl http://localhost:8000/api/health
  # Expected: 200 OK with status: "healthy"
  ```

- [ ] **No errors in logs**
  ```bash
  docker compose logs --tail=50 backend | grep -i error
  # Expected: No output
  ```

- [ ] **Test stream playback**
  ```bash
  # Try accessing a stream URL
  curl -I http://localhost:8000/stream/test
  # Expected: 200 OK
  ```

- [ ] **Metrics available in Grafana**
  ```bash
  curl http://localhost:3001/api/health
  # Expected: 200 OK
  ```

---

**Document Version**: 1.0
**Created**: January 24, 2026
**Last Updated**: January 24, 2026
**Status**: ✅ Production Ready
**Maintained By**: DevOps Team
