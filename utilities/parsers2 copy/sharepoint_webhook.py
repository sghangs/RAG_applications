import requests
from ingestion.utils.logger import get_logger
from ingestion.utils.exceptions import KnowledgeManagementException
from ingestion.pipeline import run_ingestion

logger = get_logger(__name__)
GRAPH_URL = "https://graph.microsoft.com/v1.0"

class SharePointWebhookProcessor:
    def __init__(self, client_id, client_secret, tenant_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.token = self._get_token()

    def _get_token(self) -> str:
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default"
        }
        resp = requests.post(url, data=payload)
        if resp.status_code != 200:
            raise KnowledgeManagementException(f"Failed to get Graph token: {resp.text}")
        return resp.json()["access_token"]

    def fetch_item_metadata(self, site_id: str, drive_id: str, item_id: str):
        url = f"{GRAPH_URL}/sites/{site_id}/drives/{drive_id}/items/{item_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise KnowledgeManagementException(f"Failed to fetch item metadata: {resp.text}")
        return resp.json()

    def process_event(self, event: dict, site_id: str, drive_id: str):
        try:
            event_type = event.get("changeType", "updated")
            item_id = event.get("resourceData", {}).get("id")

            if not item_id:
                logger.warning("Webhook event has no item ID, skipping")
                return

            # Handle delete immediately
            if event_type == "deleted":
                run_ingestion(None, doc_id=item_id, project="SharePointProject", event_type="deleted")
                return

            metadata = self.fetch_item_metadata(site_id, drive_id, item_id)
            file_name = metadata.get("name")
            download_url = metadata.get("@microsoft.graph.downloadUrl")

            if not download_url:
                logger.warning(f"No download URL for {file_name}, skipping")
                return

            logger.info(f"Triggering ingestion for {file_name}, event={event_type}")
            run_ingestion(download_url, doc_id=item_id, project="SharePointProject", event_type=event_type)

        except Exception as e:
            raise KnowledgeManagementException(f"Error processing event: {str(e)}")
