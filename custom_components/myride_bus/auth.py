import aiohttp
import datetime

from .const import COGNITO_URL, CLIENT_ID


class MyRideAuth:

    def __init__(self):
        self.token = None
        self.expiry = None

    async def login(self, username, password):

        payload = {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": CLIENT_ID,
            "AuthParameters": {
                "USERNAME": username,
                "PASSWORD": password
            }
        }

        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        }

        async with aiohttp.ClientSession() as session:

            async with session.post(
                COGNITO_URL,
                json=payload,
                headers=headers
            ) as resp:

                data = await resp.json(content_type=None)

                result = data["AuthenticationResult"]

                self.token = result["AccessToken"]

                # token expires in seconds
                self.expiry = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=result["ExpiresIn"]
                )

                return self.token

    async def get_token(self, username, password):

        if self.token and datetime.datetime.utcnow() < self.expiry:
            return self.token

        return await self.login(username, password)