from kadmessages import *
from ipaddress import IPv4Address
from helpers import distance, latencies, find_k_closest_nodes, kad_k, KAD_ID_LEN, kad_alpha, kad_beta, id_to_bucket_index
from random import uniform, sample
import functools
from kadnode import random_ip_from_all_peers
from connection import Connection
from collections import OrderedDict
from itertools import islice

class SendingToSelf(Exception): pass


use_dandelion = False
dand_q = 0.5
env = None
ip_to_node = {}
connections = {}
latency = None

@functools.lru_cache(maxsize=1)
def init_env(environment):
    global env
    env = environment
    global latency
    latency = latencies()



@functools.lru_cache(maxsize=1)
def init_dandelion(use_dand, q):
    global use_dandelion
    use_dandelion = use_dand
    global dand_q
    dand_q = q


def init_ipnode(ipnode):
    global ip_to_node
    ip_to_node = ipnode
    for ip in ip_to_node:
        connections.setdefault(ip, Connection())


def init_broadcast(ip_id, block: 'Block', anon_phase=True):

    if use_dandelion and anon_phase:
        forward_block(ip_id, block)
        return

    n = ip_to_node[ip_id[0]]
    startheight = KAD_ID_LEN
    n.done_blocks[block.b_id] = True
    n.blocks[block.b_id] = block

    if block.b_id not in n.max_seen_height:
        n.max_seen_height[block.b_id] = startheight

    broadcast_block(n, block)


# MESSAGE SENDING
def send_msg(msg: BaseMessage, ip: IPv4Address, d=0):
    if msg.sender[0] == ip:
        raise SendingToSelf
    # print("%d: SENT %s %s -> %s (%d -> %d)" % (
    #  self.env.now, msg, self.ip, ip, self.kad_id, self.ip_to_node[ip].kad_id))
    delay = next(latency) + d
    connections[ip].put(msg, delay)


def send_ping(ip_id, ip: IPv4Address):
    send_msg(Ping(ip_id), ip)


def send_pong(ip_id, ip: IPv4Address):
    send_msg(Pong(ip_id), ip)


def send_find_node(ip_id, ip: IPv4Address, target_id: int):
    send_msg(FindNode(ip_id, target_id), ip)


def send_nodes(ip_id, ip: IPv4Address, target_id: int, node_list: [(IPv4Address, int)]):
    send_msg(Nodes(ip_id, target_id, node_list), ip)


def send_block(ip_id, adr, block, height, d):
    send_broadcast_msg(ip_id, adr, block, height, d)


def send_forward(ip_id, adr, block, visited_hops, d=0):
    send_forward_msg(ip_id, adr, block, visited_hops)


def send_broadcast_msg(ip_id, ip: IPv4Address, block: 'Block', height: int, delay):
    send_msg(Broadcast(ip_id, block, height), ip, delay)


def send_forward_msg(ip_id, ip: IPv4Address, block: 'Block', visited_hops):
    send_msg(Forward(ip_id, block, visited_hops), ip)


# MESSAGE HANDLING
def handle_ping(ip_id, msg) -> None:
    update_bucket(ip_id, (msg.sender[0], msg.sender[1]))
    send_pong(ip_id, msg.sender[0])


def handle_pong(ip_id, msg) -> None:
    update_bucket(ip_id, (msg.sender[0], msg.sender[1]))


def handle_find_node(ip_id, msg) -> None:
    n = ip_to_node[ip_id[0]]
    update_bucket(ip_id, (msg.sender[0], msg.sender[1]))
    k_closest = find_k_closest_nodes(n, msg.target_id)
    send_nodes(ip_id, msg.sender[0], msg.target_id, k_closest)


def init_lookup(n, target_id):
    if target_id in n.looking_for and n.looking_for[target_id]:
        return

    n.looking_for[target_id] = True
    n.queried[target_id] = set()
    k_closest = find_k_closest_nodes(n, target_id)
    add = n.queried[target_id].add
    for (ip, k_id) in islice(k_closest, kad_alpha):
        send_find_node(n.ip_id_pair(), ip, target_id)
        add(k_id)


def handle_nodes(ip_id, msg): #ip_id_pair: (IPv4Address, int), target_id: int, node_list: [(IPv4Address, int)]) -> None:
    ip_a, kad_id_a = ip_id
    target_id = msg.target_id
    node_list = msg.node_list
    recv = ip_to_node[ip_a]

    if not node_list:
        return
    if not recv.looking_for[target_id]:
        return

    k_closest_old = find_k_closest_nodes(recv, target_id)

    for elem in node_list:
        update_bucket(ip_id, elem)
        if elem[1] == target_id:
            # found node id
            #env.timeout(100).callbacks.append(lambda _: stop_lookup(recv, target_id))
            del recv.queried[target_id]
            recv.looking_for[target_id] = False
            return

    k_closest_new = find_k_closest_nodes(recv, target_id)

    #print(node_list)
    #print(ip_id)
    #print(k_closest_old)
    #p#rint(k_closest_new)
    if distance(k_closest_new[-1][1], target_id) < distance(k_closest_old[-1][1], target_id):
        # progress
        #print("Progress: %d, Target: %d" % (distance(k_closest_new[-1][1], target_id), target_id))
        # TODO can optimize?
        queried = 0
        for (ip, k_id) in node_list:
            if queried >= kad_alpha:
                break
            if k_id not in recv.queried[target_id]:
                try:
                    recv.queried[target_id].add(k_id)
                    queried += 1
                    send_find_node(ip_id, ip, target_id)
                except SendingToSelf:
                    pass
    else:
        #print("NO PROGRESS looking up %d, stopping lookup..." % target_id)
        del recv.queried[target_id]
        recv.looking_for[target_id] = False
        #env.timeout(1000).callbacks.append(lambda _: stop_lookup(recv, target_id))


