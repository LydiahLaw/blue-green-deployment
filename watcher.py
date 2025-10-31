#!/usr/bin/env python3
"""
Nginx Log Watcher - Monitors logs for failover and error rate alerts
"""
import os
import re
import time
import json
import requests
from collections import deque
from datetime import datetime

# Configuration from environment
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', '2.0'))
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', '200'))
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', '300'))
MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
TRAFFIC_THRESHOLD = int(os.getenv('TRAFFIC_THRESHOLD', '50'))  # Minimum requests before alerting

LOG_FILE = '/var/log/nginx/access.log'

# State tracking
current_pool = None
request_window = deque(maxlen=WINDOW_SIZE)
last_failover_alert = 0
last_error_alert = 0
total_requests = 0

def send_slack_alert(message, alert_type="info"):
    """Send alert to Slack"""
    if not SLACK_WEBHOOK_URL:
        print(f"[ALERT] {message} (Slack webhook not configured)")
        return False
    
    color_map = {
        "danger": "#dc3545",
        "warning": "#ffc107",
        "good": "#28a745",
        "info": "#17a2b8"
    }
    
    payload = {
        "attachments": [{
            "color": color_map.get(alert_type, "#17a2b8"),
            "title": f":rotating_light: Blue-Green Deployment Alert",
            "text": message,
            "footer": "Nginx Monitor",
            "ts": int(time.time())
        }]
    }
    
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"[SLACK] Alert sent: {message}")
            return True
        else:
            print(f"[SLACK ERROR] Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[SLACK ERROR] Failed to send alert: {e}")
        return False

def parse_log_line(line):
    """Parse Nginx log line to extract relevant fields"""
    try:
        # Extract pool (look for pool=value)
        pool_match = re.search(r'pool=(\w+)', line)
        pool = pool_match.group(1) if pool_match else None
        
        # Extract upstream_status
        status_match = re.search(r'upstream_status=(\d+)', line)
        upstream_status = int(status_match.group(1)) if status_match else None
        
        # Extract upstream_addr to detect actual server
        addr_match = re.search(r'upstream_addr=([\d\.:]+)', line)
        upstream_addr = addr_match.group(1) if addr_match else None
        
        # Extract HTTP status code
        status_code_match = re.search(r'"\s+(\d{3})\s+\d+', line)
        status_code = int(status_code_match.group(1)) if status_code_match else None
        
        return {
            'pool': pool,
            'upstream_status': upstream_status or status_code,
            'upstream_addr': upstream_addr,
            'line': line
        }
    except Exception as e:
        print(f"[PARSE ERROR] {e}: {line}")
        return None

def check_failover(pool):
    """Check if a failover occurred"""
    global current_pool, last_failover_alert
    
    if pool is None:
        return
    
    # Initialize on first request
    if current_pool is None:
        current_pool = pool
        print(f"[INIT] Starting pool: {pool}")
        return
    
    # Detect pool change
    if pool != current_pool:
        now = time.time()
        
        # Check cooldown
        if now - last_failover_alert < ALERT_COOLDOWN_SEC:
            print(f"[COOLDOWN] Failover detected but in cooldown period")
            return
        
        # Check maintenance mode
        if MAINTENANCE_MODE:
            print(f"[MAINTENANCE] Failover detected but maintenance mode active")
            current_pool = pool
            return
        
        message = (
            f"*Failover Detected!*\n"
            f"Pool switched: `{current_pool}` → `{pool}`\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"_Check health of {current_pool} container immediately._"
        )
        
        if send_slack_alert(message, "danger"):
            last_failover_alert = now
            print(f"[FAILOVER] {current_pool} → {pool}")
        
        current_pool = pool

def check_error_rate():
    """Check if error rate exceeds threshold"""
    global last_error_alert
    
    if len(request_window) < TRAFFIC_THRESHOLD:
        # Not enough requests yet
        return
    
    # Count 5xx errors in window
    error_count = sum(1 for status in request_window if status and status >= 500)
    error_rate = (error_count / len(request_window)) * 100
    
    # Debug output every 50 requests
    if total_requests % 50 == 0:
        print(f"[STATS] Requests: {len(request_window)}, "
              f"Errors: {error_count}, Rate: {error_rate:.2f}%")
    
    # Check if threshold breached
    if error_rate > ERROR_RATE_THRESHOLD:
        now = time.time()
        
        # Check cooldown
        if now - last_error_alert < ALERT_COOLDOWN_SEC:
            return
        
        message = (
            f"*High Error Rate Detected!*\n"
            f"Error Rate: `{error_rate:.2f}%` (threshold: {ERROR_RATE_THRESHOLD}%)\n"
            f"Window: {error_count} errors in {len(request_window)} requests\n"
            f"Pool: `{current_pool or 'unknown'}`\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"_Inspect upstream logs and consider pool toggle._"
        )
        
        if send_slack_alert(message, "warning"):
            last_error_alert = now
            print(f"[ERROR RATE] {error_rate:.2f}% exceeds threshold")

def tail_logs():
    """Tail Nginx logs and process in real-time"""
    global total_requests
    
    print(f"[START] Monitoring {LOG_FILE}")
    print(f"[CONFIG] Error threshold: {ERROR_RATE_THRESHOLD}%, "
          f"Window: {WINDOW_SIZE}, Cooldown: {ALERT_COOLDOWN_SEC}s")
    print(f"[CONFIG] Maintenance mode: {MAINTENANCE_MODE}")
    
    # Wait for log file to exist
    while not os.path.exists(LOG_FILE):
        print(f"[WAIT] Waiting for {LOG_FILE}...")
        time.sleep(2)
    
    # Send startup notification
    send_slack_alert(
        f"*Alert Watcher Started*\n"
        f"Monitoring Blue-Green deployment\n"
        f"Error threshold: {ERROR_RATE_THRESHOLD}%",
        "good"
    )
    
    # Open and seek to end
    with open(LOG_FILE, 'r') as f:
        # Go to end of file
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            
            if not line:
                time.sleep(0.1)  # Wait for new data
                continue
            
            # Parse log line
            parsed = parse_log_line(line)
            
            if parsed:
                total_requests += 1
                
                # Track pool
                if parsed['pool']:
                    check_failover(parsed['pool'])
                
                # Track error rate
                if parsed['upstream_status']:
                    request_window.append(parsed['upstream_status'])
                    check_error_rate()

if __name__ == '__main__':
    try:
        tail_logs()
    except KeyboardInterrupt:
        print("\n[STOP] Watcher stopped by user")
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        send_slack_alert(f"*Watcher Crashed*\n```{e}```", "danger")
