import json
import logging
import os
from pathlib import Path

from bot import BotOrchestrator

logging.basicConfig(handlers=[logging.StreamHandler()],
                    level=logging.INFO,
                    format='%(asctime)s %(threadName)-12s %(levelname).4s %(message)s',
                    datefmt='%a %d %H:%M:%S')

current_dir = Path(os.path.dirname(os.path.abspath(__file__)))

# karmawhore is another one
subreddits = ["FreeKarma4U", "FreeKarma4You"]


def read_all_credentials():
    with open(current_dir.joinpath("client_creds.json")) as cred_f:
        return json.load(cred_f)


if __name__ == '__main__':
    credentials = read_all_credentials()

    with BotOrchestrator(credentials) as orchestrator:
        orchestrator.parse_different_submissions("FreeKarma4U+FreeKarma4You+karmawhore", limit=120)
        orchestrator.log_karma()
