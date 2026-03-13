import aiohttp
from .const import COGNITO_URL, CLIENT_ID

class MyRideAuth:

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
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"
        }

        async with aiohttp.ClientSession() as session:

            async with session.post(
                COGNITO_URL,
                json=payload,
                headers=headers
            ) as resp:

                data = await resp.json()

                return data["AuthenticationResult"]["AccessToken"]