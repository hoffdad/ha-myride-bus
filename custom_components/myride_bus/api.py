import aiohttp
from .const import API_BASE

class MyRideAPI:

    def __init__(self, token):
        self.token = token

    async def get_students(self):

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        async with aiohttp.ClientSession() as session:

            async with session.get(
                f"{API_BASE}/parent/students",
                headers=headers
            ) as resp:

                return await resp.json()