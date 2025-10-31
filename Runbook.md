# Blue-Green Deployment Alert Runbook

## Overview
This runbook describes how to respond to alerts from the Nginx monitoring system for the blue-green deployment setup.

---

## Alert Types

### 1. 🔴 Failover Detected

**Alert Example:**
```
Failover Detected!
Pool switched: `blue` → `green`
Time: 2025-10-31 11:04:15
Check health of blue container immediately.
```

**What it means:**
- The primary pool (blue or green) has failed health checks or returned too many errors
- Nginx has automatically failed over to the backup pool
- Traffic is now being served by the secondary pool

**Operator Actions:**

1. **Verify the failover** (2 minutes)
   ```bash
   # Check which containers are running
   docker ps
   
   # Check container health status
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

2. **Inspect the failed pool's logs** (5 minutes)
   ```bash
   # If blue failed, check its logs
   docker logs app_blue --tail 100
   
   # Or if green failed
   docker logs app_green --tail 100
   
   # Look for:
   # - Application errors
   # - Out of memory errors
   # - Connection refused
   # - Health check failures
   ```

3. **Check container health** (2 minutes)
   ```bash
   # Test health endpoint directly
   curl http://localhost:8081/healthz  # Blue
   curl http://localhost:8082/healthz  # Green
   
   # Check resource usage
   docker stats --no-stream
   ```

4. **Decide on action:**
   
   **Option A: Temporary issue - Restart failed container**
   ```bash
   docker restart app_blue  # or app_green
   
   # Wait 10 seconds for health checks
   sleep 10
   
   # Verify health
   docker ps
   curl http://localhost:8081/healthz
   ```
   
   **Option B: Application bug - Keep current pool active**
   - Leave traffic on the healthy pool
   - Investigate logs for root cause
   - Fix the issue and deploy new image
   - Test before switching back
   
   **Option C: Complete outage - Both pools affected**
   ```bash
   # Check Nginx status
   docker logs nginx --tail 50
   
   # Restart all services if needed
   docker compose restart
   ```

5. **Verify recovery** (2 minutes)
   ```bash
   # Generate test traffic
   for i in {1..20}; do curl http://localhost:8080/ && sleep 0.5; done
   
   # Check Nginx logs for pool
   docker exec nginx tail -20 /var/log/nginx/access.log | grep "pool="
   ```

6. **Document incident**
   - Record time of failover
   - Note root cause
   - Document resolution steps
   - Update team in Slack thread

**Expected Resolution Time:** 5-15 minutes

---

### 2. ⚠️ High Error Rate Detected

**Alert Example:**
```
High Error Rate Detected!
Error Rate: `3.92%` (threshold: 2.0%)
Window: 2 errors in 51 requests
Pool: `green`
Time: 2025-10-31 11:04:15
Inspect upstream logs and consider pool toggle.
```

**What it means:**
- The current pool is returning elevated 5xx errors
- Error rate has exceeded the configured threshold (default: 2%)
- System is still functional but degraded
- May indicate application issues, resource constraints, or partial failures

**Operator Actions:**

1. **Assess severity** (1 minute)
   ```bash
   # Check current error rate in real-time
   docker logs alert_watcher --tail 20 | grep STATS
   
   # Sample format:
   # [STATS] Requests: 150, Errors: 5, Rate: 3.33%
   ```

2. **Check upstream logs** (3 minutes)
   ```bash
   # Check which pool is active
   docker exec nginx tail -50 /var/log/nginx/access.log | grep "pool="
   
   # If green is active and showing errors
   docker logs app_green --tail 100
   
   # Look for:
   # - Database connection errors
   # - Timeout errors
   # - Memory/CPU issues
   # - Third-party API failures
   ```

3. **Check system resources** (2 minutes)
   ```bash
   # Check container resource usage
   docker stats --no-stream
   
   # Check if containers are being throttled
   docker inspect app_green | grep -A 5 "Memory"
   ```

4. **Determine if error rate is climbing or stable:**
   
   **If climbing (getting worse):**
   ```bash
   # Manually switch to the backup pool
   
   # Step 1: Update .env
   # Change ACTIVE_POOL from current to other pool
   # If currently green, change to blue:
   nano .env  # Change ACTIVE_POOL=blue
   
   # Step 2: Restart Nginx
   docker compose restart nginx
   
   # Step 3: Verify switch
   docker logs nginx | tail -20
   
   # Step 4: Monitor new pool
   for i in {1..30}; do curl http://localhost:8080/ && sleep 0.3; done
   ```
   
   **If stable (not getting worse):**
   - Monitor for 5 more minutes
   - Check if specific endpoints are failing
   - May be transient issue
   
   **If declining (getting better):**
   - Transient issue, likely resolved
   - Continue monitoring
   - No action needed

5. **Investigate root cause** (10-30 minutes)
   ```bash
   # Check for common issues:
   
   # Database connectivity
   docker logs app_green | grep -i "database\|connection"
   
   # Memory issues
   docker logs app_green | grep -i "memory\|oom"
   
   # Timeout issues
   docker logs app_green | grep -i "timeout"
   
   # Recent deploys
   echo $RELEASE_ID_GREEN  # Check version
   ```

6. **Recovery actions:**
   - If transient: Continue monitoring
   - If persistent: Switch pools (see step 4)
   - If critical bug: Rollback to previous version
   - If resource issue: Scale up or restart container

7. **Post-incident:**
   - Monitor error rate for 30 minutes
   - Verify error rate drops below threshold
   - Document findings in Slack thread
   - Create ticket for root cause analysis

**Expected Resolution Time:** 10-30 minutes

---

### 3. ✅ Alert Watcher Started

**Alert Example:**
```
Alert Watcher Started
Monitoring Blue-Green deployment
Error threshold: 2.0%
```

**What it means:**
- The monitoring system has started successfully
- Alerts are now active

**Operator Actions:**
- No action required
- Informational only
- Confirms monitoring is operational

---

## Maintenance Mode

When performing planned pool switches (e.g., deployments), enable maintenance mode to suppress failover alerts:

```bash
# Before planned switch
echo "MAINTENANCE_MODE=true" >> .env
docker compose restart alert_watcher

