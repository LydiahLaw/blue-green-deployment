# HNG Stage 3 - Blue/Green Deployment with Nginx Auto-Failover

This project implements a Blue/Green deployment strategy for a Node.js application using Docker Compose and Nginx. It automatically routes traffic to the active service (Blue or Green) and fails over with zero downtime if the active instance becomes unavailable.

---

## ✳️ Project Overview

You’re deploying two identical Node.js containers (Blue and Green) behind an Nginx reverse proxy.  
Blue is the **active** app by default, Green is the **backup**.  
When Blue fails, Nginx automatically switches traffic to Green without any failed client requests.

The applications include these endpoints (already in the provided image):

- `GET /version` → Returns JSON + headers (`X-App-Pool`, `X-Release-Id`)
- `GET /healthz` → Checks app health
- `POST /chaos/start` → Simulates downtime or error
- `POST /chaos/stop` → Stops simulated downtime

---

## 🧠 What You’ll Learn

- How Nginx handles upstream failover and retries  
- How Blue/Green deployments enable zero-downtime releases  
- How to parameterize Docker Compose using a `.env` file  
- How to test failover behavior and confirm headers from both app versions

---

## 🏗️ Architecture

**Services:**
- **Nginx** – Reverse proxy and load balancer  
- **app_blue** – Blue version of the app (active by default, port 8081)  
- **app_green** – Green version of the app (backup, port 8082)

**Ports:**
- Public (Nginx): `http://<EC2-IP>:8080`
- Blue direct: `http://<EC2-IP>:8081`
- Green direct: `http://<EC2-IP>:8082`

**Failover Flow:**
1. All traffic goes to Blue by default.
2. If Blue returns `5xx` or times out, Nginx retries the same request to Green.
3. Nginx automatically switches to Green until Blue recovers.

---

## 🧩 Prerequisites

- AWS EC2 instance (Ubuntu 22.04 or similar)
- Docker Engine (v20.10+) installed
- Docker Compose (v2.0+)
- Security group open for ports 8080, 8081, 8082
- SSH access to EC2 (e.g. `ssh -i "blue-green-key.pem" ubuntu@<EC2-IP>`)

---

## ⚙️ Setup Instructions (EC2)

### 1. SSH into your EC2 instance
```bash
ssh -i "blue-green-key.pem" ubuntu@<your-ec2-public-dns>
