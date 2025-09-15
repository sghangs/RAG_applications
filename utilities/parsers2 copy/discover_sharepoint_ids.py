import requests
import sys
from ingestion.utils.logger import get_logger
from ingestion.utils.exceptions import KnowledgeManagementException

logger = get_logger(__name__)

GRAPH_URL = "https://graph.microsoft.com/v1.0"


def get_token(client_id, client_secret, tenant_id):
    """Fetch Microsoft Graph access token"""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default"
    }
    resp = requests.post(url, data=payload)
    if resp.status_code != 200:
        raise KnowledgeManagementException(f"Failed to get token: {resp.text}")
    return resp.json()["access_token"]


def get_site_id(token, hostname, site_path):
    """Get SharePoint site_id from hostname + path (e.g., contoso.sharepoint.com + /sites/ProjectX)"""
    url = f"{GRAPH_URL}/sites/{hostname}:{site_path}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise KnowledgeManagementException(f"Failed to get site_id: {resp.text}")
    return resp.json()["id"]


def get_drive_id(token, site_id):
    """Get default document library (drive_id) for a site"""
    url = f"{GRAPH_URL}/sites/{site_id}/drives"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise KnowledgeManagementException(f"Failed to get drives: {resp.text}")
    drives = resp.json()["value"]
    if not drives:
        raise KnowledgeManagementException("No drives found for site")
    return drives[0]["id"], drives[0]["name"]


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python discover_sharepoint_ids.py <client_id> <client_secret> <tenant_id> <hostname> <site_path>")
        print("Example: python discover_sharepoint_ids.py 123abc secret123 456def contoso.sharepoint.com /sites/ProjectX")
        sys.exit(1)

    client_id, client_secret, tenant_id, hostname, site_path = sys.argv[1:6]

    token = get_token(client_id, client_secret, tenant_id)
    site_id = get_site_id(token, hostname, site_path)
    drive_id, drive_name = get_drive_id(token, site_id)

    print(f"\n✅ Site ID: {site_id}")
    print(f"✅ Drive ID: {drive_id} (name: {drive_name})\n")
