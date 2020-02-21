import simpy
import ipaddress
import random
import kadnode
from helpers import Block

RANDOM_SEED = 42
SIM_DURATION = 10000000
NUM_NODES = 10 # max 16 at cur id_len


ip_to_node = {}
id_to_node = {}
nodes = [] # list of ip adr

random.seed(RANDOM_SEED)
env = simpy.Environment()


def print_at(time, str):
    env.timeout(time).callbacks.append(lambda _: print(str))

rand_ips = list(map(ipaddress.ip_address, random.sample(range(4294967295), NUM_NODES)))
rand_kids = random.sample(range((kadnode.KAD_ID_LEN**2)), NUM_NODES)
rand_kids = range(kadnode.KAD_ID_LEN**2)

for i in range(NUM_NODES):
    n = kadnode.Node(rand_ips[i], rand_kids[i], env, ip_to_node, seed=RANDOM_SEED)
    ip_to_node[rand_ips[i]] = n
    id_to_node[rand_kids[i]] = n
    nodes.append(rand_ips[i])
    env.process(n.handle_message())


for node in ip_to_node:
    env.run(random.randint(env.now+1,env.now+50))
    for node2 in ip_to_node:
        ip_to_node[node].send_ping(node2)


rand_node = random.choice(nodes)
env.run(2000)
#ip_to_node[rand_ips[0]].init_broadcast(Block(0, "BLOCK NUMMER 0"))
#ip_to_node[rand_ips[1]].init_broadcast(Block(1, "BLOCK NUMMER 1"))
#env.run(env.now+1000)
#print_at(env.now, "Node " + str(ip_to_node[rand_node].kad_id) + " Buckets: " + str(ip_to_node[rand_node].buckets))
#print_at(env.now, [node.kad_id for node in ip_to_node.values()])
n = id_to_node[0]
print("Node %d received blocks: %s " % (n.kad_id, list(n.blocks)))


k_closest = id_to_node[0].find_k_closest_nodes(3)
#print(id_to_node[0].id_to_bucket_index(1))
#print(k_closest)
#print(len(k_closest))
#print(id_to_node[3].buckets)


#id_to_node[0].init_lookup(0)

n = kadnode.Node(ipaddress.ip_address(123), 15, env, ip_to_node, seed=RANDOM_SEED)
ip_to_node[ipaddress.ip_address(123)] = n
id_to_node[999] = n
nodes.append(ipaddress.ip_address(123))
env.process(n.handle_message())

n.bootstrap([rand_ips[0], rand_ips[1], rand_ips[2]])
env.run(until=env.now+200)

n.init_lookup(15)
env.run(until=env.now+2000)
print(n.buckets)

env.run(until=SIM_DURATION)