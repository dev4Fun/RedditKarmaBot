import random
from time import sleep


def rand_wait_sec(a=None, b=None):
    if not a:
        a = 2
    if not b:
        b = 3
    sleep(random.randint(a, b))


def rand_wait_min(a=None, b=None):
    a = a if not a else a * 60
    b = b if not b else b * 60
    rand_wait_sec(a, b)
