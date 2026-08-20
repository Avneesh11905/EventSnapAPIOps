#!/bin/bash
set -euo pipefail

# Source the .env file in the same directory to get the Webhook Token and Infisical credentials
source "$(dirname "$0")/.env"

echo "🔄 Webhook triggered! Fetching latest secrets from Infisical..."

# 1. Log in to Infisical
export INFISICAL_TOKEN=$(infisical login --method=universal-auth --client-id="$INFISICAL_MACHINE_IDENTITY_CLIENT_ID" --client-secret="$INFISICAL_MACHINE_IDENTITY_CLIENT_SECRET" --plain --silent)

# 2. Export the latest secrets directly to the /app/.env file on the VM
infisical export --projectId="$INFISICAL_PROJECT_ID" --env=prod --format=dotenv > /app/.env

echo "✅ Secrets updated! Restarting all backend Docker containers in /app..."

# 3. Restart Docker containers to pick up the new .env file
# We dynamically preserve the current scale of any scaled services (like celery workers).
cd /app
SCALE_ARGS=""
for SERVICE in $(sudo docker compose config --services); do
    COUNT=$(sudo docker compose ps -q $SERVICE | wc -l)
    if [ "$COUNT" -gt 1 ]; then
        SCALE_ARGS="$SCALE_ARGS --scale $SERVICE=$COUNT"
        echo "Preserving scale for $SERVICE: $COUNT replicas"
    fi
done

sudo docker compose up -d --force-recreate $SCALE_ARGS

# 4. Reload Nginx so it resolves the new internal Docker IPs of the recreated backend containers
echo "🔄 Reloading Nginx to re-resolve backend IPs..."
sudo docker exec eventsnap_nginx nginx -s reload

echo "🚀 Infrastructure update and restart complete!"
