# Blue/Green Deployment with Nginx (Auto-Failover + Manual Toggle)

## Overview
This project demonstrates a Blue/Green deployment using Docker Compose and Nginx as a reverse proxy with automatic failover. It runs two identical Node.js services — Blue (active) and Green (backup) — behind Nginx. When Blue fails, Nginx automatically switches traffic to Green with zero client errors.

## Architecture
**Services**
- app_blue: Active Node.js service (default)
- app_green: Backup Node.js service
- nginx: Reverse proxy managing routing and failover

**Flow**
1. Client sends requests to Nginx (http://localhost:8080)  
2. Nginx routes traffic to the active app (Blue or Green)  
3. If Blue fails (timeout or 5xx), Nginx retries the request on Green  
4. Client still receives a successful 200 response  

**Ports**
- Nginx: 8080  
- Blue: 8081  
- Green: 8082  

## File Structure
blue-green-deployment/  
├── docker-compose.yml  
├── nginx.conf.template  
├── entrypoint.sh  
├── .env.example  
└── README.md  

## Environment Variables
Configured via a .env file:

BLUE_IMAGE=yimikaade/wonderful:devops-stage-two  
GREEN_IMAGE=yimikaade/wonderful:devops-stage-two  
ACTIVE_POOL=blue  
RELEASE_ID_BLUE=blue-v1.0  
RELEASE_ID_GREEN=green-v1.0  
PORT=3000  

To manually switch, change ACTIVE_POOL=green and reload Nginx or restart the containers.

## Nginx Configuration
Defined in nginx.conf.template:
- Uses upstreams with primary and backup roles  
- Tight timeouts for fast failure detection  
- Retries failed requests on the backup app  
- Forwards headers X-App-Pool and X-Release-Id unchanged  

## Docker Compose Overview
Two Node.js containers (Blue and Green) expose endpoints for version, health, and chaos simulation:
- GET /version → shows app and release  
- GET /healthz → health check  
- POST /chaos/start → simulate failure  
- POST /chaos/stop → restore  

Nginx routes requests between them based on health and configuration.

## How to Run
1. Clone the repository  
   git clone https://github.com/<your-username>/blue-green-deployment.git  
   cd blue-green-deployment  

2. Create your environment file  
   cp .env.example .env  

3. Start the services  
   docker-compose up -d  

4. Check containers  
   docker ps  

5. Test the active environment  
   curl -i http://localhost:8080/version  
   Expected headers:  
   X-App-Pool: blue  
   X-Release-Id: blue-v1.0  

6. Simulate Blue’s failure  
   curl -X POST http://localhost:8081/chaos/start?mode=error  
   Then check again:  
   curl -i http://localhost:8080/version  
   Expected headers:  
   X-App-Pool: green  
   X-Release-Id: green-v1.0  

7. Recover Blue  
   curl -X POST http://localhost:8081/chaos/stop  

## Manual Toggle
To switch manually:
- Update .env → ACTIVE_POOL=green  
- Reload Nginx: docker exec nginx nginx -s reload  
  or restart: docker-compose down && docker-compose up -d  

## Key Concepts
- Blue/Green deployment strategy  
- Nginx upstreams and retry logic  
- Health-based failover  
- Environment-driven configuration  
- Docker Compose orchestration  

## Troubleshooting
- Ensure entrypoint.sh is executable: chmod +x entrypoint.sh  
- Check logs if failover doesn’t occur:  
  docker logs nginx  
  docker logs app_blue  
  docker logs app_green  
- Verify timeouts in nginx.conf.template are short for quick detection  

## Deliverables
| File | Purpose |
|------|----------|
| docker-compose.yml | Defines containers and networking |
| nginx.conf.template | Handles routing and failover |
| entrypoint.sh | Substitutes environment variables into Nginx config |
| .env.example | Lists required environment variables |
| README.md | Explains setup and usage |
