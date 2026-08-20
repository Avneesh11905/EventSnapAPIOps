#!/bin/bash
set -euo pipefail

# Source the .env file in the same directory to get the Webhook Token and Infisical credentials
source "$(dirname "$0")/.env"

echo "🔄 Webhook triggered! Fetching latest secrets from Infisical..."

# 1. Log in to Infisical
export INFISICAL_TOKEN=$(infisical login --method=universal-auth --client-id="$INFISICAL_MACHINE_IDENTITY_CLIENT_ID" --client-secret="$INFISICAL_MACHINE_IDENTITY_CLIENT_SECRET" --plain --silent)

# 2. Export the latest secrets directly to the /app/.env file on the VM
infisical export --projectId="$INFISICAL_PROJECT_ID" --env=prod --format=dotenv > /app/.env

echo "✅ Secrets updated! Restarting specific Docker containers (keeping Nginx untouched)..."

# 3. Restart Docker containers to pick up the new .env file
# We use --force-recreate to guarantee they pick up the new .env
# We list specific services to avoid restarting es-nginx
cd /app
sudo docker compose up -d --no-deps --force-recreate es-main-api es-celery-worker es-inference-api es-rabbitmq es-flower

# Check if the first argument passed to this script is "RESTART_GCP"
if [ "${1:-}" == "RESTART_GCP" ]; then
    echo -e "\n🔥 Telling GCP to replace Spot VMs..."
    /home/eventsnap/googlecloud/google-cloud-sdk/bin/gcloud compute instance-groups managed rolling-action replace eventsnap-gpu-group --zone=us-central1-a
else
    echo "⏭️ Skipping GCP VM replacement."
fi

echo "🚀 Infrastructure update and restart complete!"
