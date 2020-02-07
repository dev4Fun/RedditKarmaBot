import os
import pickle
from pathlib import Path

persistence_dir = Path(os.path.dirname(os.path.abspath(__file__)))


def read_pickled_set(filename):
    path = persistence_dir.joinpath(filename)
    if path.exists():
        with open(path, 'rb') as sub_f:
            return pickle.load(sub_f)
    else:
        return set()


def dump_pickled(obj, filename):
    path = persistence_dir.joinpath(filename)
    with open(path, "wb") as sub_f:
        pickle.dump(obj, sub_f)
