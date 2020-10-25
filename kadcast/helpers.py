import simpy
from itertools import groupby, cycle, chain, islice, zip_longest
import functools
from ipaddress import IPv4Address
from random import shuffle
#from gmpy import bit_length, mpz
import math

import heapq
from collections import OrderedDict
import operator

kad_k = 20
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
    buckets = n.buckets

    index = id_to_bucket_index(n.kad_id, target_id)
    idx_left = sorted(list(filter(lambda x: x < index, buckets.keys())))
    idx_right = sorted(list(filter(lambda x: x > index, buckets.keys())), reverse=True)

    noleft = False
    noright = False

    nodes = []
    try:
        for node in buckets[index].items():
            heapq.heappush(nodes, (distance(target_id, node[1]), node))
    except:
        pass
    while not (noleft and noright) and len(nodes) < kad_k:
        try:
            for node in buckets[idx_left.pop()].items():
                #print(node)
                heapq.heappush(nodes, (distance(target_id, node[1]), node))
        except:
            noleft = True

        try:
            for node in buckets[idx_right.pop()].items():
                #print(node)
                heapq.heappush(nodes, (distance(target_id, node[1]), node))
        except:
            noright = True


    # flat = (b.items() for b in buckets.values())
    # flat = chain.from_iterable(flat)
    # flat_sorted = sorted(flat, key=lambda x: distance(target_id, x[1]))
    # return list(islice(flat_sorted, kad_k))
    return list(map(operator.itemgetter(1), heapq.nsmallest(kad_k, nodes)))


# class Traverser:
#     def __init__(self, n, start_node):
#         index = id_to_bucket_index(n.kad_id, start_node)
#         try:
#             self.current_nodes = OrderedDict(n.buckets[index].items())
#         except KeyError:
#             self.current_nodes = OrderedDict()
#
#         idx_left = sorted(list(filter(lambda x: x < index, n.buckets.keys())))
#         idx_right = sorted(list(filter(lambda x: x > index, n.buckets.keys())), reverse=True)
#         self.left_buckets = (OrderedDict(n.buckets[i].items()) for i in idx_left)
#         self.right_buckets = (OrderedDict(n.buckets[i].items()) for i in idx_right)
#         self.left = True
#         self.stop_left = False
#         self.stop_right = False
#
#     def __iter__(self):
#         return self
#
#     def __next__(self):
#         """
#         Pop an item from the left subtree, then right, then left, etc.
#         """
#         if self.current_nodes:
#             return self.current_nodes.popitem()
#
#         if self.left and not self.stop_left:
#             try:
#                 self.current_nodes = next(self.left_buckets)
#                 self.left = False
#                 return next(self)
#             except StopIteration:
#                 self.left = False
#                 self.stop_left = True
#                 return next(self)
#
#         if not self.stop_right:
#             try:
#                 self.current_nodes = next(self.right_buckets)
#                 self.left = True
#                 return next(self)
#             except StopIteration:
#                 self.left = True
#                 self.stop_right = True
#                 return next(self)
#
#         raise StopIteration
#
#
# def find_k_closest_nodes(n, target_id: int) -> [(IPv4Address, int)]:
#     nodes = []
#     x = 0
#     for neighbor in Traverser(n, target_id):
#         x += 1
#         heapq.heappush(nodes, (distance(target_id, neighbor[1]), neighbor))
#         if x >= kad_k:
#             break
#
#     return list(map(operator.itemgetter(1), heapq.nsmallest(kad_k, nodes)))
