# main.py
from fastapi import FastAPI, Request, BackgroundTasks
from connectors.sharepoint import SharePointConnector
from pipeline import IngestionPipeline
from utils.logger import logger

app = FastAPI()
pipeline = IngestionPipeline()

# Configure SharePoint connection from env/config in prod
sp = SharePointConnector(
    tenant_id="YOUR_TENANT",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    site_id="YOUR_SITE_ID",
    drive_id="YOUR_DRIVE_ID"
)

@app.post("/sharepoint/webhook")
async def sharepoint_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    logger.info(f"[Webhook] received: {payload}")

    # Graph sends notifications in 'value' array
    for event in payload.get("value", []):
        # Graph resourceData contains id and other details
        rd = event.get("resourceData", {})
        item_id = rd.get("id")
        change_type = event.get("changeType")  # created, updated, deleted

        # Use background tasks to quickly ack webhook and process async
        if change_type == "deleted":
            # doc_id strategy: use SharePoint item id as doc_id
            doc_id = item_id
            background_tasks.add_task(pipeline.delete_document, doc_id)
            logger.info(f"[Webhook] scheduled delete for {doc_id}")
        else:
            # created or updated
            try:
                content = sp.fetch_file(item_id)
                # Prefer stable doc_id: use SharePoint item id
                filename = rd.get("name") or f"{item_id}"
                background_tasks.add_task(pipeline.ingest, filename, content)
                logger.info(f"[Webhook] scheduled ingest for {filename}")
            except Exception as e:
                logger.exception(f"[Webhook] failed to fetch file {item_id}: {e}")

    return {"status": "accepted"}
