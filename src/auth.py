#Author: Pranav Sastry
#DateTime: 2021-06-30 22:15:15.129984 IST

import requests
from rauth import OAuth1Service
from src.config import API_KEY, API_KEY_SECRET

auth = OAuth1Service(name='twitter_login', consumer_key=API_KEY, consumer_secret=API_KEY_SECRET, request_token_url='https://api.twitter.com/oauth/request_token', access_token_url='https://api.twitter.com/oauth/access_token', authorize_url='https://api.twitter.com/oauth/authorize', base_url='https://api.twitter.com/1.1/')

request_token, request_token_secret = auth.get_request_token()
authorize_url = auth.get_authorize_url(request_token)
print(f'URL: {authorize_url}')
