import time
from src.bot import Bot

confirmation = input("THIS IS DESTRUCTIVE ACTION AND WILL >> DELETE << ALL OF YOUR LIKES!\nDo you want to continue? (y/n)  ")

if(confirmation=="y"):
    print("Deleting...")
    bot = Bot()
    while(True):
        twts = bot.get_likes()
        if(len(twts)==0):
            break
        else:
            for twt in twts:
                bot.delete_like(twt['id'])
            time.sleep(30)
    print("Deleted!")
