import simpy
import ipaddress
import random
import kadnode

RANDOM_SEED = 42
SIM_DURATION = 100
NUM_NODES = 10

ip_to_node = {}
nodes = [] # list of ip adr

random.seed(RANDOM_SEED)
env = simpy.Environment()

rand_ips = list(map(ipaddress.ip_address, random.sample(range(4294967295), NUM_NODES)))
rand_kids = random.sample(range((kadnode.KAD_ID_LEN**2)-1), NUM_NODES)

for i in range(NUM_NODES):
    n = kadnode.Node(rand_ips[i], rand_kids[i], env)
    ip_to_node[rand_ips[i]] = n
    nodes.append(rand_ips[i])
    env.process(n.handle_message())



env.process(ip_to_node[rand_ips[0]].send_ping(nodes[1], ip_to_node))



env.run(until=SIM_DURATION)