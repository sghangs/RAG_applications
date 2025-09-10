import requests
from utils.logger import logger
from exceptions import KnowledgeManagementException

class SharePointConnector:
    def __init__(self, tenant_id, client_id, client_secret, site_id, drive_id):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_id = site_id
        self.drive_id = drive_id
        self.token = self._get_access_token()

    def _get_access_token(self):
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        resp = requests.post(url, data=data)
        if resp.status_code != 200:
            raise KnowledgeManagementException(
                "Failed to authenticate with SharePoint",
                resp.text,
                "SharePointConnector"
            )
        return resp.json()["access_token"]

    def fetch_file(self, item_id: str) -> bytes:
        """Download a file from SharePoint using Graph API"""
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drives/{self.drive_id}/items/{item_id}/content"
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise KnowledgeManagementException(
                f"Failed to fetch file {item_id}",
                resp.text,
                "SharePointConnector"
            )
        return resp.content
