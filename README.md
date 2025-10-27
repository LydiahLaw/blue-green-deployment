# Blue/Green Deployment with Nginx Auto-Failover

> **🌐 Live Demo**: [http://ec2-13-218-173-73.compute-1.amazonaws.com:8080/](http://ec2-13-218-173-73.compute-1.amazonaws.com:8080/)

## 📋 Overview

This project implements a Blue/Green deployment strategy for a Node.js service using Nginx as a reverse proxy with automatic failover capabilities. The setup ensures zero-downtime deployments and automatic traffic switching when the active service fails.

## 🏗️ Architecture

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

## 🚀 Quick Start

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

## 📁 Project Structure

```
.
├── docker-compose.yml       # Service orchestration
├── nginx.conf.template      # Nginx configuration template
├── entrypoint.sh           # Nginx startup script with envsubst
├── .env                    # Environment variables
└── README.md              # This file
```

## ⚙️ Configuration

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

## 🧪 Testing Failover

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

## 📡 API Endpoints

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

## 🔍 Troubleshooting

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

## 📊 Performance Expectations

- **Failover Time**: < 2 seconds
- **Request Success Rate**: 100% (zero failed requests during failover)
- **Green Traffic After Failover**: ≥95% (typically 100%)
- **Max Request Duration**: < 10 seconds

## 🛠️ Development

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

## 📝 Notes

- Both Blue and Green use the same image but are identified by environment variables
- The `ACTIVE_POOL` variable controls which service is primary in Nginx
- Healthchecks ensure services are ready before accepting traffic
- Nginx retry logic prevents client-facing errors during failover

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Task Completion**: DevOps Intern Stage 2 Task - Part A