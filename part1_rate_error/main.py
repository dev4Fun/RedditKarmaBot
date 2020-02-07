import json
import logging
import os
from pathlib import Path

from bot import RedditBot

logging.basicConfig(handlers=[logging.StreamHandler()],
                    level=logging.INFO,
                    format='%(asctime)s %(threadName)-12s %(levelname).4s %(message)s',
                    datefmt='%a %d %H:%M:%S')

current_dir = Path(os.path.dirname(os.path.abspath(__file__)))


def read_all_credentials():
    with open(current_dir.joinpath("new_client_creds.json")) as cred_f:
        return json.load(cred_f)


if __name__ == '__main__':
    credentials = read_all_credentials()
    bot = RedditBot(credentials[0])
    bot.work_on_subreddit('FreeKarma4U', limit=5)
