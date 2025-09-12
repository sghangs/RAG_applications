import requests
import datetime
from ingestion.utils.logger import get_logger
from ingestion.utils.exceptions import KnowledgeManagementException

logger = get_logger(__name__)
GRAPH_URL = "https://graph.microsoft.com/v1.0"

class SubscriptionCreator:
    def __init__(self, client_id, client_secret, tenant_id, site_id, drive_id, notification_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.site_id = site_id
        self.drive_id = drive_id
        self.notification_url = notification_url
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

    def create_subscription(self, days_valid=3):
        expiration = (datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)).isoformat() + "Z"

        url = f"{GRAPH_URL}/subscriptions"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        body = {
            "changeType": "updated,created,deleted",
            "notificationUrl": self.notification_url,
            "resource": f"/sites/{self.site_id}/drives/{self.drive_id}/root",
            "expirationDateTime": expiration,
            "clientState": "SecretClientValue"  # optional secret for verifying notifications
        }

        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 201:
            raise KnowledgeManagementException(f"Failed to create subscription: {resp.text}")

        sub = resp.json()
        logger.info(f"Subscription created: {sub['id']}, expires {sub['expirationDateTime']}")
        return sub


if __name__ == "__main__":
    creator = SubscriptionCreator(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        tenant_id="YOUR_TENANT_ID",
        site_id="YOUR_SITE_ID",
        drive_id="YOUR_DRIVE_ID",
        notification_url="https://your-domain.com/sharepoint/webhook"
    )
    creator.create_subscription(days_valid=3)
