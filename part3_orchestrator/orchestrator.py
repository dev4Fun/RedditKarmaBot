import itertools
import random
from concurrent.futures import wait
from concurrent.futures.thread import ThreadPoolExecutor

from bot import RedditBot


class BotOrchestrator:
    def __init__(self, all_credentials: dict, executor=None):
        all_usernames = {cred['username'] for cred in all_credentials}
        self.bots = [RedditBot(creds, all_bot_names=all_usernames) for creds in all_credentials]
        self.executor = executor if executor else ThreadPoolExecutor(max_workers=len(self.bots),
                                                                     thread_name_prefix="RedditBot")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.shutdown(wait=True)

    def parse_different_submissions(self, subreddit, **kwargs):
        submissions = list(random.choice(self.bots).fetch_submission_ids(subreddit, **kwargs))
        submission_ids = iter(submissions)

        futures = []
        bots_iter = itertools.cycle(self.bots)
        for bot in bots_iter:
            submission_id = next(submission_ids, None)
            if not submission_id:
                break
            futures.append(self.executor.submit(bot.parse_submission, submission_id))
        wait(futures)

    def log_karma(self):
        self._submit_to_executor_for_all(lambda bot: bot.log_comment_karma())

    def _submit_to_executor_for_all(self, func, to_wait=False):
        futures = []

        for bot in self.bots:
            futures.append(self.executor.submit(func, bot))
        if to_wait:
            wait(futures)
