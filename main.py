import logging
from fastapi import FastAPI, HTTPException
from schemas import InfisicalWebhookPayload , InfisicalWebhookResponse
from config import settings
from state_machine import restart_manager

app = FastAPI()
logging.basicConfig(level=logging.INFO)


@app.post("/api/ops/infisical-webhook", response_model=InfisicalWebhookResponse)
async def handle_webhook(
    payload: InfisicalWebhookPayload,
    token: str = ""
):
    if token != settings.OPS_WEBHOOK_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Queue the restart in the state machine
    restart_manager.queue_restart()
    
    return InfisicalWebhookResponse()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
