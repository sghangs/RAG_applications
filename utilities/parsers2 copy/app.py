from fastapi import FastAPI, Request, BackgroundTasks
from ingestion.sharepoint_webhook import SharePointWebhookProcessor
from ingestion.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI()

# Config (load from env in prod)
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
TENANT_ID = "YOUR_TENANT_ID"
SITE_ID = "YOUR_SITE_ID"
DRIVE_ID = "YOUR_DRIVE_ID"

processor = SharePointWebhookProcessor(CLIENT_ID, CLIENT_SECRET, TENANT_ID)

@app.get("/sharepoint/webhook")
async def validation(request: Request):
    token = request.query_params.get("validationToken")
    if token:
        logger.info("Validating subscription")
        return token
    return {"status": "ok"}

@app.post("/sharepoint/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    events = data.get("value", [])
    logger.info(f"Webhook events received: {len(events)}")

    for event in events:
        background_tasks.add_task(processor.process_event, event, SITE_ID, DRIVE_ID)

    return {"status": "processing"}
