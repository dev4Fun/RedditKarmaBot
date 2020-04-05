import logging
import random

import praw

from persistence.store import read_pickled_set, dump_pickled
from utils import rand_wait_sec, rand_wait_min

submission_reply_words = {"Done, my friend!", "Done!", "Here you go", "Wow", "Quality content", "Free upvotes!",
                          "Get that karma", "up you go", "get that upvote", "upvoted!", "Nice post",
                          "Let me give you some upvotes", "Nice", "up up", "nice job, friend",
                          "I like your creativity", "Very nice", "Get on that karma train",
                          "Wanna some free karma? You got it", "Brilliant", "10 out of 10", "Great post",
                          "Get it here", "Karma train is coming", "You are the best", "I like it",
                          "Best content on reddit!", "Spread the love", "Donee"}

comment_reply_words = {"Get my upvote", "Here is upvote for you", "Free karma for you", "I like you",
                       "You seem like a nice person", "Lovely comment", "What a nice thing to say",
                       "Free upvote", "you have to go up", "good comment", "you get my vote", "Hey. Have an upvote!",
                       "Get on it", "woot woot", "Here, take my upvote", "So kind of you", "Did you say free karma?",
                       "you wanna free upvote?"}

submission_reply_list = list(submission_reply_words)
comment_reply_list = list(comment_reply_words)


class RedditBot:
    def __init__(self, credentials: dict, reddit_client=None, all_bot_names=None):
        self.credentials = credentials
        username = credentials['username']
        self.credentials['user_agent'] = f"testscript by /u/{username}"

        self.all_bot_names = all_bot_names if all_bot_names else {username}

        self.reddit_client = reddit_client if reddit_client else praw.Reddit(**self.credentials)

        self.is_broken = self.reddit_client.user.me().is_suspended

        if self.is_broken:
            logging.warning(f"{self.username} is Suspended")
        else:
            self.passed_submissions = read_pickled_set(f"submissions-{username}.pickle")

            self.current_session_comment_ids = set()
            self.current_session_submissions = set()

            self.failure_count = 0
            self.is_terminating = False

    @property
    def username(self):
        return self.credentials['username']

    @property
    def bot_comment_karma(self):
        return self.reddit_client.redditor(self.username).comment_karma

    def fetch_submission_ids(self, subreddit, **kwargs):
        return [submission.id for submission in self.reddit_client.subreddit(subreddit).hot(**kwargs)]

    def fetch_new_comments(self, **kwargs):
        return [comment.id for comment in self.reddit_client.user.me().comments.new(**kwargs)]

    def parse_submission(self, submission_id=None, url=None):
        try:
            submission = self.reddit_client.submission(id=submission_id, url=url)
            self._process_submission(submission)
        except Exception as ex:
            self._try_handle_exception(ex, self.parse_submission, submission_id)
        finally:
            dump_pickled(self.passed_submissions, f"submissions-{self.username}.pickle")

    def log_comment_karma(self):
        logging.info(f"{self.username} has {self.bot_comment_karma} comment karma")

    def process_posts_on_subreddits(self, subreddits):
        self.work_on_subreddit('+'.join(subreddits), limit=len(subreddits) * 40)

    def work_on_subreddit(self, subreddit: str, **generator_kwargs):
        if 'limit' not in generator_kwargs:
            generator_kwargs['limit'] = 60

        try:
            submissions = list(self.reddit_client.subreddit(subreddit).new(**generator_kwargs))
            for submission in random.sample(submissions, round(len(submissions) * 0.75)):
                self._process_submission(submission)
                rand_wait_sec(1, 2)
        except Exception as ex:
            self._try_handle_exception(ex, self.work_on_subreddit, subreddit, **generator_kwargs)
        finally:
            if not self.is_terminating:
                self.is_terminating = True

                dump_pickled(self.passed_submissions, f"submissions-{self.username}.pickle")
                if self.current_session_submissions:
                    logging.info(
                        f"{self.username} - Statistics: processed submissions - {len(self.current_session_submissions)}, "
                        f"upvoted comments - {len(self.current_session_comment_ids)}")

    def upvote_comment(self, comment_id=None, url=None):
        logging.info(f"{self.username} - Upvoting comment {comment_id}")
        self.reddit_client.comment(id=comment_id, url=url).upvote()

    def _try_handle_exception(self, ex, func, *args, **kwargs):
        self.failure_count += 1
        error_msg = str(ex)
        logging.error(f"bot {self.username} has crushed. Error: {error_msg}")

        if self.failure_count < 5:
            # subtract processed submissions from limit
            if 'limit' in kwargs:
                kwargs['limit'] = max(1, kwargs['limit'] - len(self.current_session_submissions))
            self._retry_rate_limited_failure(error_msg, func, *args, **kwargs)
        elif self.failure_count > 1:
            logging.warning(f"{self.username} has crushed {self.failure_count} times")

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
                rand_wait_min(wait_time_in_min, wait_time_in_min + 1)
                func(*args, **kwargs)

    def _process_submission(self, submission):
        submission_id = submission.id
        rand_wait_sec()
        if submission_id not in self.passed_submissions:
            comments = submission.comments.list()
            rand_wait_sec()
            if len(comments) < 12:
                comments_to_ignore = self._compute_comments_to_ignore(comments)

                # Make sure we don't repeat the comments that been left by this or other bots
                comment_bodies_to_ignore = {comment.body for comment in comments_to_ignore.values()}
                submission_reply = random.choice(submission_reply_list)
                if comments_to_ignore:
                    logging.info(f"{self.username} - found {len(comments_to_ignore)} comments. Skip comment replying")

                    while submission_reply in comment_bodies_to_ignore:
                        submission_reply = random.choice(submission_reply_list)

                submission.upvote()
                rand_wait_sec()
                submission.reply(submission_reply)
                self._mark_submission(submission_id)
                rand_wait_sec()

                comment_count = None
                if not comments_to_ignore:
                    comment_count = self._process_comments(comments)

                logging.info(
                    f"{self.username} - Processed '{submission.title}'." +
                    (f" Upvoted and replied to {comment_count} comments" if comment_count else ""))

    def _compute_comments_to_ignore(self, comments) -> dict:
        to_ignore = {}
        for comment in comments:
            if comment.author and comment.author.name in self.all_bot_names:
                to_ignore[comment.id] = comment
            for reply in comment.replies:
                if reply.author and reply.author.name in self.all_bot_names:
                    to_ignore[reply.id] = reply
        return to_ignore

    def _process_comments(self, comments):
        num_of_replies = round(len(comments) * 0.35)
        comments_to_leave = iter(random.sample(comment_reply_list, num_of_replies + 1))
        for comment in random.sample(comments, num_of_replies):
            comment.upvote()
            rand_wait_sec()
            comment.reply(next(comments_to_leave, random.choice(comment_reply_list)))
            self._mark_comment(comment.id)
        return num_of_replies

    def _mark_submission(self, submission_id):
        self.passed_submissions.add(submission_id)
        self.current_session_submissions.add(submission_id)

    def _mark_comment(self, comment_id):
        self.current_session_comment_ids.add(comment_id)
