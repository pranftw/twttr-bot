import os
import requests
from requests_oauthlib import OAuth1Session
import json
import urllib
import logging
from src.endpoints import CREATE_TWEET, CREATE_RETWEET, CREATE_LIKE, CREATE_DM, FILTERED_SEARCH, FILTERED_STREAM, MEDIA_UPLOAD, USER_TIMELINE, MENTIONS_TIMELINE, GET_LIKES, DELETE_TWEET, DELETE_RETWEET, DELETE_LIKE, GET_LOCATION, RULES
from src.config import API_KEY, API_KEY_SECRET, BEARER,ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BOT_ID, BOT_HANDLE, TWEET_LENGTH
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

    def tweet(self, text=None, text_split=None, medias=None):
        if(text and not(text_split)):
            messages = split_text(text,f"@{BOT_HANDLE} ")
        elif(text_split and not(text)):
            check_split = check_split_text(text_split)
            if(not(check_split)):
                logger.error("TWEET text_split has an entity exceeding the TWEET_LENGTH")
                print("Ensure that all the individual tweets don't exceed the TWEET_LENGTH")
                return
            else:
                messages = text_split
        elif(text and text_split):
            logger.error("TWEET Both text and text_split specified")
            print("Specify either one of text or text_split")
            return
        else:
            logger.error("TWEET Both text and text_split aren't specified")
            print("Specify either one of text or text_split")
            return
        media_list = self.get_media_list("TWEET",messages,medias)
        if(media_list):
            if(media_list[0]):
                p = self.auth.post(CREATE_TWEET, data={'status':messages[0],'media_ids':(",").join(media_list[0])})
            else:
                p = self.auth.post(CREATE_TWEET, data={'status':messages[0]})
            if(p.status_code!=200):
                logger.error(f"TWEET {p.json()}")
                return
            twt_id, twt_author = self.get_tweet_details(p.json())
            k = 1
            for message in messages[1:]:
                if(k<len(media_list)):
                    if(media_list[k]):
                        p = self.auth.post(CREATE_TWEET, data={'status':f"@{twt_author} "+message,'in_reply_to_status_id':twt_id,'media_ids':(",").join(media_list[k])})
                    else:
                        p = self.auth.post(CREATE_TWEET, data={'status':f"@{twt_author} "+message,'in_reply_to_status_id':twt_id})
                    k+=1
                else:
                    p = self.auth.post(CREATE_TWEET, data={'status':f"@{twt_author} "+message,'in_reply_to_status_id':twt_id})
                if(p.status_code!=200):
                    logger.error(f"TWEET {p.json()}")
                    return
                twt_id, twt_author = self.get_tweet_details(p.json())
        else:
            logger.error(f"TWEET get_media_list returned None")
            return

    def reply(self, tweet_id, tweet_author, text=None, text_split=None, medias=None):
        twt_id = tweet_id
        twt_author = tweet_author
        handle_str = f"@{twt_author} "
        if(text and not(text_split)):
            messages = split_text(text,handle_str)
        elif(text_split and not(text)):
            check_split = check_split_text(text_split)
            if(not(check_split)):
                logger.error("TWEET text_split has an entity exceeding the TWEET_LENGTH")
                print("Ensure that all the individual tweets don't exceed the TWEET_LENGTH")
                return
            else:
                messages = text_split
        elif(text and text_split):
            logger.error("TWEET Both text and text_split specified")
            print("Specify either one of text or text_split")
            return
        else:
            logger.error("TWEET Both text and text_split aren't specified")
            print("Specify either one of text or text_split")
            return
        media_list = self.get_media_list("REPLY",messages,medias)
        if(media_list):
            k = 0
            for message in messages:
                if(k<len(media_list)):
                    if(media_list[k]):
                        p = self.auth.post(CREATE_TWEET, data={'status':handle_str+message,'in_reply_to_status_id':twt_id,'media_ids':(",").join(media_list[k])})
                    else:
                        p = self.auth.post(CREATE_TWEET, data={'status':handle_str+message,'in_reply_to_status_id':twt_id})
                    k+=1
                else:
                    p = self.auth.post(CREATE_TWEET, data={'status':handle_str+message,'in_reply_to_status_id':twt_id})
                if(p.status_code!=200):
                    logger.error(f"REPLY {p.json()}")
                    return
                twt_id, twt_author = self.get_tweet_details(p.json())
        else:
            logger.error(f"TWEET get_media_list returned None")
            return

    def retweet(self, twt_id):
        p = self.auth.post(CREATE_RETWEET.format(twt_id))
        if(p.status_code!=200):
            logger.error(f"RETWEET {p.json()}")

    def like(self, twt_id):
        p = self.auth.post(CREATE_LIKE, data={"id":twt_id})
        if(p.status_code!=200):
            logger.error(f"LIKE {p.json()}")

    def dm(self, receiver_id, message):
        p = self.auth.post(CREATE_DM, data=json.dumps({"event":{"type":"message_create","message_create":{"target":{"recipient_id":"{}".format(receiver_id)},"message_data":{"text":"{}".format(message)}}}}))
        if(p.status_code!=200):
            logger.error(f"DM {p.json()}")

    def search(self, queries, expansions=None, tweet_fields=None):
        queries = to_query_str(queries)
        if(not(expansions)):
            expansions = "author_id,geo.place_id,referenced_tweets.id"
        if(not(tweet_fields)):
            tweet_fields = "conversation_id,created_at,geo,referenced_tweets"
        s = requests.get(FILTERED_SEARCH, data={"query":queries,"max_results":100,"expansions":expansions,"tweet.fields":tweet_fields,"user.fields":"location,description,username"},headers=self.headers)
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
                    response = requests.get(FILTERED_STREAM, data={"expansions":"author_id"}, headers=self.headers, stream=True)
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

            # INIT request
            init_request = self.auth.post(UPLOAD_MEDIA, data={"command":"INIT","total_bytes":media_size,"media_type":media_type})
            if(init_request.status_code!=202):
                logger.error(f"UPLOAD_MEDIA init_request {init_request.json()}")
                return
            media_id = init_request.json()['media_id']

            # APPEND request
            with open(media_path,'rb') as media_fp:
                segment_index = 0
                bytes_uploaded = 0
                while(bytes_uploaded<media_size):
                    media_chunk = media_fp.read(4*1024*1024)
                    append_request = self.auth.post(UPLOAD_MEDIA, data={"command":"APPEND","media_id":media_id,"segment_index":segment_index},files={'media':media_chunk})
                    if(append_request.status_code not in range(200,300)):
                        logger.error(f"UPLOAD_MEDIA append_request segment={k} {append_request.json()}")
                        return
                    segment_index+=1
                    bytes_uploaded = media_fp.tell()
                media_fp.close()

            # FINALIZE request
            finalize_request = self.auth.post(UPLOAD_MEDIA, data={"command":"FINALIZE","media_id":media_id})
            if(finalize_request.status_code!=201):
                logger.error(f"UPLOAD_MEDIA finalize_request {finalize_request.json()}")
                return
            return finalize_request.json()['media_id_string']
        else:
            logger.error(f"UPLOAD_MEDIA media_path specified is a directory!")
            return

    def user_timeline(self, username=BOT_HANDLE, exclude_replies=True, include_retweets=False,count=200):
        r = requests.get(USER_TIMELINE, data={"screen_name":username,"exclude_replies":exclude_replies,"include_rts":include_retweets,"count":count})
        if(r.status_code!=200):
            logger.error(f"USER_TIMELINE {r.json()}")
        else:
            return r.json()

    def mentions_timeline(self, user_id=BOT_ID):
        r = requests.get(MENTIONS_TIMELINE.format(BOT_ID), headers=self.headers)
        if(r.status_code!=200):
            logger.error(f"MENTIONS_TIMELINE {r.json()}")
        else:
            return r.json()

    def get_likes(self, username=BOT_HANDLE, count=200):
        r = requests.get(GET_LIKES, data={"count":count,"screen_name":BOT_HANDLE}, headers=self.headers)
        if(r.status_code!=200):
            logger.error(f"GET_LIKES {r.json()}")
        else:
            return r.json()

    def delete_tweet(self, twt_id):
        p = self.auth.post(DELETE_TWEET.format(twt_id))
        if(p.status_code!=200):
            logger.error(f"DELETE_TWEET {p.json()}")

    def delete_retweet(self, twt_id):
        p = self.auth.post(DELETE_RETWEET.format(twt_id))
        if(p.status_code!=200):
            logger.error(f"DELETE_RETWEET {p.json()}")

    def delete_like(self, twt_id):
        p = self.auth.post(DELETE_LIKE, data={"id":twt_id})
        if(p.status_code!=200):
            logger.error(f"DELETE_LIKE {p.json()}")

    def get_media_list(self, type, messages, medias):
        if(medias):
            if(len(medias)>len(messages)):
                logger.error(f"{type}_WITH_MEDIA Length of medias > length of messages")
                print("Length of medias > length of messages")
                return
            else:
                media_list = []
                for media in medias:
                    if(media is None):
                        media_list.append(None)
                    else:
                        media_ids = []
                        for media_path in media:
                            media_id = self.upload_media(media_path)
                            if(media_id):
                                media_ids.append(media_id)
                            else:
                                logger.error(f"{type}_WITH_MEDIA error uploading. upload_media returned None")
                                return
                        media_list.append(media_ids)
        else:
            media_list = list(None for _ in range(len(messages)))
        return media_list

    def get_location_data(self,place_id):
        r = requests.get(GET_LOCATION.format(place_id), headers=self.headers)
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
        r = requests.post(RULES, headers=self.headers,json=payload)
        if(r.status_code!=200):
            r_str = json.dumps(r.json())
            if('DuplicateRule' not in r_str):
                logger.error(f"AddRules {r.json()}")

    def delete_all_rules(self):
        r = requests.get(RULES, headers=self.headers)
        rules = r.json()
        if(rules.get('data',None)):
            ids = list(map(lambda rule: rule["id"], rules["data"]))
            payload = {"delete": {"ids": ids}}
            r = requests.post(RULES, headers=self.headers,json=payload)
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


def split_text(text,handle_str=None,limit=TWEET_LENGTH):
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


def check_split_text(text_split):
    for message in text_split:
        if(len(message)>TWEET_LENGTH):
            return False
    return True


if __name__=="__main__":
    bot = Bot()
    bot.stream()
