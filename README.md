# Blue/Green Deployment with Nginx Auto-Failover

> **🌐 Live Demo**: [http://ec2-13-218-173-73.compute-1.amazonaws.com:8080/](http://ec2-13-218-173-73.compute-1.amazonaws.com:8080/)

##  Overview

This project implements a Blue/Green deployment strategy for a Node.js service using Nginx as a reverse proxy with automatic failover capabilities. The setup ensures zero-downtime deployments and automatic traffic switching when the active service fails.

##  Architecture

```
Client Request → Nginx (localhost:8080)
                   ↓
                Backend Upstream
                   ├─→ Blue App (localhost:8081) [Primary]
                   └─→ Green App (localhost:8082) [Backup]
```

### Key Features

- **Automatic Failover**: Nginx detects failures and switches to backup within the same request
- **Zero Failed Requests**: Retry logic ensures clients always receive 200 OK responses
- **Fast Failure Detection**: Tight timeouts (2s) for quick failover
- **Header Preservation**: Application headers (`X-App-Pool`, `X-Release-Id`) are forwarded to clients
- **Manual Toggle Support**: Switch active pool via environment variables

##  Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Ports 8080, 8081, and 8082 available

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd blue-green-deployment
   ```

2. **Review environment variables**
   
   The `.env` file is already configured with working defaults. Edit if needed:
   ```bash
   nano .env
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Verify deployment**
   ```bash
   curl http://localhost:8080/version
   ```

   Expected response headers:
   ```
   X-App-Pool: blue
   X-Release-Id: blue-v1.0
   ```

##  Project Structure

```
.
├── docker-compose.yml       # Service orchestration
├── nginx.conf.template      # Nginx configuration template
├── entrypoint.sh           # Nginx startup script with envsubst
├── .env                    # Environment variables
└── README.md              # This file
```

##  Configuration

### Environment Variables (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `BLUE_IMAGE` | Docker image for Blue service | `yimikaade/wonderful:devops-stage-two` |
| `GREEN_IMAGE` | Docker image for Green service | `yimikaade/wonderful:devops-stage-two` |
| `ACTIVE_POOL` | Active service pool (blue/green) | `blue` |
| `RELEASE_ID_BLUE` | Release identifier for Blue | `blue-v1.0` |
| `RELEASE_ID_GREEN` | Release identifier for Green | `green-v1.0` |
| `PORT` | Application port | `3000` |

### Nginx Configuration Highlights

- **Primary/Backup Upstreams**: Active pool is primary, others are backup
- **Fast Failover**: `max_fails=1 fail_timeout=5s`
- **Tight Timeouts**: 2s for connect/send/read operations
- **Retry Policy**: Retries on error, timeout, and 5xx status codes
- **Header Forwarding**: All upstream headers passed to clients

##  Testing Failover

### Test Automatic Failover

1. **Verify Blue is active**
   ```bash
   curl -i http://localhost:8080/version
   # Should show X-App-Pool: blue
   ```

2. **Induce failure on Blue**
   ```bash
   # Simulate 500 errors
   curl -X POST http://localhost:8081/chaos/start?mode=error
   
   # OR simulate timeout
   curl -X POST http://localhost:8081/chaos/start?mode=timeout
   ```

3. **Verify automatic switch to Green**
   ```bash
   curl -i http://localhost:8080/version
   # Should now show X-App-Pool: green
   ```

4. **Stop chaos mode**
   ```bash
   curl -X POST http://localhost:8081/chaos/stop
   ```

### Test Manual Pool Toggle

1. **Update .env**
   ```bash
   ACTIVE_POOL=green
   ```

2. **Reload Nginx configuration**
   ```bash
   docker-compose restart nginx
   ```

3. **Verify Green is now active**
   ```bash
   curl -i http://localhost:8080/version
   # Should show X-App-Pool: green
   ```

##  API Endpoints

### Via Nginx (localhost:8080)

- `GET /version` - Returns service version and headers
- `GET /healthz` - Health check endpoint

### Direct Service Access

**Blue Service (localhost:8081)**
- `GET /version`
- `GET /healthz`
- `POST /chaos/start?mode=error` - Start chaos mode (500 errors)
- `POST /chaos/start?mode=timeout` - Start chaos mode (timeouts)
- `POST /chaos/stop` - Stop chaos mode

**Green Service (localhost:8082)**
- Same endpoints as Blue

##  Troubleshooting

### Check service status
```bash
docker-compose ps
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f nginx
docker-compose logs -f app_blue
docker-compose logs -f app_green
```

### Verify Nginx configuration
```bash
docker exec nginx nginx -t
```

### Test direct service access
```bash
# Test Blue directly
curl http://localhost:8081/version

# Test Green directly
curl http://localhost:8082/version
```

##  Performance Expectations

- **Failover Time**: < 2 seconds
- **Request Success Rate**: 100% (zero failed requests during failover)
- **Green Traffic After Failover**: ≥95% (typically 100%)
- **Max Request Duration**: < 10 seconds

##  Development

### Making Configuration Changes

1. Edit `nginx.conf.template`
2. Restart Nginx service:
   ```bash
   docker-compose restart nginx
   ```

### Switching Active Pool

1. Update `ACTIVE_POOL` in `.env`
2. Restart services:
   ```bash
   docker-compose restart nginx
   ```

### Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes and orphans
docker-compose down -v --remove-orphans
```

## ✅ Validation Checklist

- [ ] Blue is active by default
- [ ] All requests return 200 with correct headers
- [ ] Chaos mode triggers automatic failover
- [ ] Zero failed requests during failover
- [ ] Headers (`X-App-Pool`, `X-Release-Id`) are forwarded correctly
- [ ] Manual pool toggle works
- [ ] Services restart cleanly

##  Notes

- Both Blue and Green use the same image but are identified by environment variables
- The `ACTIVE_POOL` variable controls which service is primary in Nginx
- Healthchecks ensure services are ready before accepting traffic
- Nginx retry logic prevents client-facing errors during failover

##  Contributing
=======
# Blue-Green Deployment with Monitoring & Alerts (Stage 3)

## Overview

This project implements a production-ready blue-green deployment strategy with Nginx load balancing, automatic failover, and operational monitoring with Slack alerts.

**Key Features:**
- ✅ Automatic failover between blue and green pools
- ✅ Real-time Slack alerts for failovers and error rates
- ✅ Structured logging with pool, release, and upstream tracking
- ✅ Configurable alert thresholds and cooldowns
- ✅ Maintenance mode for planned deployments

---

## Architecture

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐       ┌──────────────────┐
│  Nginx (Port    │──────▶│  alert_watcher   │
│  8080)          │       │  (Python)        │
│  - Load Balance │       │  - Tail logs     │
│  - Failover     │       │  - Parse events  │
│  - Logging      │       │  - Slack alerts  │
└────────┬────────┘       └──────────────────┘
         │                         │
         │                         ▼
    ┌────┴────┐            ┌──────────────┐
    ▼         ▼            │    Slack     │
┌────────┐ ┌────────┐     │   Webhook    │
│ app_   │ │ app_   │     └──────────────┘
│ blue   │ │ green  │
│:8081   │ │:8082   │
└────────┘ └────────┘
```

---

## Prerequisites

- Docker & Docker Compose installed
- Slack workspace with incoming webhook configured
- Stage 2 setup complete (blue-green deployment working)

---

## Quick Start

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd blue-green-deployment

# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env
```

**Required `.env` variables:**
```bash
# Docker images
BLUE_IMAGE=your-registry/app:blue
GREEN_IMAGE=your-registry/app:green

# Release identifiers
RELEASE_ID_BLUE=blue-v1.0
RELEASE_ID_GREEN=green-v1.0

# Initial active pool
ACTIVE_POOL=blue

# Slack webhook (REQUIRED)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Alert configuration (optional, these are defaults)
ERROR_RATE_THRESHOLD=2.0
WINDOW_SIZE=200
ALERT_COOLDOWN_SEC=300
TRAFFIC_THRESHOLD=50
MAINTENANCE_MODE=false
```

### 2. Start Services

```bash
# Start all services
docker compose up -d

# Verify all containers are running
docker ps

# Check logs
docker compose logs -f
```

### 3. Verify Setup

```bash
# Test the application
curl http://localhost:8080/

# Check which pool is serving
docker exec nginx tail -5 /var/log/nginx/access.log | grep pool=

# Watch alert watcher
docker logs -f alert_watcher
```

Expected output in alert_watcher:
```
[START] Monitoring /var/log/nginx/access.log
[CONFIG] Error threshold: 2.0%, Window: 200, Cooldown: 300s
[SLACK] Alert sent: Alert Watcher Started...
[INIT] Starting pool: blue
```

You should also see a Slack message confirming the watcher started.

---

## Testing Alerts

### Test 1: Failover Alert

This test verifies that stopping the active pool triggers a failover alert.

```bash
# 1. Generate baseline traffic
for i in {1..30}; do 
  curl http://localhost:8080/
  sleep 0.2
done

# 2. Check current pool
docker logs alert_watcher | grep INIT

# 3. Stop the active pool (if blue is active)
docker stop app_blue

# 4. Generate traffic to trigger failover
for i in {1..20}; do 
  curl http://localhost:8080/
  sleep 0.3
done

# 5. Check logs
docker logs alert_watcher | tail -20
```

**Expected Results:**
- ✅ Nginx automatically fails over to green pool
- ✅ Slack alert appears within 10 seconds
- ✅ Alert shows: "Failover Detected! Pool switched: `blue` → `green`"

**Screenshot Location:** See `screenshots/failover-alert.png`

### Test 2: High Error Rate Alert

This test verifies that elevated error rates trigger alerts.

```bash
# 1. Generate clean baseline traffic (60+ requests)
for i in {1..70}; do 
  curl -s http://localhost:8080/ > /dev/null
  sleep 0.1
done

# 2. Stop BOTH containers to force errors
docker stop app_blue app_green

# 3. Generate requests that will return 502/503 errors
for i in {1..30}; do 
  curl -s http://localhost:8080/ > /dev/null 2>&1
  sleep 0.1
done

# 4. Restart containers
docker start app_blue app_green
sleep 5

# 5. Generate more traffic
for i in {1..30}; do 
  curl -s http://localhost:8080/ > /dev/null
  sleep 0.1
done

# 6. Check watcher logs for error stats
docker logs alert_watcher | grep "STATS\|ERROR RATE"
```

**Expected Results:**
- ✅ Error rate climbs above threshold (2%)
- ✅ Slack alert appears within 30 seconds
- ✅ Alert shows: "High Error Rate Detected! Error Rate: `X.XX%`"

**Screenshot Location:** See `screenshots/error-rate-alert.png`

### Test 3: Recovery

```bash
# 1. Restart the stopped container from Test 1
docker start app_blue

# 2. Wait for health checks
sleep 10

# 3. Generate traffic
for i in {1..50}; do 
  curl -s http://localhost:8080/ > /dev/null
  sleep 0.1
done

# 4. Verify blue is serving again (optional manual switch)
# Edit .env: ACTIVE_POOL=blue
# docker compose restart nginx
```

---

## Viewing Logs

### Application Logs
```bash
# Blue pool
docker logs app_blue

# Green pool
docker logs app_green

# Follow live
docker logs -f app_blue
```

### Nginx Logs
```bash
# Access logs (structured format)
docker exec nginx tail -50 /var/log/nginx/access.log

# Error logs
docker exec nginx tail -50 /var/log/nginx/error.log

# Live tail
docker exec nginx tail -f /var/log/nginx/access.log
```

**Example Nginx log line:**
```
172.18.0.1 - - [31/Oct/2025:11:04:15 +0000] "GET / HTTP/1.1" 200 1234 "-" "curl/7.68.0" pool=green release=green-v1.0 upstream_status=200 upstream_addr=172.18.0.3:3000 request_time=0.045 upstream_response_time=0.042
```

Key fields:
- `pool=green` - Which pool served the request
- `release=green-v1.0` - Release identifier
- `upstream_status=200` - Upstream response code
- `upstream_addr=172.18.0.3:3000` - Actual container that responded

### Alert Watcher Logs
```bash
# View recent logs
docker logs alert_watcher | tail -50

# Follow live
docker logs -f alert_watcher

# Check statistics
docker logs alert_watcher | grep STATS

# Check alerts sent
docker logs alert_watcher | grep SLACK
```

---

## Configuration

### Alert Thresholds

Edit `.env` to tune alert sensitivity:

```bash
# Error rate threshold (percentage)
# Lower = more sensitive, more alerts
# Higher = less sensitive, fewer alerts
ERROR_RATE_THRESHOLD=2.0

# Number of requests to track in sliding window
# Larger window = smoother, less volatile
# Smaller window = more responsive, more volatile
WINDOW_SIZE=200

# Minimum requests before alerting on error rate
# Prevents alerts during startup or low traffic
TRAFFIC_THRESHOLD=50

# Cooldown between duplicate alerts (seconds)
# Prevents alert spam
ALERT_COOLDOWN_SEC=300
```

### Maintenance Mode

During planned deployments, enable maintenance mode to suppress failover alerts:

```bash
# Before deployment
echo "MAINTENANCE_MODE=true" >> .env
docker compose restart alert_watcher

# Perform deployment
# ...

# After deployment
echo "MAINTENANCE_MODE=false" >> .env
docker compose restart alert_watcher
```

**Note:** Error rate alerts remain active during maintenance mode.

---

## Operational Runbook

For detailed incident response procedures, see **[runbook.md](runbook.md)**.

Quick reference:

| Alert | Severity | Response Time | Action |
|-------|----------|---------------|--------|
| Failover Detected | 🔴 High | 5 min | Check failed pool health, investigate logs |
| High Error Rate | ⚠️ Medium | 15 min | Monitor trend, check upstream logs, consider pool toggle |
| Watcher Started | ℹ️ Info | None | Informational only |

---

## Troubleshooting

### Alerts Not Appearing

1. **Verify Slack webhook:**
   ```bash
   curl -X POST $SLACK_WEBHOOK_URL \
     -H 'Content-Type: application/json' \
     -d '{"text": "Test from terminal"}'
   ```

2. **Check watcher container:**
   ```bash
   docker ps | grep alert_watcher
   docker logs alert_watcher
   ```

3. **Check environment variables:**
   ```bash
   docker exec alert_watcher env | grep SLACK
   ```

### Watcher Not Starting

```bash
# Check container status
docker ps -a | grep alert_watcher

# Check logs for errors
docker logs alert_watcher

# Restart watcher
docker compose restart alert_watcher
```

### Logs Not Showing Pool Information

```bash
# Verify log format
docker exec nginx cat /etc/nginx/nginx.conf | grep log_format

# Check if upstream headers are being passed
curl -v http://localhost:8080/

# Restart Nginx
docker compose restart nginx
```

### Both Pools Failing

```bash
# Check if images are valid
docker images | grep app

# Check network connectivity
docker network inspect blue-green-deployment_app_network

# Restart all services
docker compose down
docker compose up -d
```

---

## Project Structure

```
blue-green-deployment/
├── docker-compose.yml          # Service orchestration
├── nginx.conf.template         # Nginx configuration with logging
├── entrypoint.sh              # Nginx startup script
├── watcher.py                 # Alert monitoring script
├── requirements.txt           # Python dependencies
├── .env                       # Environment configuration (not in git)
├── .env.example              # Environment template
├── runbook.md                # Operational procedures
├── README.md                 # This file
└── screenshots/              # Verification screenshots
    ├── failover-alert.png
    ├── error-rate-alert.png
    └── nginx-logs.png
```

---

## Screenshots

### 1. Failover Alert in Slack
![Failover Alert](screenshots/failover-alert.png)

Shows the Slack message when the primary pool fails and traffic switches to backup.

### 2. High Error Rate Alert
![Error Rate Alert](screenshots/error-rate-alert.png)

Shows the Slack message when error rate exceeds the configured threshold.

### 3. Structured Nginx Logs
![Nginx Logs](screenshots/nginx-logs.png)

Shows the structured log format with pool, release, and upstream information.

---

## Cleanup

```bash
# Stop all services
docker compose down

# Remove volumes (caution: deletes logs)
docker compose down -v

# Remove images (if needed)
docker rmi $(docker images -q 'your-registry/app:*')
```

---

## Stage 2 Verification

This setup maintains all Stage 2 functionality:
- ✅ Blue-green deployment with Nginx load balancing
- ✅ Automatic failover on container failure
- ✅ Health checks on both pools
- ✅ Manual pool switching via ACTIVE_POOL variable

Stage 2 tests should still pass:
```bash
# Test 1: Normal traffic routing
for i in {1..20}; do curl http://localhost:8080/; done

# Test 2: Failover on primary failure
docker stop app_blue
for i in {1..20}; do curl http://localhost:8080/; done

# Test 3: Manual pool toggle
# Edit .env: ACTIVE_POOL=green
docker compose restart nginx
```

---

## Contributing
>>>>>>> 59c52de (Stage 3: Add observability setup with watcher, runbook, and env example)

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

<<<<<<< HEAD
**Task Completion**: DevOps Intern Stage 2 Task - Part A
=======
Built as part of HNG internship Stage 3 DevOps Challenge


>>>>>>> 59c52de (Stage 3: Add observability setup with watcher, runbook, and env example)