# Perform your deployment/switch
# ...

# After deployment complete
echo "MAINTENANCE_MODE=false" >> .env
docker compose restart alert_watcher
```

**Note:** Maintenance mode only suppresses failover alerts. Error-rate alerts remain active.

---

## Configuration

### Alert Thresholds (in `.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ERROR_RATE_THRESHOLD` | 2.0 | Error rate % that triggers alert |
| `WINDOW_SIZE` | 200 | Number of requests to track for error rate |
| `ALERT_COOLDOWN_SEC` | 300 | Seconds between duplicate alerts |
| `TRAFFIC_THRESHOLD` | 50 | Minimum requests before error alerts |
| `MAINTENANCE_MODE` | false | Suppress failover alerts during planned changes |

### Tuning Recommendations

**For high-traffic environments (>1000 req/min):**
```bash
ERROR_RATE_THRESHOLD=1.0
WINDOW_SIZE=500
TRAFFIC_THRESHOLD=100
```

**For low-traffic environments (<100 req/min):**
```bash
ERROR_RATE_THRESHOLD=5.0
WINDOW_SIZE=100
TRAFFIC_THRESHOLD=20
```

**For production (sensitive):**
```bash
ERROR_RATE_THRESHOLD=0.5
ALERT_COOLDOWN_SEC=180
```

---

## Testing Alerts

### Test Failover Alert
```bash
# Generate baseline traffic
for i in {1..30}; do curl http://localhost:8080/ && sleep 0.2; done

# Stop active pool
docker stop app_blue  # or app_green

# Trigger failover
for i in {1..20}; do curl http://localhost:8080/ && sleep 0.2; done

# Expected: Failover alert in Slack within 10 seconds
```

### Test Error Rate Alert
```bash
# Generate clean traffic first
for i in {1..60}; do curl -s http://localhost:8080/ > /dev/null && sleep 0.1; done

# Stop both containers to force errors
docker stop app_blue app_green

# Generate errors
for i in {1..30}; do curl -s http://localhost:8080/ > /dev/null 2>&1 && sleep 0.1; done

# Restart containers
docker start app_blue app_green
sleep 5

# Continue traffic
for i in {1..30}; do curl -s http://localhost:8080/ > /dev/null && sleep 0.1; done

# Expected: Error rate alert in Slack within 30 seconds
```

---

## Troubleshooting

### Alerts Not Appearing in Slack

1. **Verify webhook URL:**
   ```bash
   curl -X POST $SLACK_WEBHOOK_URL \
     -H 'Content-Type: application/json' \
     -d '{"text": "Test from terminal"}'
   ```

2. **Check watcher logs:**
   ```bash
   docker logs alert_watcher | grep -i "slack\|error"
   ```

3. **Verify watcher is running:**
   ```bash
   docker ps | grep alert_watcher
   ```

### False Positive Alerts

If getting too many alerts:
- Increase `ERROR_RATE_THRESHOLD`
- Increase `ALERT_COOLDOWN_SEC`
- Increase `TRAFFIC_THRESHOLD`

### Missed Alerts

If not getting expected alerts:
- Decrease `ERROR_RATE_THRESHOLD`
- Decrease `TRAFFIC_THRESHOLD`
- Check watcher logs for errors

---

## Quick Reference Commands

```bash
# View live alerts
docker logs -f alert_watcher

# Check current pool serving traffic
docker exec nginx tail -20 /var/log/nginx/access.log | grep pool=

# Check error rate stats
docker logs alert_watcher | grep STATS | tail -5

# Test Slack webhook
curl -X POST $SLACK_WEBHOOK_URL -H 'Content-Type: application/json' -d '{"text":"Test"}'

# Manually switch pools
# 1. Edit .env: change ACTIVE_POOL=blue (or green)
# 2. Restart: docker compose restart nginx

# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"
curl http://localhost:8081/healthz  # Blue
curl http://localhost:8082/healthz  # Green

# View Nginx logs
docker exec nginx tail -50 /var/log/nginx/access.log

# Restart everything
docker compose restart

# Stop all
docker compose down

# Start fresh
docker compose up -d
```
