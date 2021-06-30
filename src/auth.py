#Author: Pranav Sastry
#DateTime: 2021-06-30 22:15:15.129984 IST

import requests
import secrets
import time
import hmac
import base64
from hashlib import sha1
from urllib.parse import quote_plus
from src.config import API_KEY, ACCESS_TOKEN, API_KEY_SECRET, ACCESS_TOKEN_SECRET


def get_oauth_params():
    oauth_nonce = secrets.token_hex(16)
    oauth_consumer_key = API_KEY
    oauth_signature_method = "HMAC-SHA1"
    oauth_timestamp = str(int(time.time()))
    oauth_version = "1.0"
    oauth_token = ACCESS_TOKEN
    oauth_params = {
                    "oauth_nonce": oauth_nonce,
                    "oauth_consumer_key": oauth_consumer_key,
                    "oauth_signature_method": oauth_signature_method,
                    "oauth_timestamp": oauth_timestamp,
                    "oauth_version": oauth_version,
                    "oauth_token": oauth_token
                    }
    return oauth_params


def get_signature(signature_base_string, signing_key):
    signature_base_string_bytes = bytes(signature_base_string,'utf-8')
    signing_key_bytes = bytes(signing_key,'utf-8')
    hashed = hmac.new(signing_key_bytes, signature_base_string_bytes, sha1)
    hashed_bytes = hashed.digest()
    b64_bytes = base64.b64encode(hashed_bytes)
    b64_signature = quote_plus(b64_bytes.decode('utf-8'));
    return hashed_bytes


def make_auth_request(url, callback_url):
    oauth_params = get_oauth_params()
    parameter_string = f"oauth_callback={callback_url}&oauth_nonce={oauth_params['oauth_nonce']}&oauth_consumer_key={oauth_params['oauth_consumer_key']}&oauth_timestamp={oauth_params['oauth_timestamp']}&oauth_token={oauth_params['oauth_token']}&oauth_signature_method={oauth_params['oauth_signature_method']}&oauth_version={oauth_params['oauth_version']}"
    percent_encoded_parameter_string = quote_plus(parameter_string)
    percent_encoded_url = quote_plus(url)
    signature_base_string = f"POST&{percent_encoded_url}&{percent_encoded_parameter_string}"
    signing_key = quote_plus(API_KEY_SECRET) + "&" + quote_plus(ACCESS_TOKEN_SECRET)
    oauth_signature = get_signature(signature_base_string, signing_key)
    percent_encoded_callback_url = quote_plus(callback_url)
    headers = {"Authorization": f"OAuth oauth_callback={percent_encoded_callback_url},oauth_nonce={oauth_params['oauth_nonce']},oauth_consumer_key={oauth_params['oauth_consumer_key']},oauth_timestamp={oauth_params['oauth_timestamp']},oauth_signature_method={oauth_params['oauth_signature_method']},oauth_version={oauth_params['oauth_version']},oauth_signature={oauth_signature}",
                "Host": "api.twitter.com",
                "Accept": "* /*"
            }
    r = requests.post(url, headers=headers)
    r_json = r.json()
    return r_json


if __name__ == '__main__':
    r_json = make_auth_request("https://api.twitter.com/oauth/request_token", "https://crunchftw.github.io")
    print(r_json)
