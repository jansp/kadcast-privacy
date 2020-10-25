from random import choice
from ipaddress import IPv4Address


def random_ip_from_all_peers(n, visited_hops=None):
    if visited_hops is None:
        visited_hops = set()

    all_ips = set()
    for i in n.non_empty_buckets:
        for ip_id_pair in n.buckets[i]:
            all_ips.add(ip_id_pair[0])

    if not all_ips.difference(visited_hops):
        return None

    return choice(tuple(all_ips.difference(visited_hops)))


class Node:
    def __init__(self, ip: IPv4Address = None, kad_id: int = None):
        self.done_blocks = {}  # block_id: is_done
        self.max_seen_height = {}  # max seen height of block_id, int:int
        self.seen_broadcasts = {}  # int : bool
        self.blocks = {}  # int : Block
        self.block_source = {}  # BLOCK_ID: IPv4Address
        self.block_timestamps = {}  # BLOCK_ID: int[timestamp]
        self.block_height = {}  # BLOCK_ID: height
        self.block_map = {}  # BLOCK_ID: (ipadr, timestamp)
        self.ip = ip
        self.kad_id = kad_id
        self.looking_for = {}
        self.queried = {int: set()}
        self.buckets = {}  # bucket: {ip: id}, starts from 0
        #self.node_heap = []

    def __hash__(self):
        return hash(self.ip_id_pair())

    def ip_id_pair(self):
        return self.ip, self.kad_id
