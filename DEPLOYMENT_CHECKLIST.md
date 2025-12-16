# Feature 022 Phase 3: Deployment Checklist

**Date**: December 16, 2025  
**Feature**: Feature 022 Phase 3 (Advanced Stream Quality Monitoring)  
**Status**: ✅ Ready for Deployment  
**Estimated Time**: 30-45 minutes

---

## ✅ Pre-Deployment (10 minutes)

### Code Review
- [ ] Read: `PHASE3_QUICK_START.md` (executive summary)
- [ ] Review: Backend service layer in IDE
- [ ] Review: Frontend components in IDE
- [ ] Verify: All files created in correct locations

**Time**: ~10 minutes

---

## ✅ Local Testing (10 minutes)

### Backend Tests
```bash
cd backend
pytest tests/api/test_quality_trends.py -v
# Expected: 30+ tests passing ✅
```

### Frontend Tests (Optional - if vitest configured)
```bash
cd frontend
npm test StreamQualityPhase3.test.tsx
# Expected: 45+ tests passing ✅
```

### Validation Script
```bash
cd /path/to/project
chmod +x validate-phase3.sh
./validate-phase3.sh
# Expected: All checks passing ✅
```

**Time**: ~10 minutes

---

## ✅ Database Backup (5 minutes)

**Before running migration:**

```bash
# MySQL
mysqldump -u root -p your_database > backup_phase3_$(date +%Y%m%d_%H%M%S).sql

# PostgreSQL
pg_dump your_database > backup_phase3_$(date +%Y%m%d_%H%M%S).sql

# Verify backup created
ls -lah backup_phase3_*
```

**Time**: ~5 minutes

---

## ✅ Database Migration (5 minutes)

### 1. Navigate to Backend
```bash
cd /app/backend
# or wherever your backend is located
```

### 2. Run Alembic Upgrade
```bash
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume utf8 character set.
INFO  [alembic.runtime.migration] Running upgrade  -> 22_phase3_stream_quality_history
INFO  [alembic.runtime.migration] New tables created
```

### 3. Verify Tables Created
```bash
# MySQL
mysql -u root -p your_database -e "SHOW TABLES LIKE 'stream_quality%';"

# Expected output:
# stream_quality_history
# quality_alert_configs
# quality_trend_snapshots
```

**Time**: ~5 minutes

---

## ✅ Service Deployment (5 minutes)

### Option A: Docker Compose
```bash
# Restart backend
docker compose up -d backend

# Restart frontend
docker compose up -d frontend

# Check status
docker compose ps
```

### Option B: Manual Restart
```bash
# Kill existing processes
pkill -f "python.*run.py"
pkill -f "npm.*dev"

# Start backend
cd backend && python run.py &

# Start frontend
cd frontend && npm run dev &
```

**Time**: ~5 minutes

---

## ✅ Service Verification (5 minutes)

### Backend Health Check
```bash
# Should return 200 with health info
curl http://localhost:8000/api/admin/health
```

### API Endpoints Check
```bash
# Test trend endpoint
curl http://localhost:8000/api/admin/stream/quality/trend/test?hours=24

# Test alert config endpoint
curl http://localhost:8000/api/admin/stream/quality/alert/config/test
```

### Check Logs
```bash
# Backend logs
tail -f backend/logs/*.log
# Should show: No errors, service started successfully

# Frontend console
# Open browser DevTools (F12)
# Check Console tab: No red errors
```

**Time**: ~5 minutes

---

## ✅ UI/UX Verification (5 minutes)

### Navigate to Admin Dashboard
1. Open: http://localhost:3000/admin
2. Click: **Metrics** (or your metrics page URL)

### Verify 3 Tabs Visible
- [ ] Tab 1: "Current Quality (Phase 2)" — Should show real-time badge
- [ ] Tab 2: "Trend Analysis (Phase 3)" — Should show trend chart placeholder
- [ ] Tab 3: "Alert Settings (Phase 3)" — Should show alert form

### Click Each Tab
1. Click "Trend Analysis" → Should load without errors
2. Click "Alert Settings" → Should show form
3. Click "Current Quality" → Should show Phase 2 badge

### Check for Errors
- [ ] No red errors in browser console (F12)
- [ ] No errors in backend logs
- [ ] All tabs clickable and responsive

**Time**: ~5 minutes

---

## ✅ Browser Testing (5 minutes)

### Test Trend Analysis Tab
```
Expected:
- Loading spinner visible (optional, depends on data)
- Statistics grid visible
- Data summary table visible
- Chart placeholder visible (or actual chart if Recharts integrated)
- No console errors
```

### Test Alert Settings Tab
```
Expected:
- Alert settings form visible
- Quality threshold selectors visible
- "Advanced Bitrate Thresholds" section expandable
- Save button present
- No console errors
```

