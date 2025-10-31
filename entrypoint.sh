#!/bin/sh
set -e

# Remove default symlinks
rm -f /var/log/nginx/access.log
rm -f /var/log/nginx/error.log

>>>>>>> 59c52de (Stage 3: Add observability setup with watcher, runbook, and env example)
# Substitute environment variables in nginx config
envsubst '${ACTIVE_POOL}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start nginx
exec nginx -g 'daemon off;'
