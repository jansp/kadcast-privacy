import random
import ipaddress
from typing import Tuple
from kadmessages import *
from helpers import Connection, Block

KAD_ID_LEN: int = 4


class Node:
    def __init__(self, ip: ipaddress.IPv4Address = None, kad_id: int = None, env = None, ip_to_node: dict = None, seed = None):
        self.kad_k = 20
        self.kad_alpha = 3
        self.kad_beta = 3
        self.env = env
        self.connection = Connection(env, 10)
        self.ip_to_node = ip_to_node
        self.node_lookup_map = {} # dict({int: (ipaddress.IPv4Address, int, bool)}) # distance/or id? <- TODO check? : (ip. id, mark_queried)
        self.done_blocks = {} # block_id: is_done
        self.max_seen_height = {} # max seen height of block_id, int:int
        self.seen_broadcasts = {} # int : bool
        self.blocks = {} # int : Block

        random.seed(seed)

        self.buckets = {} # bucket: [(ip,id)]


        for i in range(KAD_ID_LEN):
            self.buckets[i] = []

        if ip is None:
            # TODO check if ip already used
            self.ip = random_ip()
        else:
            assert isinstance(ip, ipaddress.IPv4Address), "ip is not of type ipaddress.IPv4Address: %r" % ip
            self.ip = ip

        if kad_id is None:
            # TODO check if id already used
            self.kad_id = random.getrandbits(KAD_ID_LEN)
        else:
            assert isinstance(kad_id, int), "kad_id is not of type int: %r" % kad_id
            self.kad_id = kad_id

    def distance(self, id_b: int) -> int:
        return self.kad_id ^ id_b

    def id_to_bucket_index(self, id_b: int) -> int:
        """Returns bucket_index for node with id 'id_b', starting from 0"""
        dist = self.distance(id_b)
        for i in range(KAD_ID_LEN):
            if pow(2, i) <= dist < pow(2, i + 1):
                return i

    def random_address_from_bucket(self, bucket: int) -> str:
        return random.choice(self.buckets[bucket])[0]

    def update_bucket(self, ip_id_pair: (ipaddress.IPv4Address, int)):
        assert isinstance(ip_id_pair, tuple) and list(map(type, ip_id_pair)) == [ipaddress.IPv4Address, int], "ip_id_pair is not of type (ipaddress.IPv4Address, int): %r" % ip_id_pair
        ip_b, id_b = ip_id_pair

        if self.kad_id == id_b:
            return

        bucket = self.buckets[self.id_to_bucket_index(id_b)]
        ips = [i[0] for i in bucket] # list of all ip addr in bucket
        if ip_b in ips:
            #TODO optimize to don't double check list
            idx = ips.index(ip_b)
            del bucket[idx]
            bucket.append((ip_b, id_b))
        else: # ip not found in bucket
            if len(bucket) < self.kad_k:
                bucket.append((ip_b, id_b))
            else:
                # TODO ping last recently seen node, drop only if no answer, not always
                del bucket[0]
                bucket.append((ip_b, id_b))

    def to_ip_id_pair(self) -> Tuple[ipaddress.IPv4Address, int]:
        return self.ip, self.kad_id

    def find_k_closest_nodes(self, target_id: int) -> dict({int: (ipaddress.IPv4Address, int)}):
        #TODO check correctness
        closest_nodes = {} # dict({int: (ipaddress.IPv4Address, int)}) # distance: (ip, id)
        target_bucket = self.id_to_bucket_index(target_id)

        for elem in self.buckets[target_bucket]:
            dist = distance(target_id, elem[1])
            closest_nodes[dist] = elem

        remain_n = self.kad_k - len(closest_nodes)
        if remain_n > 0:
            for i in range(KAD_ID_LEN):
                cur_bucket = self.buckets[i]
                for elem in cur_bucket:
                    dist = distance(target_id, elem[1])
                    if dist not in closest_nodes.keys(): #TODO really correct?
                        closest_nodes[dist] = elem
                    if len(closest_nodes) > self.kad_k: #TODO really correct?
                        del closest_nodes[max(closest_nodes.keys())]

        return closest_nodes

    def init_broadcast(self, block: 'Block'):
        startheight = KAD_ID_LEN
        self.done_blocks[block.b_id] = True
        self.blocks[block.b_id] = block

        if block.b_id not in self.max_seen_height:
            self.max_seen_height[block.b_id] = startheight

        self.broadcast_block(block)

    def broadcast_block(self, block: 'Block'):
        height = self.max_seen_height[block.b_id]
        del self.max_seen_height[block.b_id]

        if height < 0:
            return

        bucket_idx = height - 1
        while True:
            if bucket_idx < 0 or bucket_idx >= KAD_ID_LEN:
                break


            if len(self.buckets[bucket_idx]) == 0:
                bucket_idx -= 1
                continue

            #print("%d broadcasting at height %d" % (self.kad_id, bucket_idx))

            if len(self.buckets[bucket_idx]) < self.kad_beta:
                to_query = len(self.buckets[bucket_idx])
            else:
                to_query = self.kad_beta

            to_query = 1  # TODO remove this line after testing

            all_adr = [elem[0] for elem in self.buckets[bucket_idx]]
            adr_list = random.sample(all_adr, to_query)
            while self.ip in adr_list:
                adr_list = random.sample(all_adr, to_query)

            for adr in adr_list:
                self.send_block(adr, block, bucket_idx)

            bucket_idx -= 1


    def send_block(self, adr, block, height):
        # create chunks here if needed later
        self.send_broadcast_msg(adr, block, height)

    def send_msg(self, msg: BaseMessage, ip: int, delay: int = 10):
        # TODO timeout/if node not reachable
        if ip == self.ip:
            return

        print("%d: SENT %s %s -> %s (%d -> %d)" % (
          self.env.now, msg, self.ip, ip, self.kad_id, self.ip_to_node[ip].kad_id))

        node = self.ip_to_node[ip]

        yield self.env.timeout(delay)
        node.connection.put(msg)

    def send_ping(self, ip: ipaddress.IPv4Address):
        self.env.process(self.send_msg(Ping(self), ip))

    def send_pong(self, ip: ipaddress.IPv4Address):
        self.env.process(self.send_msg(Pong(self), ip))

    def send_nodes(self, ip: ipaddress.IPv4Address, target_id: int, node_list: [(ipaddress.IPv4Address, int)]):
        #TODO correct?
        self.env.process(self.send_msg(Nodes(self, target_id, node_list), ip))

    def send_broadcast_msg(self, ip: ipaddress.IPv4Address, block: 'Block', height: int):
        self.env.process(self.send_msg(Broadcast(self, block, height), ip))



    def handle_ping(self, ip_id_pair: (ipaddress.IPv4Address, int)) -> None:
        self.update_bucket(ip_id_pair)
        self.send_pong(ip_id_pair[0])

    def handle_pong(self, ip_id_pair: (ipaddress.IPv4Address, int)) -> None:
        self.update_bucket(ip_id_pair)

    def handle_find_node(self, ip_id_pair: (ipaddress.IPv4Address, int), target_id: int) -> None:
        self.update_bucket(ip_id_pair)
        k_closest = self.find_k_closest_nodes(target_id)

        node_list = k_closest.values()
        self.send_nodes(ip_id_pair[0], target_id, node_list)


    def handle_nodes(self, ip_id_pair: (ipaddress.IPv4Address, int), target_id: int, node_list: [(ipaddress.IPv4Address, int)]) -> None:
        #TODO check if correct
        if target_id not in self.node_lookup_map:
            return

        query_map = self.node_lookup_map[target_id]

        query_all = True
        for elem in node_list:
            self.update_bucket(elem)

            if elem[1] == target_id:
                # found node id
                del self.node_lookup_map[target_id]
                return

            dist = distance(elem[1], target_id)
            if dist in query_map:
                return # node already known

            n = (elem[0], elem[1], False)
            query_map[dist] = n


            # TODO check if correct
            if len(query_map) > self.kad_k:
                if dist != max(query_map): #TODO really correct?
                    query_all = False

                del query_map[max(query_map)] #TODO really correct?

        self.node_lookup_map[target_id] = query_map
        self.lookup_node(target_id, query_all)


    def handle_request(self, ip_id_pair: (ipaddress.IPv4Address, int), ):
        pass

    def handle_broadcast(self, ip_id_pair: (ipaddress.IPv4Address, int), block: 'Block', height: int) -> None:
        if block.b_id in self.seen_broadcasts and self.seen_broadcasts[block.b_id]:
            return

        self.seen_broadcasts[block.b_id] = True

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
            #print("Node %d with IP %s received %s message from node %d with IP %s at time %d" % (self.kad_id, self.ip, msg, msg.sender.kad_id, msg.sender.ip, self.env.now))
            print("%d: RECEIVED %s %s <- %s (%d <- %d)" % (self.env.now, msg, self.ip, msg.sender.ip, self.kad_id, msg.sender.kad_id))
            if isinstance(msg, Ping):
                #print('Node %d received PING from %s at %d' % (self.kad_id, msg.sender.kad_id, self.env.now))
                self.handle_ping((msg.sender.ip, msg.sender.kad_id))

            if isinstance(msg, Pong):
                #print('Node %d received PONG from %s at %d' % (self.kad_id, msg.sender.kad_id, self.env.now))
                self.handle_pong((msg.sender.ip, msg.sender.kad_id))

            if isinstance(msg, FindNode):
                #print('Node %d received FINDNODE from %s at %d' % (self.kad_id, msg.sender.kad_id, self.env.now))
                self.handle_find_node((msg.sender.ip, msg.sender.kad_id), msg.target_id)

            if isinstance(msg, Nodes):
                self.handle_nodes((msg.sender.ip, msg.sender.kad_id), msg.target_id, msg.node_list)

            if isinstance(msg, Broadcast):
                self.handle_broadcast((msg.sender.ip, msg.sender.kad_id), msg.block, msg.height)

            #if message == 'REQUEST':
            # TODO
            #    pass


    def init_lookup(self, target_id: int):
        # TODO CHECK correctness
        if target_id in self.node_lookup_map.keys():
            return

        k_closest = self.find_k_closest_nodes(target_id)
        query_dict = dict({ int: (ipaddress.IPv4Address, int, bool) })

        for key in k_closest:
            query_dict[key] = (k_closest[key][0], k_closest[key][1], False)

        self.node_lookup_map[target_id] = query_dict

        self.lookup_node(target_id)


    def lookup_node(self, target_id: int, query_all = False):
        #TODO check correctness
        if target_id in self.node_lookup_map:
            return

        target_bucket = self.id_to_bucket_index(target_id)

        if target_id in [i[0] for i in self.buckets[target_bucket]]:
            self.terminate_lookup(target_id)
            return # found in local bucket

        query_map = self.node_lookup_map[target_id]

        to_query = self.kad_alpha
        n_queried = 0

        for elem in query_map:
            if not query_all and to_query == 0:
                break

            (node_addr, node_id, queried) = elem

            if queried:
                n_queried += 1
                continue

            self.send_find_node(node_addr, target_id)
            self.mark_queried(target_id, node_id)
            n_queried += 1
            to_query -= 1

        if n_queried < self.kad_alpha:
            return

        self.env.timeout(10000).callbacks.append(lambda _: self.terminate_lookup(target_id))


    def terminate_lookup(self, target_id: int):
        #TODO check correctness
        if target_id not in self.node_lookup_map:
            return
        del self.node_lookup_map[target_id]


def distance(id_a: int, id_b: int) -> int:
    return id_a ^ id_b


def random_ip() -> ipaddress.IPv4Address:
    return ipaddress.ip_address(random.getrandbits(32))