### Test Tab Switching
```
Expected:
- Smooth transition between tabs
- Only one tab active at a time
- Active tab styling (blue border/text)
- Components mount/unmount correctly
- No memory leaks in console
```

**Time**: ~5 minutes

---

## 🚨 Troubleshooting

### Issue: Migration Fails
**Solution**:
```bash
# Check database connection
mysql -u root -p -e "SELECT 1;"

# Check migration status
alembic current

# Rollback if needed
alembic downgrade -1
```

### Issue: Tables Not Created
**Solution**:
```bash
# Verify migration ran
mysql -u root -p your_database -e "SELECT * FROM alembic_version;"

# Check for errors in alembic output
alembic upgrade head --verbose
```

### Issue: Metrics Tabs Don't Appear
**Solution**:
```bash
# Clear browser cache
# Ctrl+Shift+Delete (Windows/Linux) or Cmd+Shift+Delete (Mac)

# Hard refresh
# Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)

# Check browser console
# Open DevTools (F12) → Console tab
# Look for errors related to Metrics component
```

### Issue: Trend Data Not Loading
**Solution**:
```bash
# Check API response
curl http://localhost:8000/api/admin/stream/quality/trend/test

# Check backend logs
tail -f backend/logs/*.log
# Look for errors in QualityTrendsService

# Check database
mysql -u root -p your_database -e "SELECT COUNT(*) FROM stream_quality_history;"
```

### Issue: Form Not Responding
**Solution**:
```bash
# Check browser console (F12)
# Look for JavaScript errors

# Check API endpoint
curl -X POST http://localhost:8000/api/admin/stream/quality/alert/config \
  -H "Content-Type: application/json" \
  -d '{"stream_url":"test"}'

# Check backend logs for validation errors
```

---

## ✅ Post-Deployment (1 hour)

### Monitor for 1 Hour
- [ ] Check backend logs for errors
- [ ] Check browser console for warnings
- [ ] Verify database queries completing
- [ ] No spike in API response times

### Test Specific Scenarios
- [ ] Load 24-hour trend data (if data exists)
- [ ] Save alert configuration
- [ ] Verify alert config loads
- [ ] Test form validation (try invalid values)

### Document Issues
- [ ] Note any warnings or errors
- [ ] Create issues for any bugs found
- [ ] Document workarounds if needed

---

## ✅ Team Notification (Immediate)

### Notify Team
```
Feature 022 Phase 3 (Advanced Stream Quality Monitoring)
has been deployed to [staging/production].

New features:
✅ 24-hour quality trends visualization
✅ Alert configuration interface
✅ Intelligent threshold management

Location: Admin > Metrics (3 new tabs)
Docs: PHASE3_QUICK_START.md

Please test and report any issues.
```

---

## 📊 Deployment Summary

| Step | Time | Status |
|------|------|--------|
| Pre-Deployment | 10 min | ✅ |
| Local Testing | 10 min | ✅ |
| Database Backup | 5 min | ✅ |
| Database Migration | 5 min | ✅ |
| Service Deployment | 5 min | ✅ |
| Service Verification | 5 min | ✅ |
| UI/UX Testing | 5 min | ✅ |
| Browser Testing | 5 min | ✅ |
| **Total** | **50 min** | ✅ |

---

## ✅ Sign-Off

**Deployment Completed**: [Date/Time]  
**Deployed By**: [Your Name]  
**Environment**: [staging/production]  
**Status**: ✅ **SUCCESS**

### Verification Complete
- ✅ All tests passing
- ✅ Database migration successful
- ✅ Services running
- ✅ UI tabs visible and functional
- ✅ No console errors
- ✅ Ready for users

### Rollback Plan (If Needed)
```bash
# Step 1: Downgrade database
cd backend
alembic downgrade -1

# Step 2: Restart services
docker compose restart backend frontend

# Step 3: Restore from backup if needed
mysql -u root -p your_database < backup_phase3_*.sql
```

---

## 📞 Support

**During Deployment**:
- Backend logs: `backend/logs/*.log`
- Frontend console: Browser DevTools (F12)
- Database: `mysql -u root -p your_database`

**After Deployment**:
- Feature guide: `docs/features/feature-022-phase3-advanced-monitoring.md`
- Quick troubleshooting: See "Troubleshooting" section above
- Full documentation: `PHASE3_DOCUMENTATION_INDEX.md`

---

## 🎉 Celebrate!

Feature 022 Phase 3 is now live! 

🎊 **Deployment Complete!**

**What's Next**:
1. Gather user feedback
2. Monitor for issues
3. Plan Phase 4 enhancements
4. Consider Phase 4 recommendations in documentation

---

**Deployment Checklist Version**: 1.0  
**Created**: December 16, 2025  
**Status**: Final & Ready to Use
