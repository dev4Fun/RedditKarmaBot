import logging
import random
from time import sleep

import praw

from store import dump_pickled, read_pickled_set

submission_reply_list = ["Nice", "up up", "nice job, friend",
                         "I like your creativity", "Very nice"]

comment_reply_list = ["Get my upvote", "Here is upvote for you", "Free karma for you", "I like you",
                      "You seem like a nice person"]


class RedditBot:
    def __init__(self, credentials: dict):
        self.credentials = credentials

        username = credentials['username']
        self.credentials['user_agent'] = f"testscript by /u/{username}"

        self.reddit_client = praw.Reddit(**self.credentials)
        self.passed_submissions = read_pickled_set(f"submissions-{username}.pickle")

    @property
    def username(self):
        return self.credentials['username']

    def work_on_subreddit(self, subreddit: str, **generator_kwargs):
        if 'limit' not in generator_kwargs:
            generator_kwargs['limit'] = 60

        try:
            submissions = list(self.reddit_client.subreddit(subreddit).new(**generator_kwargs))
            for submission in submissions:
                self._process_submission(submission)
        except Exception as ex:
            error_message = str(ex)
            self._retry_rate_limited_failure(error_message, self.work_on_subreddit, subreddit, **generator_kwargs)
        finally:
            dump_pickled(self.passed_submissions, f"submissions-{self.username}.pickle")

    def _process_submission(self, submission):
        submission_id = submission.id
        if submission_id not in self.passed_submissions:
            comments = submission.comments.list()
            if len(comments) < 12:

                submission_reply = random.choice(submission_reply_list)
                submission.upvote()
                submission.reply(submission_reply)
                self.passed_submissions.add(submission_id)

                comments_to_ignore = self._compute_comments_to_ignore(comments)
                comment_count = None
                if not comments_to_ignore:
                    comment_count = self._process_comments(comments)

                logging.info(
                    f"{self.username} - Processed '{submission.title}'." +
                    (f" Upvoted and replied to {comment_count} comments" if comment_count else ""))

    def _retry_rate_limited_failure(self, error_msg, func, *args, **kwargs):
        error_msg = error_msg.lower()
        search_term = "try again in "
        if search_term in error_msg:
            minute_idx = error_msg.index(search_term) + len(search_term)
            if error_msg[minute_idx].isdigit():
                digits = [error_msg[minute_idx]]
                if error_msg[minute_idx + 1].isdigit():
                    digits.append(error_msg[minute_idx + 1])
                wait_time_in_min = int(''.join(digits))
                logging.info(f"{self.username} will attempt a second run after waiting for {wait_time_in_min} minutes")
                wait_time_sec = wait_time_in_min * 60
                sleep(random.randint(wait_time_sec + 10))
                func(*args, **kwargs)

    def _compute_comments_to_ignore(self, comments) -> dict:
        to_ignore = {}
        for comment in comments:
            if comment.author and comment.author.name == self.username:
                to_ignore[comment.id] = comment
            for reply in comment.replies:
                if reply.author and reply.author.name == self.username:
                    to_ignore[reply.id] = reply
        return to_ignore

    def _process_comments(self, comments):
        num_of_replies = round(len(comments) * 0.35)
        comments_to_leave = iter(random.sample(comment_reply_list, num_of_replies + 1))
        for comment in random.sample(comments, num_of_replies):
            comment.upvote()
            sleep(random.randint(2, 3))
            comment.reply(next(comments_to_leave, random.choice(comment_reply_list)))
        return num_of_replies
