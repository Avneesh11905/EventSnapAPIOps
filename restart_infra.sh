#!/bin/bash
set -euo pipefail

# Source the .env file in the same directory to get the Webhook Token
source "$(dirname "$0")/.env"

echo "🔄 Running deployment script for Main API..."
sudo /usr/local/bin/eventsnap

# Check if the first argument passed to this script is "RESTART_GCP"
if [ "${1:-}" == "RESTART_GCP" ]; then
    echo "⚠️ WEBHOOK_SECRET changed! Telling Main API to pause Celery Queue..."
    
    # Send offline webhook to Main API locally (port 8003) to safely pause Celery
    curl -s -X POST "http://127.0.0.1:8003/api/webhooks/inference-status" \
         -H "Authorization: Bearer $OPS_WEBHOOK_TOKEN" \
         -H "Content-Type: application/json" \
         -d '{"status": "offline"}' || echo "Failed to pause Celery queue."
    
    echo -e "\n🚀 Telling GCP to replace Spot VMs..."
    /home/eventsnap/googlecloud/google-cloud-sdk/bin/gcloud compute instance-groups managed rolling-action replace eventsnap-gpu-group --zone=us-central1-a
else
    echo "⏭️ Skipping GCP VM replacement (not required for this specific secret change)."
fi

echo "✅ Infrastructure restart complete!"
