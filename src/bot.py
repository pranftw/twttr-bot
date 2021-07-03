import os
import requests
from requests_oauthlib import OAuth1Session
import json
import urllib
import logging
import base64 as b64
from src.config import API_KEY, API_KEY_SECRET, BEARER,ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BOT_ID, BOT_HANDLE
from requests.exceptions import ChunkedEncodingError


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s]: [%(levelname)s]: %(name)s:  %(message)s ","%d-%m-%Y %H:%M:%S")
file_handler = logging.FileHandler('src/bot.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class Bot:
    def __init__(self):
        logger.info("Bot STARTED.")
        self.auth = OAuth1Session(API_KEY, client_secret=API_KEY_SECRET, resource_owner_key=ACCESS_TOKEN, resource_owner_secret=ACCESS_TOKEN_SECRET)
        self.headers = {'Authorization':'Bearer {}'.format(BEARER)}
        self.add_rules()

    def tweet(self,text):
        messages = split_text(text,f"@{BOT_HANDLE} ")
        p = self.auth.post("https://api.twitter.com/1.1/statuses/update.json",data={'status':messages[0]})
        if(p.status_code!=200):
            logger.error(f"TWEET {p.json()}")
            return
        twt_id, twt_author = self.get_tweet_details(p.json())
        for message in messages[1:]:
            p = self.auth.post("https://api.twitter.com/1.1/statuses/update.json",data={'status':f"@{twt_author} "+message,'in_reply_to_status_id':twt_id})
            if(p.status_code!=200):
                logger.error(f"TWEET {p.json()}")
                return
            twt_id, twt_author = self.get_tweet_details(p.json())

    def reply(self, text, tweet_id, tweet_author):
        twt_id = tweet_id
        twt_author = tweet_author
        handle_str = f"@{twt_author} "
        messages = split_text(text,handle_str)
        for message in messages:
            p = self.auth.post("https://api.twitter.com/1.1/statuses/update.json",data={'status':handle_str+message,'in_reply_to_status_id':twt_id})
            if(p.status_code!=200):
                logger.error(f"REPLY {p.json()}")
                return
            twt_id, twt_author = self.get_tweet_details(p.json())

    def retweet(self, twt_id):
        p = self.auth.post("https://api.twitter.com/1.1/statuses/retweet/{}.json".format(twt_id))
        if(p.status_code!=200):
            logger.error(f"RETWEET {p.json()}")

    def like(self, twt_id):
        p = self.auth.post(f"https://api.twitter.com/1.1/favorites/create.json?id={twt_id}")
        if(p.status_code!=200):
            logger.error(f"LIKE {p.json()}")

    def dm(self, receiver_id, message):
        p = self.auth.post("https://api.twitter.com/1.1/direct_messages/events/new.json",data=json.dumps({"event":{"type":"message_create","message_create":{"target":{"recipient_id":"{}".format(receiver_id)},"message_data":{"text":"{}".format(message)}}}}))
        if(p.status_code!=200):
            logger.error(f"DM {p.json()}")

    def search(self, queries, expansions=None, tweet_fields=None):
        queries = to_query_str(queries)
        if(not(expansions)):
            expansions = "author_id,geo.place_id,referenced_tweets.id"
        if(not(tweet_fields)):
            tweet_fields = "conversation_id,created_at,geo,referenced_tweets"
        s = requests.get("https://api.twitter.com/2/tweets/search/recent?query={}&max_results=100&expansions={}&tweet.fields={}&user.fields=location,description,username".format(queries,expansions,tweet_fields),headers=self.headers)
        if(s.status_code!=200):
            logger.error(f"SEARCH {s.json()}")
            return None
        else:
            return s.json()

    def stream(self,type="search"):
        print("STREAM STARTED! Listening ...\n")
        timeout = 0
        while True:
            try:
                if(type=="search"):
                    response = requests.get("https://api.twitter.com/2/tweets/search/stream?expansions=author_id", headers=self.headers, stream=True)
                    if(response.status_code!=200):
                        logger.error(f"SearchStream {response.json()}")
                        break
                    self.on_stream_trigger(response)
            except KeyboardInterrupt as e:
                print("\nSTREAM CLOSED!")
                raise SystemExit(e)
            except ChunkedEncodingError:
                continue
            except Exception as e:
                logger.exception(f"STREAMING {e}")
                raise

    def upload_media(self, media_path):
        if(os.path.isfile(media_path)):
            image_extensions = ['gif', 'jpg', 'jpeg', 'png']
            video_extensions = ['mp4']
            media_size = os.path.getsize(media_path)
            media_extension = ((((media_path.split("/"))[-1]).split("."))[-1])
            if(media_extension in image_extensions):
                media_type = "image/" + media_extension
            elif(media_extension in video_extensions):
                media_type = "video/" + media_extension
            else:
                logger.error(f"UPLOAD_MEDIA file extension not supported!")
                return
            headers = {"content-type":"multipart/form-data"}

            # INIT request
            init_request = self.auth.post("https://upload.twitter.com/1.1/media/upload.json",data={"command":"INIT","total_bytes":media_size,"media_type":media_type})
            if(init_request.status_code!=202):
                logger.error(f"UPLOAD_MEDIA init_request {init_request.json()}")
                return
            media_id = init_request.json()['media_id']

            # APPEND request
            media_fp = open(media_path)
            media_string = media_fp.read()
            media_fp.close()
            len_string_in_chunk = len(media_string)/1000
            media_string_split = []
            i = 0
            while(i<len(media_string)):
                media_string_split.append(media_string[i:i+len_string_in_chunk])
                i+=len_string_in_chunk

            for (k,split_string) in enumerate(media_string_split):
                media_bin = ""
                for j in range(0,len(split_string)):
                    media_bin += bin(ord(split_string[j])).replace("0b","").zfill(8)
                media_data = b64.b64encode(split_string.encode('ascii')).decode("ascii")
                append_request = self.auth.post("https://upload.twitter.com/1.1/media/upload.json",data={"command":"APPEND","media_id":media_id,"media":media_bin,"media_data":media_data,"segment_index":k})
                if(append_request.status_code not in range(200,300)):
                    logger.error(f"UPLOAD_MEDIA append_request segment={k} {append_request.json()}")
                    return

            # FINALIZE request
            finalize_request = self.auth.post("https://upload.twitter.com/1.1/media/upload.json",data={"command":"FINALIZE","media_id":media_id},headers=headers)
            if(finalize_request.status_code!=200):
                logger.error(f"UPLOAD_MEDIA finalize_request {finalize_request.json()}")
                return
            return media_id
        else:
            logger.error(f"UPLOAD_MEDIA media_path specified is a directory!")
            return

    def user_timeline(self, username=BOT_HANDLE, exclude_replies=True, include_retweets=False,count=200):
        r = requests.get(f"https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={username}&exclude_replies={exclude_replies}&include_rts={include_retweets}&count={count}")
        if(r.status_code!=200):
            logger.error(f"USER_TIMELINE {r.json()}")
        else:
            return r.json()

    def mentions_timeline(self, user_id=BOT_ID):
        r = requests.get(f"https://api.twitter.com/2/users/{BOT_ID}/mentions", headers=self.headers)
        if(r.status_code!=200):
            logger.error(f"MENTIONS_TIMELINE {r.json()}")
        else:
            return r.json()

    def get_likes(self, username=BOT_HANDLE, count=200):
        r = requests.get(f"https://api.twitter.com/1.1/favorites/list.json", data={"count":count,"screen_name":BOT_HANDLE}, headers=self.headers)
        if(r.status_code!=200):
            logger.error(f"GET_LIKES {r.json()}")
        else:
            return r.json()

    def delete_tweet(self, twt_id):
        p = self.auth.post(f"https://api.twitter.com/1.1/statuses/destroy/{twt_id}.json")
        if(p.status_code!=200):
            logger.error(f"DELETE_TWEET {p.json()}")

    def delete_retweet(self, twt_id):
        p = self.auth.post(f"https://api.twitter.com/1.1/statuses/unretweet/{twt_id}.json")
        if(p.status_code!=200):
            logger.error(f"DELETE_RETWEET {p.json()}")

    def delete_like(self, twt_id):
        p = self.auth.post(f"https://api.twitter.com/1.1/favorites/destroy.json?id={twt_id}")
        if(p.status_code!=200):
            logger.error(f"DELETE_LIKE {p.json()}")

    def get_location_data(self,place_id):
        r = requests.get(f"https://api.twitter.com/1.1/geo/id/:{place_id}.json",headers=self.headers)
        if(r.status_code!=200):
            logger.error(f"GET_LOCATION {r.json()}")
            return None
        else:
            r_json = r.json()
            if(r_json['place_type']!='city'):
                found = False
                for place in r_json['contained_within']:
                    if(place['place_type']=='city'):
                        found = True
                        return place['name']
                if(not(found)):
                    return None
            else:
                return r_json['name']

    def get_tweet_details(self,request_json):
        twt_id = request_json['id']
        twt_author = request_json['user']['screen_name']
        return twt_id,twt_author

    def add_rules(self):
        rules = [{'value':"{} (-is:retweet)".format(BOT_HANDLE)}]
        payload = {"add":rules}
        r = requests.post("https://api.twitter.com/2/tweets/search/stream/rules",headers=self.headers,json=payload)
        if(r.status_code!=200):
            r_str = json.dumps(r.json())
            if('DuplicateRule' not in r_str):
                logger.error(f"AddRules {r.json()}")

    def delete_all_rules(self):
        r = requests.get("https://api.twitter.com/2/tweets/search/stream/rules",headers=self.headers)
        rules = r.json()
        if(rules.get('data',None)):
            ids = list(map(lambda rule: rule["id"], rules["data"]))
            payload = {"delete": {"ids": ids}}
            r = requests.post("https://api.twitter.com/2/tweets/search/stream/rules",headers=self.headers,json=payload)
            if(r.status_code!=200):
                logger.error(f"DeleteRules {r.json()}")

    def on_stream_trigger(self,response):
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line)
                if(json_response['data']['author_id']!=BOT_ID):
                    has_location = json_response.get('geo')
                    if(has_location):
                        location = self.get_location_data(has_location['place_id'])
                    # self.retweet(int(json_response['data']['id']))
                    for user in json_response['includes']['users']:
                        if(user['id']==json_response['data']['author_id']):
                            author_name = user['name']
                            author_handle = user['username']
                            break
                    # self.reply("Thanks for tagging us!",int(json_response['data']['id']),author_handle)
                    # self.dm(json_response['data']['author_id'],"Hey {}!\nThanks for tagging us!".format(author_name))
                    print("{}\n".format(json_response))


def to_query_str(query):
    return urllib.parse.quote(query)


def split_text(text,handle_str=None,limit=280):
    if(handle_str):
        limit -= len(handle_str)
    split_text_list = []
    words = text.split(" ")
    new_str = ""
    i = 0
    while(i<len(words)):
        if(len(new_str+words[i]+" ")<limit):
            new_str += (words[i] + " ")
            i+=1
        else:
            split_text_list.append(new_str)
            new_str = ""
    split_text_list.append(new_str)
    return split_text_list



if __name__=="__main__":
    bot = Bot()
    bot.stream()