def stop_lookup(n, target_id):
    try:
        #print("STOPPING LOOKUP")
        n.looking_for[target_id] = False
        del n.queried[target_id]
    except Exception:
        #env.timeout(1000).callbacks.append(lambda _: stop_lookup(n, target_id))
        pass
        #print(e)


def handle_forward(ip_id, msg): #ip_id_pair: (IPv4Address, int), block: 'Block', visited_hops):
    ip = ip_id[0]
    recv = ip_to_node[ip]
    block = msg.block
    visited_hops = msg.visited_hops
    ip_id_pair = msg.sender
    #print("%d: %s RECEIVED FORWARD %d FROM %s" % (
    # env.now, recv.ip, block.b_id, ip_id_pair[0]))

    if block.b_id not in recv.block_source:
        add_block(recv, block.b_id, ip_id_pair[0], -1)  # height -1 when received dur forward
    unif = uniform(0, 1)
    if unif <= dand_q:
        init_broadcast(ip_id, block, anon_phase=False)
    else:
        # init broadcast if no unvisited hops left
        if visited_hops is None:
            init_broadcast(ip_id, block, anon_phase=False)
        # keep forwarding
        else:
            forward_block(ip_id, block, visited_hops)


def handle_broadcast(ip_id, msg): #ip_id_pair: (IPv4Address, int), block: 'Block', height: int) -> None:
    #print("%d: %s RECEIVED BROADCAST %d FROM %s AT HEIGHT %d " % (env.now, recv.ip, block.b_id, ip_id_pair[0], height))
    block = msg.block
    ip_id_pair = msg.sender
    height = msg.height
    recv = ip_to_node[ip_id[0]]
    block_id = block.b_id
    if block_id in recv.seen_broadcasts and recv.seen_broadcasts[block_id]:
        return

    recv.seen_broadcasts[block_id] = True

    if block_id not in recv.block_source:
        add_block(recv, block_id, ip_id_pair[0], height)

    if block_id in recv.blocks:
        return

    if block_id not in recv.max_seen_height:
        recv.max_seen_height[block_id] = height
    else:
        recv.max_seen_height[block_id] = max(height, recv.max_seen_height[block_id])

    recv.blocks[block_id] = block
    recv.done_blocks[block_id] = True

    broadcast_block(recv, block)


msg_handler_dict = {FindNode: handle_find_node, Nodes: handle_nodes, Ping: handle_ping, Pong: handle_pong,
                Broadcast: handle_broadcast, Forward: handle_forward}


def handle_message(ip_id):
    conn_get = connections[ip_id[0]].get

    while True:
        msg = yield conn_get()

        if msg.sender[0] == ip_id[0]:
            print("Sending message to self?")
            return

        #print("Node %d with IP %s received %s message from node %d with IP %s at time %d" % (recv_ipid[1], recv_ipid[0], msg, msg.sender[0], msg.sender[1], env.now))
        # print("%d: RECEIVED %s %s <- %s (%d <- %d)" % (n.env.now, msg, n.ip, msg.sender.ip, n.kad_id, msg.sender.kad_id))

        msg_handler_dict[type(msg)](ip_id, msg)


def forward_block(ip_id, block: 'Block', visited_hops=None):
    if visited_hops is None:
        visited_hops = set()

    rand_ip = random_ip_from_all_peers(ip_to_node[ip_id[0]], visited_hops)
    visited_hops.add(rand_ip)

    send_forward(ip_id, rand_ip, block, visited_hops=visited_hops)


def broadcast_block(n, block: 'Block'):
    height = n.max_seen_height[block.b_id]
    del n.max_seen_height[block.b_id]

    if height < 0:
        return

    bucket_idx = height - 1
    d = 0
    while True:
        if bucket_idx < 0 or bucket_idx >= KAD_ID_LEN:
            break

        try:
            to_query = len(n.buckets[bucket_idx])
            #print("%d: Node %d broadcasting block %d at height %d" % (n.env.now, n.kad_id, block.b_id, bucket_idx))
            if to_query >= kad_beta:
                to_query = kad_beta
        except KeyError:
            bucket_idx -= 1
            continue

        all_adr = n.buckets[bucket_idx].keys()
        query_list = sample(all_adr, to_query)
        #print("Receivers: ", end='')

        #d = 0
        for adr in query_list:
            send_block(n.ip_id_pair(), adr, block, bucket_idx, d)
            d += 100  # delay between sending to next subtree

        bucket_idx -= 1


def add_block(n, block_id, sender_ip, height):
    n.block_source[block_id] = sender_ip
    n.block_timestamps[block_id] = env.now
    n.block_map[block_id] = (sender_ip, env.now)
    n.block_height[block_id] = height


def update_bucket(ip_id_pair_a, ip_id_pair_b: (IPv4Address, int)):
    ip_b, id_b = ip_id_pair_b
    ip_a, id_a = ip_id_pair_a

    if id_a == id_b:
        return

    n = ip_to_node[ip_a]
    buckets = n.buckets

    bucket_idx = id_to_bucket_index(id_a, id_b)
    if bucket_idx not in buckets:
        buckets[bucket_idx] = OrderedDict({ip_b: id_b})
        return

    bucket = buckets[bucket_idx]

    bucket[ip_b] = id_b
    if len(bucket) > kad_k:
        bucket.popitem(last=False)
