import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://myridek12.tylerapi.com"


class MyRideAPI:

    def __init__(self, token):
        self.token = token
        self.tenant_id = None

    def _headers(self):

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://myridek12.tylerapp.com",
            "Referer": "https://myridek12.tylerapp.com/"
        }

        if self.tenant_id:
            headers["x-tenant-id"] = self.tenant_id

        return headers

    async def discover_tenant(self):

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/api/user",
                headers=self._headers()
            ) as resp:

                data = await resp.json(content_type=None)

                # Format 1 (some districts)
                if "tenantId" in data:
                    self.tenant_id = data["tenantId"]
                    return

                # Format 2 (your district)
                if "groups" in data and len(data["groups"]) > 0:
                    self.tenant_id = data["groups"][0]["groupGuid"]
                    return

                # Format 3
                if "district" in data and "id" in data["district"]:
                    self.tenant_id = data["district"]["id"]
                    return

                raise Exception(f"Unable to determine tenantId: {data}")

    async def get_students(self):

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/api/student",
                headers=self._headers()
            ) as resp:

                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(
                        f"MyRide student API failed: {resp.status} {text}"
                    )

                data = await resp.json(content_type=None)

                return data