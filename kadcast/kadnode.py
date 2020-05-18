import random
import seed_handler
import ipaddress
from typing import Tuple
from kadmessages import *
from helpers import Connection, Block

KAD_ID_LEN: int = 4


class Node:
    def __init__(self, ip: ipaddress.IPv4Address = None, kad_id: int = None, env=None, ip_to_node: dict = None):
        self.kad_k = 20
        self.kad_alpha = 3
        self.kad_beta = 1
        self.env = env
        self.connection = Connection(env, 10)
        self.ip_to_node = ip_to_node
        self.node_lookup_map = {}  # dict({int: {int: (ipaddress.IPv4Address, int, bool)}})
        self.done_blocks = {}  # block_id: is_done
        self.max_seen_height = {}  # max seen height of block_id, int:int
        self.seen_broadcasts = {}  # int : bool
        self.blocks = {}  # int : Block
        self.block_source = {}  # ipaddress.IPv4Address: int
        self.block_timestamps = {}
        self.non_empty_buckets = set()
        self.continue_broadcast = env.event()

        seed = seed_handler.load_seed()
        random.seed(seed)

        self.buckets = {}  # bucket: [(ip,id)], starts from 0


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

    def random_address_from_bucket(self, bucket: int):
        try:
            return random.choice(self.buckets[bucket])[0]
        except:
            return self.kad_id

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
            # TODO optimize to don't double check list
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

    def to_ip_id_pair(self) -> Tuple[ipaddress.IPv4Address, int]:
        return self.ip, self.kad_id

    def find_k_closest_nodes(self, target_id: int) -> dict({int: (ipaddress.IPv4Address, int)}):
        closest_nodes = {}  # dict({int: (ipaddress.IPv4Address, int)}) # distance: (ip, id)
        target_bucket = self.id_to_bucket_index(target_id)

        if target_bucket is not None:
            for elem in self.buckets[target_bucket]:
                dist = distance(target_id, elem[1])
                closest_nodes[dist] = (elem[0], elem[1])

        remain_n = self.kad_k - len(closest_nodes)
        if remain_n > 0:
            for i in range(KAD_ID_LEN):
                cur_bucket = self.buckets[i]
                for elem in cur_bucket:
                    dist = distance(target_id, elem[1])
                    if dist not in closest_nodes.keys():
                        closest_nodes[dist] = (elem[0], elem[1])
                    if len(closest_nodes) > self.kad_k:
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
        d = 1
        while True:
            if bucket_idx < 0 or bucket_idx >= KAD_ID_LEN:
                break


            if len(self.buckets[bucket_idx]) == 0:
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
                #self.env.timeout((10-height)*100).callbacks.append(lambda _: self.send_block(adr, block, bucket_idx))
                #self.env.process(self.send_block(adr, block, bucket_idx))
                self.send_block(adr, block, bucket_idx, d)
                d += 1


                #self.env.process(self.env.timeout(100))
                #yield self.env.timeout(100)
                #self.env.run(self.env.now + 100)

            bucket_idx -= 1


    def send_block(self, adr, block, height, d):
        #yield self.env.timeout(100)
        self.send_broadcast_msg(adr, block, height, delay=10*d)

    def send_msg(self, msg: BaseMessage, ip: int, delay: int = 10):
        # TODO timeout/if node not reachable
        if ip == self.ip:
            return

        #print("%d: SENT %s %s -> %s (%d -> %d)" % (
        #  self.env.now, msg, self.ip, ip, self.kad_id, self.ip_to_node[ip].kad_id))

        node = self.ip_to_node[ip]

        yield self.env.timeout(delay)
        node.connection.put(msg)

    def send_ping(self, ip: ipaddress.IPv4Address):
        self.env.process(self.send_msg(Ping(self), ip))

    def send_pong(self, ip: ipaddress.IPv4Address):
        self.env.process(self.send_msg(Pong(self), ip))

    def send_find_node(self, ip: ipaddress.IPv4Address, target_id: int):
        self.env.process(self.send_msg(FindNode(self, target_id), ip))

    def send_nodes(self, ip: ipaddress.IPv4Address, target_id: int, node_list: [(ipaddress.IPv4Address, int)]):
        self.env.process(self.send_msg(Nodes(self, target_id, node_list), ip))

    def send_broadcast_msg(self, ip: ipaddress.IPv4Address, block: 'Block', height: int, delay=10):
        self.env.process(self.send_msg(Broadcast(self, block, height), ip, delay))
        #print("%d: Node %d sent TX %d" % (self.env.now, self.kad_id, block.b_id))



    def handle_ping(self, ip_id_pair: (ipaddress.IPv4Address, int)) -> None:
        self.update_bucket(ip_id_pair)
        self.send_pong(ip_id_pair[0])

    def handle_pong(self, ip_id_pair: (ipaddress.IPv4Address, int)) -> None:
        self.update_bucket(ip_id_pair)

    def handle_find_node(self, ip_id_pair: (ipaddress.IPv4Address, int), target_id: int) -> None:
        self.update_bucket(ip_id_pair)
        k_closest = self.find_k_closest_nodes(target_id)

        node_list = [k_closest[k] for k in sorted(k_closest)]  # sort from close to far
        #print(node_list)
        self.send_nodes(ip_id_pair[0], target_id, node_list)

    # def lookup_process(self, target_id, query_all):
    #     while True:
    #         self.lookup_node(target_id, query_all)
    #         #print("Waiting to continue...")
    #         yield self.continue_lookup
    #         #print("CONTINUE")
    #         self.continue_lookup = self.env.event()

    def handle_nodes(self, ip_id_pair: (ipaddress.IPv4Address, int), target_id: int, node_list: [(ipaddress.IPv4Address, int)]) -> None:
        if target_id not in self.node_lookup_map:
            #print("NOT LOOKING FOR THIS NODE, DISCARDING NODES MESSAGE!")
            return

        query_map = self.node_lookup_map[target_id]
        #print("QUERY MAP")
        #print(query_map)

        query_all = True
        #print("NODE LIST")
        #print(self.kad_id)
        #print(node_list)

        for elem in node_list:
            #print("ID %d, we are %d" % (elem[1], self.kad_id))
            if elem[1] == self.kad_id:
                continue

            self.update_bucket(elem)

            if elem[1] == target_id:
                # found node id
                del self.node_lookup_map[target_id]
                return

            dist = distance(elem[1], target_id)
            if dist in query_map:
                return

            n = (elem[0], elem[1], False)
            query_map[dist] = n


            if len(query_map) > self.kad_k:
                if dist != max(query_map):
                    query_all = False

                del query_map[max(query_map)]

        self.node_lookup_map[target_id] = query_map
        self.lookup_node(target_id, query_all)

        #lookup_proc = self.env.process(self.lookup_process(target_id, query_all))

        #if query_all:
            #print("ALL %d" % self.kad_id)
        #self.env.timeout(10000).callbacks.append(lambda _: self.terminate_lookup(target_id))
        #yield lookup_proc


    def handle_request(self, ip_id_pair: (ipaddress.IPv4Address, int), ):
        pass

    def handle_broadcast(self, ip_id_pair: (ipaddress.IPv4Address, int), block: 'Block', height: int) -> None:
        #print("%d: %d RECEIVED BROADCAST %d FROM %d AT HEIGHT %d " % (self.env.now, self.kad_id, block.b_id, ip_id_pair[1], height))
        if block.b_id in self.seen_broadcasts and self.seen_broadcasts[block.b_id]:
            return

        self.seen_broadcasts[block.b_id] = True

        (ip, id) = ip_id_pair
        #self.block_source[ip] = block.b_id
        self.block_source[block.b_id] = ip
        self.block_timestamps[block.b_id] = self.env.now

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

            if msg.sender.ip not in self.ip_to_node:
                self.ip_to_node[msg.sender.ip] = msg.sender

            #self.update_bucket((msg.sender.ip, msg.sender.kad_id))
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

            #if message == 'REQUEST':
            # TODO
            #    pass



    def init_lookup(self, target_id: int):
        #print("%d: INIT LOOKUP %d -> %d" % (self.env.now, self.kad_id, target_id))
        if target_id in self.node_lookup_map:
            #print("LOOKUP ALREADY IN PROCESS!")
            return

        k_closest = self.find_k_closest_nodes(target_id)
        query_dict = {}  # dict({int: (ipaddress.IPv4Address, int, bool)})

        for key in sorted(k_closest):
            query_dict[key] = (k_closest[key][0], k_closest[key][1], False)

        self.node_lookup_map[target_id] = query_dict

        #print("STARTING LOOKUP WITH FOLLOWING LOOKUP MAP:")
        #print(self.node_lookup_map)
        #self.lookup_proc = self.env.process(self.lookup_node(target_id))
        self.lookup_node(target_id)


    def lookup_node(self, target_id: int, query_all = False):
        #print("LOOKUP")
        #self.env.timeout(50000).callbacks.append(lambda _: self.terminate_lookup(target_id))
        #print(self.node_lookup_map)
        if target_id not in self.node_lookup_map:
            #print("Not looking for this node, initialize with init_lookup! NODE %d SEARCHING FOR %d" % (self.kad_id, target_id))
            return

        target_bucket = self.id_to_bucket_index(target_id)
        #print(target_bucket)

        if target_bucket is not None:
            if target_id in [i[1] for i in self.buckets[target_bucket]]:
                self.terminate_lookup(target_id)
                return  # found in local bucket

        query_map = self.node_lookup_map[target_id]

        to_query = self.kad_alpha
        n_queried = 0

        for elem in query_map:
            if not query_all and to_query == 0:
                break

            (node_addr, node_id, queried) = query_map[elem]

            if queried:
                n_queried += 1
                continue

            dist = distance(target_id, node_id)

            self.send_find_node(node_addr, target_id)
            #print("Mark node %d as queried..." % node_id)
            self.node_lookup_map[target_id][dist] = (node_addr, node_id, True)
            #print(self.node_lookup_map[target_id][dist])
            #print(self.node_lookup_map)

            n_queried += 1
            to_query -= 1

        #print("%d: KID: %d Queried %d/%d nodes" % (self.env.now, self.kad_id, n_queried, self.kad_k))
        if n_queried < self.kad_k:
            #self.init_lookup(self.kad_id)
            #print("CONTINUE LOOKUP %d/%d" % (n_queried,self.kad_k))
            #self.env.timeout(1000).callbacks.append(lambda _: self.continue_lookup.succeed())
            #self.lookup_node(target_id)
            return

        self.env.timeout(10000).callbacks.append(lambda _: self.terminate_lookup(target_id))

    def terminate_lookup(self, target_id: int):
        if target_id not in self.node_lookup_map:
            return
        del self.node_lookup_map[target_id]
        #print("%d: NODE %d TERMINATED LOOKUP OF NODE %d" % (self.env.now, self.kad_id, target_id))

    def bootstrap(self, ips):
        for ip in ips:
            self.send_ping(ip)

        self.init_lookup(self.kad_id)
        #self.env.timeout(1000).callbacks.append(lambda _: self.init_lookup(self.kad_id))
        self.env.timeout(3000).callbacks.append(lambda _: self.refresh_buckets())
        self.env.timeout(300000).callbacks.append(lambda _: self.refresh_buckets())
        self.env.timeout(400000).callbacks.append(lambda _: self.refresh_buckets())


    def refresh_buckets(self):
        min_max_list_all = [(2**i, 2**(i+1)) for i in range(KAD_ID_LEN)]
        empty_buckets = set(range(0, KAD_ID_LEN)).difference(self.non_empty_buckets)
        min_max_list = [min_max_list_all[idx] for idx in empty_buckets]


        for minmax in min_max_list:
            id_to_find = self.kad_id ^ random.randrange(*minmax)
            if id_to_find in self.node_lookup_map:
                continue

            #print("Node %d looking for id %d" % (self.kad_id,id_to_find))
            self.init_lookup(id_to_find)

    #def main_loop(self):
    #    while True:
    #        yield self.env.timeout(45)
    #        self.continue_broadcast.succeed()
    #        self.continue_broadcast = self.env.event()


def distance(id_a: int, id_b: int) -> int:
    return id_a ^ id_b


def random_ip() -> ipaddress.IPv4Address:
    return ipaddress.ip_address(random.getrandbits(32))