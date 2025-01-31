#https://mojang-api-docs.gapple.pw/authentication/msa#signing-into-xbox-live

import requests
import re
from urllib.parse import urlencode
import json

EMAIL = input('Enter your email: ')
PASSWORD = input('Enter your password: ')

def extract_tokens(url):
    raw_login_data = url.split("#")[1]
    login_data = dict(item.split("=") for item in raw_login_data.split("&"))
    login_data["access_token"] = requests.utils.unquote(login_data["access_token"])
    login_data["refresh_token"] = requests.utils.unquote(login_data["refresh_token"])
    return login_data

session = requests.Session()

session.allow_redirects = True
response = session.get('https://login.live.com/oauth20_authorize.srf?client_id=000000004C12AE6F&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en')

ppft = ""
url_post = ""

if response.status_code == 200:
    response_text = response.text

    ppft_match = re.search(r'value="(.+?)"', response_text)
    if ppft_match:
        ppft_value = ppft_match.group(1)
        ppft = ppft_value
    else:
        print("PPFT value not found in the response.")

    urlpost_match = re.search(r"urlPost:'(.+?)'", response_text)
    if urlpost_match:
        urlpost_value = urlpost_match.group(1)
        url_post = urlpost_value
    else:
        print("urlPost value not found in the response.")
else:
    print("Failed to retrieve the webpage. Status code:", response.status_code)
    exit()

email = EMAIL
password = PASSWORD
sFTTag = ppft

data = {
    'login': email,
    'loginfmt': email,
    'passwd': password,
    'PPFT': sFTTag
}
response = session.post(url_post, data=urlencode(data), headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=True)


### XBOX live
uhs = ""
xbox_token = ""

if response.status_code == 200:
    if 'access_token' in response.url:
        if response.url == url_post:
            print("Login failed.")
            exit()
        else:
            print("Login successful.")
            tokens = extract_tokens(response.url)

            access_token = tokens.get("access_token", "")

            if access_token:
                post_data = {
                    "Properties": {
                        "AuthMethod": "RPS",
                        "SiteName": "user.auth.xboxlive.com",
                        "RpsTicket": f"{access_token}"  # Include "d=" before the access token
                    },
                    "RelyingParty": "http://auth.xboxlive.com",
                    "TokenType": "JWT"
                }

                json_data = json.dumps(post_data)

                xbox_response = session.post('https://user.auth.xboxlive.com/user/authenticate',
                                             data=json_data,
                                             headers={'Content-Type': 'application/json', 'Accept': 'application/json'})

                uhs = xbox_response.json()['DisplayClaims']['xui'][0]['uhs']
                xbox_token = xbox_response.json()['Token']

                if xbox_response.status_code == 200:
                    print("Authentication successful with Xbox Live.")
                else:
                    print("Failed to authenticate with Xbox Live. Status code:", xbox_response.status_code)
            else:
                print("Access token not found.")
    else:
        if 'Sign in to' in response.text:
            print("Invalid credentials.")
        elif 'Help us protect your account' in response.text:
            print("2-factor authentication is enabled on this account.")
        else:
            print("Unexpected response.")
        exit()
else:
    print("Failed to send the POST request. Status code:", response.status_code)
    exit()

url = "https://xsts.auth.xboxlive.com/xsts/authorize"

json_body = {
    "Properties": {
        "SandboxId": "RETAIL",
        "UserTokens": [
            xbox_token
        ]
    },
    "RelyingParty": "rp://api.minecraftservices.com/",
    "TokenType": "JWT"
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

response = session.post(url, json=json_body, headers=headers)

xsts_token = ""
xsts_uhs = ""

if response.status_code == 200:
    xsts_token = response.json()["Token"]
    xsts_uhs = response.json()["DisplayClaims"]["xui"][0]["uhs"]
else:
    print("Error getting xsts")
    print(response.status_code)
    exit()

payload = {
   "identityToken": "XBL3.0 x=" + xsts_uhs + ";" + xsts_token,
   "ensureLegacyEnabled": True
}

url = "https://api.minecraftservices.com/authentication/login_with_xbox"

response = session.post(url, headers={"Content-Type": "application/json"}, json=payload)

actual_end_token = ""

if response.status_code == 200:
    print("Success! Bearer token received:")
    actual_end_token = response.json().get("access_token", "")
    print("Access Token:", actual_end_token)
else:
    print("Error:", response.status_code)
