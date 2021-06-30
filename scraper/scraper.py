import os
import sys
from hashlib import sha256
import json
import time
import logging
from src.bot import Bot
from scraper.scraper_config import hashtags, handles


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s]: [%(levelname)s]: %(name)s:  %(message)s ","%d-%m-%Y %H:%M:%S")
file_handler = logging.FileHandler('scraper/scraper.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def hash_data(data):
    hashed = []
    for d in data:
        hashed.append(sha256(str(d).encode('utf-8')).hexdigest())
    return hashed


class QueryLengthExceededError(Exception):
    pass


def to_queries(hashtags, handles):
    queries = []
    triggers = hashtags + handles
    triggers_str = " OR ".join(triggers)
    raw_str = "lang:en ({}) (-is:retweet)"
    if(len(triggers_str) > (510-len(raw_str))):
        raise QueryLengthExceededError("Error: Please remove some hashtags or handles.")
    else:
        return raw_str.format(triggers_str)


def get_data(fname):
    if(fname=="extracted_data"):
        file_obj = open("scraper/extracted_data.json","r")
    elif(fname=="hashed_data"):
        file_obj = open("scraper/hashed_data.json","r")
    data = json.load(file_obj)['data']
    file_obj.close()
    return data


def save_to_file(data,fname):
    if(fname=="extracted_data"):
        file_obj = open("scraper/extracted_data.json","w")
    elif(fname=="hashed_data"):
        file_obj = open("scraper/hashed_data.json","w")
    json.dump({"data":data},file_obj,indent=4,default=str)
    file_obj.close()


def scrape(bot, num_tweets):
    logger.info("Scraping STARTED")
    print("SCRAPING ...\n")
    tweets_scraped = 0
    extracted_data = []
    hashed_data = get_data("hashed_data")
    while(tweets_scraped<num_tweets):
        try:
            search_results = bot.search(queries=to_queries(hashtags,handles)) # 100 is the max you can fetch from Twitter at a time
            if(search_results):
                search_results = search_results.get('data')
                for result in search_results:
                    result_hash = sha256(str(result).encode('utf-8')).hexdigest()
                    if(result_hash not in hashed_data):
                        extracted_data.append(result)
                        hashed_data.append(result_hash)
                        tweets_scraped += 1
                        print("\r{} / {} tweets scraped!".format(tweets_scraped,num_tweets),end="")
                        if(tweets_scraped==num_tweets):
                            break
                if(tweets_scraped==num_tweets):
                    break
                time.sleep(60) # Time delay to make sure that our bot doesn't get banned
            else:
                logger.error(f"SearchResults returned None")
                print("Error. Search results returned None")
                break
        except KeyboardInterrupt as e:
            save_to_file(extracted_data,"extracted_data")
            save_to_file(hashed_data,"hashed_data")
            logger.info(f"Scraping STOPPED. Scraped {len(extracted_data)}/{num_tweets} tweets.")
            raise SystemExit(e)
        except QueryLengthExceededError as e:
            logger.exception(f"SCRAPING Query length exceeded 512 characters. {e}")
            raise
        except Exception as e:
            logger.exception(f"SCRAPING {e}")
            continue

    save_to_file(extracted_data,"extracted_data")
    save_to_file(hashed_data,"hashed_data")
    logger.info(f"Scraping COMPLETED Scraped {len(extracted_data)}/{num_tweets} tweets.")
    print("\n\nDONE")


if __name__=="__main__":
    try:
        num_tweets = int(sys.argv[1])
    except IndexError:
        print("ERROR \n Enter the number of tweets to be scraped as Command line argument (int)!")
        raise SystemExit
    scrape(bot=Bot(), num_tweets=num_tweets)
