import simpy
import ipaddress
import random
import kadnode
import seed_handler
from helpers import Block

RANDOM_SEED = 42
SIM_DURATION = 2000000
NUM_NODES = 256


ip_to_node = {}
id_to_node = {}


random.seed(RANDOM_SEED)
seed_handler.save_seed(RANDOM_SEED)
env = simpy.Environment()


def print_at(time, str):
    env.timeout(time).callbacks.append(lambda _: print(str))

ip_list = list(map(ipaddress.ip_address, random.sample(range(4294967295), NUM_NODES)))
#id_list = list(random.sample(range(2**kadnode.KAD_ID_LEN), NUM_NODES))
id_list = list(range(NUM_NODES))

for i in range(NUM_NODES):
    #print(ip_to_node)
    n = kadnode.Node(ip_list[i], id_list[i], env, ip_to_node)
    ip_to_node[ip_list[i]] = n
    id_to_node[id_list[i]] = n
    env.process(n.handle_message())



for ip in ip_to_node:
    ip_to_node[ip_list[0]].send_ping(ip)

for ip in ip_to_node:
    ip_to_node[ip].bootstrap([ip_list[0]])
    env.run(env.now + 3000)


env.run(env.now + 200000)
id_to_node[id_list[0]].init_broadcast(Block(4,data="LOL"))

#env.run(until=env.now+2000)
#id_to_node[id_list[0]].init_broadcast(Block(1,data="LOL"))
#env.run(until=env.now+2000)
#id_to_node[id_list[1]].init_broadcast(Block(7,data="LOL"))

env.run(until=SIM_DURATION)


for ip in ip_to_node:
    print("Node %d received blocks: " % ip_to_node[ip].kad_id, end='')
    print(list(ip_to_node[ip].blocks))

#print(id_to_node[255].buckets)
#print(id_to_node[id_list[252]].find_k_closest_nodes(255))
print(id_to_node[id_list[255]].buckets)