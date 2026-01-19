import pytest
import os
from ns_client import NSClient
from dotenv import load_dotenv

load_dotenv()

NS_API_TOKEN = os.getenv("NS_API_TOKEN")
NS_DOMAIN = os.getenv("NS_DOMAIN")
NS_API_URL = os.getenv("NS_API_URL")


@pytest.fixture
def sandbox_client():
    if not NS_API_TOKEN:
        pytest.skip("Skipping: NS_API_TOKEN not set")
    if not NS_API_URL:
        pytest.skip("Skipping: NS_API_URL not set")
    return NSClient(token=NS_API_TOKEN, api_url=NS_API_URL)


@pytest.mark.asyncio
async def test_sandbox_connectivity(sandbox_client):
    if not NS_DOMAIN:
        pytest.skip("Skipping: NS_DOMAIN not set")

    assert sandbox_client.candidate_urls[0] == NS_API_URL.rstrip("/")

    try:
        dids = await sandbox_client.get_dids(NS_DOMAIN)
        print(f"Sandbox: Successfully fetched {len(dids)} DIDs")
    except Exception as e:
        pytest.fail(f"Sandbox connection failed: {e}")


@pytest.mark.asyncio
async def test_get_users(sandbox_client):
    if not NS_DOMAIN:
        pytest.skip("Skipping: NS_DOMAIN not set")

    users = await sandbox_client.get_users(NS_DOMAIN)

    assert users is not None
    assert isinstance(users, list)
    if users:
        print(f"First user: {users[0].user}")
