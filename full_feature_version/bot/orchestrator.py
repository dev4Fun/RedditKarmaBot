import itertools
import logging
import random
from collections import defaultdict
from concurrent.futures import wait
from concurrent.futures.thread import ThreadPoolExecutor

from bot import RedditBot
from utils import rand_wait_min, rand_wait_sec


class BotOrchestrator:
    def __init__(self, all_credentials: dict, executor=None):
        all_usernames = {cred['username'] for cred in all_credentials}
        self.bots = [RedditBot(creds, all_bot_names=all_usernames) for creds in all_credentials]
        self.bots = [bot for bot in self.bots if not bot.is_broken]  # filter out suspended bots
        self.executor = executor if executor else ThreadPoolExecutor(max_workers=len(self.bots),
                                                                     thread_name_prefix="RedditBot")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.shutdown(wait=True)

    # This will cause bots to process same submissions
    # You will get suspended for it pretty quickly once detected
    def parse_subreddit(self, subreddit: str, **kwargs):
        self._submit_to_executor_for_all(lambda bot: bot.work_on_subreddit(subreddit, **kwargs), to_wait=True)

    def upvote_other_bot_comments(self, iterations=1, comment_sample_size=3):
        session_upvotes = defaultdict(set)

        def do_fetch_comment_ids(bot):
            return [(c_id, bot.username) for c_id in bot.fetch_new_comments(limit=comment_sample_size)]

        def do_upvote_comment(bot, comment_id):
            bot.upvote_comment(comment_id)
            session_upvotes[bot.username].add(comment_id)

        for i_n in range(iterations):
            comment_with_owner = {}
            futures = []
            for bot in self.bots:
                futures.append(self.executor.submit(do_fetch_comment_ids, bot))
            wait(futures)

            for future in futures:
                result = future.result()
                for entry in result:
                    c_id, author = entry[0], entry[1]
                    comment_with_owner[c_id] = author

            comment_ids = list(comment_with_owner.keys())
            random.shuffle(comment_ids)
            comment_id_iter = itertools.cycle(comment_ids)

            futures = []
            for bot in self.bots:
                bot_name = bot.username
                loop_passed = 0
                while True:
                    comment_id = next(comment_id_iter)
                    owner = comment_with_owner[comment_id]

                    # skip your own comments and comments already upvoted
                    if owner != bot_name and comment_id not in session_upvotes[bot_name]:
                        break

                    loop_passed += 1

                    # guard from infinite loop if all comments very upvoted
                    if loop_passed > len(self.bots) + 1:
                        logging.warning(f"All comments have been already upvoted by {bot_name}")
                        break

                futures.append(self.executor.submit(do_upvote_comment, bot, comment_id))

            wait(futures)
            if i_n != iterations - 1:
                logging.info("Waiting between iterations")
                rand_wait_sec(25, 35)

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

    def execute_custom_func(self, fn):
        self._submit_to_executor_for_all(fn)

    def log_karma(self):
        self._submit_to_executor_for_all(lambda bot: bot.log_comment_karma())

    def upvote_comment_sequentially_with_wait(self, comment_id=None, url=None):
        for bot in self.bots:
            bot.upvote_comment(comment_id, url)
            rand_wait_min(1, 2)

    def _submit_to_executor_for_all(self, func, to_wait=False):
        futures = []

        for bot in self.bots:
            futures.append(self.executor.submit(func, bot))
        if to_wait:
            wait(futures)
