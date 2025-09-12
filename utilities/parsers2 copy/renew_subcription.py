import datetime
import requests
from ingestion.sharepoint_webhook import SharePointWebhookHandler
from ingestion.utils.logger import get_logger
from ingestion.utils.exceptions import KnowledgeManagementException

logger = get_logger(__name__)
GRAPH_URL = "https://graph.microsoft.com/v1.0"

class SubscriptionRenewalJob:
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

    def get_subscriptions(self):
        url = f"{GRAPH_URL}/subscriptions"
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise KnowledgeManagementException(f"Failed to list subscriptions: {resp.text}")
        return resp.json().get("value", [])

    def renew_subscriptions(self, days_valid=3, threshold_hours=24):
        try:
            subs = self.get_subscriptions()
            logger.info(f"Found {len(subs)} active subscriptions")
            for sub in subs:
                sub_id = sub["id"]
                expiration_str = sub.get("expirationDateTime")
                if not expiration_str:
                    continue
                expiration = datetime.datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
                now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

                hours_left = (expiration - now).total_seconds() / 3600
                if hours_left <= threshold_hours:
                    logger.info(f"Renewing subscription {sub_id}, expires in {hours_left:.2f}h")
                    handler = SharePointWebhookHandler(
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                        tenant_id=self.tenant_id,
                        site_id="YOUR_SITE_ID",
                        drive_id="YOUR_DRIVE_ID",
                        notification_url="https://your-domain.com/sharepoint/webhook"
                    )
                    handler.renew_subscription(sub_id, days_valid=days_valid)
                else:
                    logger.info(f"Subscription {sub_id} still valid ({hours_left:.2f}h left)")
        except Exception as e:
            raise KnowledgeManagementException(f"Subscription renewal failed: {str(e)}")


if __name__ == "__main__":
    job = SubscriptionRenewalJob(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        tenant_id="YOUR_TENANT_ID"
    )
    job.renew_subscriptions(days_valid=3, threshold_hours=24)
