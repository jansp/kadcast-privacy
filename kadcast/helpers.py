from itertools import cycle, chain, islice
import functools
from ipaddress import IPv4Address
from random import shuffle
from operator import itemgetter
from functools import cmp_to_key
import numpy as np

kad_k = 60
kad_alpha = 3
kad_beta = 1

KAD_ID_LEN: int = 160


class Block:
    def __init__(self, b_id: int, data=None):
        self.b_id = b_id
        self.data = data

    def __str__(self):
        return "".join(("BLOCK", str(self.b_id)))

    def __repr__(self):
        return "".join(("BLOCK", str(self.b_id)))

    def __hash__(self):
        return hash(self.b_id)


def distance(id_a: int, id_b: int) -> int:
    return id_a ^ id_b


def id_to_bucket_index(id_a: int, id_b: int) -> int:
    """Returns bucket_index for node with id 'id_b', starting from 0"""
    dist = distance(id_a, id_b)
    return dist.bit_length() - 1


# import iplane latencies
@functools.lru_cache(maxsize=1)
def latencies():
    with open("latencies.txt") as f:
        lats = f.readlines()

    lat = [int(x.strip()) for x in lats]
    shuffle(lat)
    return cycle(lat)


def find_k_closest_nodes(n, target_id: int) -> [(IPv4Address, int)]:
    # TODO can optimize?
    def fun(x):
        return distance(target_id, x[1])

    flat = map(dict.items, n.buckets.values())
    flat = chain.from_iterable(flat)
    flat_sorted = sorted(flat, key=fun)
    return flat_sorted[:kad_k]
