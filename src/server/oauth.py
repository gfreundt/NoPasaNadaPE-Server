import time
import requests
from src.utils.constants import (
    ZOHO_MAIL_API_CLIENT_ID,
    ZOHO_MAIL_API_CLIENT_SECRET,
    ZOHO_MAIL_API_REDIRECT_URL,
)


def get_oauth2_token(self):
    """OAuth2 endpoint for Zoho Mail"""
    print(
        f"Code: {self.all_params['code']}, Location: {self.all_params['location']}, Server: {self.all_params['accounts-server']}"
    )
    authorization_code = self.all_params["code"]
    client_id = ZOHO_MAIL_API_CLIENT_ID
    client_secret = ZOHO_MAIL_API_CLIENT_SECRET
    redirect_uri = ZOHO_MAIL_API_REDIRECT_URL
    scope = "ZohoMail.accounts.ALL"

    url = f"https://accounts.zoho.com/oauth/v2/token?code={authorization_code}&grant_type=authorization_code&client_id={client_id}&client_secret={client_secret}&redirect_uri={redirect_uri}&scope={scope}"

    time.sleep(3)
    response = requests.post(url)
    print("Status code:", response.status_code)
    print("Response body:", response.text)
    self.zoho_mail_token = response.text["access_token"]

    url = "https://mail.zoho.com/api/accounts"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Zoho-oauthtoken 1000.9305fb65057d05d5fca94c0b434d9fee.51a50174728a68d50b36866883e0403f",
    }

    response = requests.get(url, headers=headers)
    params = {}

    print(response.status_code)
    print(response.json())  # Use response.text if it's not valid JSON
    response = requests.get(url, headers=headers, params=params)

    print(response.status_code)
    print(response.json())  # or response.text if it's not valid JSON
