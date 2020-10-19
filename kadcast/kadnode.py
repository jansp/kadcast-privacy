import random
import operator
import seed_handler
import ipaddress
from typing import Tuple
from kadmessages import *
from helpers import Connection, Block
import itertools

KAD_ID_LEN: int = 160


class Node:
    def __init__(self, ip: ipaddress.IPv4Address = None, kad_id: int = None, env=None, ip_to_node: dict = None, use_dandelion=False, dand_q=0.5, latencies=[]):
        self.use_dandelion = use_dandelion
        self.latencies = latencies
        self.dand_q = dand_q
        self.kad_k = 20
        self.kad_alpha = 3
        self.kad_beta = 1
        self.env = env
        self.connection = Connection(env)
        self.ip_to_node = ip_to_node
        self.done_blocks = {}  # block_id: is_done
        self.max_seen_height = {}  # max seen height of block_id, int:int
        self.seen_broadcasts = {}  # int : bool
        self.blocks = {}  # int : Block
        self.block_source = {}  # BLOCK_ID: ipaddress.IPv4Address
        self.block_timestamps = {}  # BLOCK_ID: int[timestamp]
        self.non_empty_buckets = set()
        self.block_map = {}  # BLOCK_ID: (ipadr, timestamp)
        self.ip = ip
        self.kad_id = kad_id
        self.looking_for = set()
        self.queried = {int: set()}

        seed = seed_handler.load_seed()
        random.seed(seed)

        self.buckets = {}  # bucket: [(ip,id)], starts from 0

        for i in range(KAD_ID_LEN):
            self.buckets[i] = []

    def distance(self, id_b: int) -> int:
        return self.kad_id ^ id_b

    def id_to_bucket_index(self, id_b: int) -> int:
        """Returns bucket_index for node with id 'id_b', starting from 0"""
        dist = self.distance(id_b)
        for i in range(KAD_ID_LEN):
            if pow(2, i) <= dist < pow(2, i + 1):
                return i

    def random_ip_from_all_peers(self, visited_hops=None):
        if visited_hops is None:
            visited_hops = set()

        all_ips = set()
        for i in self.non_empty_buckets:
            for ip_id_pair in self.buckets[i]:
                all_ips.add(ip_id_pair[0])

        if not all_ips.difference(visited_hops):
            return None

        return random.choice(tuple(all_ips.difference(visited_hops)))

    def update_bucket(self, ip_id_pair: (ipaddress.IPv4Address, int)):
        assert isinstance(ip_id_pair, tuple) and list(map(type, ip_id_pair)) == [ipaddress.IPv4Address, int], "ip_id_pair is not of type (ipaddress.IPv4Address, int): %r" % ip_id_pair
        ip_b, id_b = ip_id_pair

        if self.kad_id == id_b:
            return

        bucket_idx = self.id_to_bucket_index(id_b)
        bucket = self.buckets[bucket_idx]
        ips = [i[0] for i in bucket]  # list of all ip addr in bucket
        self.non_empty_buckets.add(bucket_idx)
        if ip_b in ips:
            idx = ips.index(ip_b)
            del bucket[idx]
            bucket.append((ip_b, id_b))
        else:  # ip not found in bucket
            if len(bucket) < self.kad_k:
                bucket.append((ip_b, id_b))
            else:
                # TODO ping last recently seen node, drop only if no answer, not always
                del bucket[0]
                bucket.append((ip_b, id_b))

    def find_k_closest_nodes(self, target_id: int) -> [(ipaddress.IPv4Address, int)]:
        flat = [y for x in self.buckets.values() for y in x]
        flat.sort(key=lambda x: distance(target_id, x[1]))

        return flat[:self.kad_k]

    def init_broadcast(self, block: 'Block', anon_phase=True):
        if self.use_dandelion and anon_phase:
            self.forward_block(block)
            return

        startheight = KAD_ID_LEN
        self.done_blocks[block.b_id] = True
        self.blocks[block.b_id] = block

        if block.b_id not in self.max_seen_height:
            self.max_seen_height[block.b_id] = startheight

        self.broadcast_block(block)

    def forward_block(self, block: 'Block', visited_hops=None):
        if visited_hops is None:
            visited_hops = set()

        rand_ip = self.random_ip_from_all_peers(visited_hops)
        visited_hops.add(rand_ip)

        self.send_forward(rand_ip, block, visited_hops=visited_hops)

    def broadcast_block(self, block: 'Block'):
        height = self.max_seen_height[block.b_id]
        del self.max_seen_height[block.b_id]

        if height < 0:
            return

        bucket_idx = height - 1
        d = 1
        while True:
            if bucket_idx < 0 or bucket_idx >= KAD_ID_LEN:
                break

            if not self.buckets[bucket_idx]:
                bucket_idx -= 1
                continue

            #print("%d: Node %d broadcasting block %d at height %d" % (self.env.now, self.kad_id, block.b_id, bucket_idx))
            if len(self.buckets[bucket_idx]) < self.kad_beta:
                to_query = len(self.buckets[bucket_idx])
            else:
                to_query = self.kad_beta

            all_adr = [elem[0] for elem in self.buckets[bucket_idx]]
            adr_list = random.sample(all_adr, to_query)
            #print("Receivers: ", end='')
            #print(list(map(lambda x: self.ip_to_node[x].kad_id, adr_list)))
            while self.ip in adr_list:
                adr_list = random.sample(all_adr, to_query)

            for adr in adr_list:
                self.send_block(adr, block, bucket_idx, d)
                d += 1

            bucket_idx -= 1

    def send_block(self, adr, block, height, d):
        self.send_broadcast_msg(adr, block, height)

    def send_forward(self, adr, block, visited_hops, d=0):
        self.send_forward_msg(adr, block, visited_hops)

    def send_msg(self, msg: BaseMessage, ip: int):
        if ip == self.ip:
            return

        #print("%d: SENT %s %s -> %s (%d -> %d)" % (
        #  self.env.now, msg, self.ip, ip, self.kad_id, self.ip_to_node[ip].kad_id))

        node = self.ip_to_node[ip]

        delay = random.choice(self.latencies)
        node.connection.put(msg, delay)

    # MESSAGE SENDING
    def send_ping(self, ip: ipaddress.IPv4Address):
        self.send_msg(Ping(self), ip)

    def send_pong(self, ip: ipaddress.IPv4Address):
        self.send_msg(Pong(self), ip)

    def send_find_node(self, ip: ipaddress.IPv4Address, target_id: int):
        self.send_msg(FindNode(self, target_id), ip)

    def send_nodes(self, ip: ipaddress.IPv4Address, target_id: int, node_list: [(ipaddress.IPv4Address, int)]):
        self.send_msg(Nodes(self, target_id, node_list), ip)

    def send_broadcast_msg(self, ip: ipaddress.IPv4Address, block: 'Block', height: int):
        self.send_msg(Broadcast(self, block, height), ip)
        #print("%d: Node %s sent TX %d" % (self.env.now, self.ip, block.b_id))

    def send_forward_msg(self, ip: ipaddress.IPv4Address, block: 'Block', visited_hops):
        self.send_msg(Forward(self, block, visited_hops), ip)

    # MESSAGE HANDLING
    def handle_ping(self, ip_id_pair: (ipaddress.IPv4Address, int)) -> None:
        self.update_bucket(ip_id_pair)
        self.send_pong(ip_id_pair[0])

    def handle_pong(self, ip_id_pair: (ipaddress.IPv4Address, int)) -> None:
        self.update_bucket(ip_id_pair)

    def handle_find_node(self, ip_id_pair: (ipaddress.IPv4Address, int), target_id: int) -> None:
        self.update_bucket(ip_id_pair)
        k_closest = self.find_k_closest_nodes(target_id)
        self.send_nodes(ip_id_pair[0], target_id, k_closest)

    def handle_forward(self, ip_id_pair: (ipaddress.IPv4Address, int), block: 'Block', visited_hops):
        #print("%d: %s RECEIVED FORWARD %d FROM %s" % (
        # self.env.now, self.ip, block.b_id, ip_id_pair[0]))

        if block.b_id not in self.block_source:
            (ip, _) = ip_id_pair
            self.block_source[block.b_id] = ip
            self.block_timestamps[block.b_id] = self.env.now
            self.block_map[block.b_id] = (ip, self.env.now)

        unif = random.uniform(0, 1)
        if unif <= self.dand_q:
            self.init_broadcast(block, anon_phase=False)
        else:
            # init broadcast if no unvisited hops left
            if visited_hops is None:
                self.init_broadcast(block, anon_phase=False)
            # keep forwarding
            else:
                self.forward_block(block, visited_hops)

    def handle_broadcast(self, ip_id_pair: (ipaddress.IPv4Address, int), block: 'Block', height: int) -> None:
        #print("%d: %s RECEIVED BROADCAST %d FROM %s AT HEIGHT %d " % (self.env.now, self.ip, block.b_id, ip_id_pair[0], height))
        if block.b_id in self.seen_broadcasts and self.seen_broadcasts[block.b_id]:
            return

        self.seen_broadcasts[block.b_id] = True

        (ip, id) = ip_id_pair
        #self.block_source[ip] = block.b_id
        if block.b_id not in self.block_source:
            self.block_source[block.b_id] = ip
            self.block_timestamps[block.b_id] = self.env.now
            self.block_map[block.b_id] = (ip, self.env.now)

        if block.b_id in self.blocks:
            return

        if block.b_id not in self.max_seen_height:
            self.max_seen_height[block.b_id] = height
        else:
            self.max_seen_height[block.b_id] = max(height, self.max_seen_height[block.b_id])

        self.blocks[block.b_id] = block
        self.done_blocks[block.b_id] = True

        self.broadcast_block(block)

    def handle_message(self):
        while True:
            msg = yield self.connection.get()
            if msg.sender.ip == self.ip:
                return

            #if msg.sender.ip not in self.ip_to_node:
            #    self.ip_to_node[msg.sender.ip] = msg.sender

            #print("Node %d with IP %s received %s message from node %d with IP %s at time %d" % (self.kad_id, self.ip, msg, msg.sender.kad_id, msg.sender.ip, self.env.now))
            #print("%d: RECEIVED %s %s <- %s (%d <- %d)" % (self.env.now, msg, self.ip, msg.sender.ip, self.kad_id, msg.sender.kad_id))
            if isinstance(msg, Ping):
                self.handle_ping((msg.sender.ip, msg.sender.kad_id))

            if isinstance(msg, Pong):
                self.handle_pong((msg.sender.ip, msg.sender.kad_id))

            if isinstance(msg, FindNode):
                self.handle_find_node((msg.sender.ip, msg.sender.kad_id), msg.target_id)

            if isinstance(msg, Nodes):
                self.handle_nodes((msg.sender.ip, msg.sender.kad_id), msg.target_id, msg.node_list)

            if isinstance(msg, Broadcast):
                self.handle_broadcast((msg.sender.ip, msg.sender.kad_id), msg.block, msg.height)

            if isinstance(msg, Forward):
                self.handle_forward((msg.sender.ip, msg.sender.kad_id), msg.block, msg.visited_hops)

    def bootstrap(self, ips):
        for ip in ips:
            self.send_ping(ip)

        self.env.timeout(0).callbacks.append(lambda _: self.init_lookup(self.kad_id))
        self.env.timeout(3000).callbacks.append(lambda _: self.refresh_buckets())
        self.env.timeout(300000).callbacks.append(lambda _: self.refresh_buckets())
        #self.env.timeout(100000).callbacks.append(lambda _: self.refresh_buckets())

    def bucket_refresh(self, filterlist):
        for id_to_find in filterlist:
            yield self.env.timeout(400)
            if self.id_to_bucket_index(id_to_find) not in self.non_empty_buckets:
                self.init_lookup(id_to_find)

        #if filterlist is not None and filterlist:
        #    id_to_find = filterlist.pop()
        #    if self.id_to_bucket_index(id_to_find) not in self.non_empty_buckets:
        #        self.init_lookup(id_to_find)

        #    self.env.process(self.bucket_refresh(filterlist))

    def refresh_buckets(self):
        min_max_list_all = ((2 ** i, 2 ** (i + 1)) for i in range(KAD_ID_LEN))
        itermap = map(lambda z: self.kad_id ^ random.randrange(*z), min_max_list_all)
        filterlist = list(filter(lambda y: self.id_to_bucket_index(y) not in self.non_empty_buckets, itermap))
        bucket_proc = self.env.process(self.bucket_refresh(filterlist))
        #for id_to_find in filterlist:
        #    self.init_lookup(id_to_find)

    def init_lookup(self, target_id):
        if target_id in self.looking_for:
            return

        k_closest = self.find_k_closest_nodes(target_id)

        self.looking_for.add(target_id)
        self.queried[target_id] = set()

        for (ip, id) in k_closest[:self.kad_alpha]:
            self.send_find_node(ip, target_id)
            self.queried[target_id].add(id)

    def handle_nodes(self, ip_id_pair: (ipaddress.IPv4Address, int), target_id: int, node_list: [(ipaddress.IPv4Address, int)]) -> None:
        if target_id not in self.looking_for:
            #print("NOT LOOKING FOR THIS ID (ANYMORE)")
            return

        if not node_list:
            return

        k_closest_old = self.find_k_closest_nodes(target_id)

        for elem in node_list:
            self.update_bucket(elem)
            if elem[1] == target_id:
                # found node id
                #print("found node id")
                del self.queried[target_id]
                self.looking_for.remove(target_id)
                return

        k_closest_new = self.find_k_closest_nodes(target_id)
        if distance(k_closest_new[-1][1], target_id) < distance(k_closest_old[-1][1], target_id):
            # progress
            node_list_ids = (y for (x, y) in node_list)

            to_query_ids_filter = filter(lambda x: x not in self.queried[target_id], node_list_ids)

            to_query_ids = itertools.islice(to_query_ids_filter, self.kad_alpha)
            #print(len(list(to_query_ids)))

            to_query_nodes = filter(lambda xy: xy[1] in to_query_ids, node_list)

            for (ip, id) in to_query_nodes:
                self.queried[target_id].add(id)
                self.send_find_node(ip, target_id)
        else:
            #print("NO PROGRESS looking up %d, stopping lookup..." % target_id)
            #del self.queried[target_id]
            self.looking_for.remove(target_id)
            #self.env.timeout(1000).callbacks.append(lambda _: self.stop_lookup(target_id))

    def stop_lookup(self, target_id):
        if target_id in self.looking_for:
            self.looking_for.remove(target_id)
            #print("Stopped lookup of %d" % target_id)


def distance(id_a: int, id_b: int) -> int:
    return id_a ^ id_b
