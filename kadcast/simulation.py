import simpy
import ipaddress
import random
import kadnode
from helpers import Block

RANDOM_SEED = 42
SIM_DURATION = 10000000
NUM_NODES = 16


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
    n = kadnode.Node(rand_ips[i], rand_kids[i], env, ip_to_node, seed = RANDOM_SEED)
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
ip_to_node[rand_ips[0]].init_broadcast(Block(1, "BLOCK NUMMER 1"))
#ip_to_node[rand_ips[1]].init_broadcast(Block(2, "BLOCK NUMMER 2"))
env.run(env.now+1000)
#print_at(env.now, "Node " + str(ip_to_node[rand_node].kad_id) + " Buckets: " + str(ip_to_node[rand_node].buckets))
#print_at(env.now, [node.kad_id for node in ip_to_node.values()])
#for n in ip_to_node:
#    print("Node %d received blocks: %s " % (ip_to_node[n].kad_id, list(ip_to_node[n].blocks.keys())))


#print(id_to_node[0].buckets)
env.run(until=SIM_DURATION)