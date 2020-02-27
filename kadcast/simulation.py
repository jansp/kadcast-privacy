import simpy
import ipaddress
import random
import kadnode
import seed_handler
from helpers import Block
import estimators

RANDOM_SEED = 42
SIM_DURATION = 2000000
NUM_NODES = 256
FRACTION_SPIES = 0.3

NUM_SPIES = int(FRACTION_SPIES*NUM_NODES)
ip_to_node = {}
id_to_node = {}

random.seed(RANDOM_SEED)
seed_handler.save_seed(RANDOM_SEED)
env = simpy.Environment()


ip_list = list(map(ipaddress.ip_address, random.sample(range(4294967295), NUM_NODES)))
id_list = list(range(NUM_NODES))
spies = sorted(random.sample(id_list, NUM_SPIES))

for i in range(NUM_NODES):
    n = kadnode.Node(ip_list[i], id_list[i], env, ip_to_node)
    ip_to_node[ip_list[i]] = n
    id_to_node[id_list[i]] = n
    env.process(n.handle_message())

for ip in ip_to_node:
    ip_to_node[ip_list[0]].send_ping(ip)

for ip in ip_to_node:
    ip_to_node[ip].bootstrap([ip_list[0]])
    env.run(env.now + 3000)

#id_to_node[50].bootstrap([ip_list[0]])

true_sources = {}
for ip in ip_list:
    true_sources[ip] = []

env.run(env.now + 200000)
id_to_node[id_list[0]].init_broadcast(Block(1, data="BLOCK 1"))
true_sources[ip_list[0]].append(1)
env.run(env.now + 200000)
id_to_node[id_list[0]].init_broadcast(Block(2, data="BLOCK 2"))
true_sources[ip_list[0]].append(2)
env.run(until=SIM_DURATION)


spy_mapping = [id_to_node[i].block_source for i in spies]
block_timestamps = [id_to_node[i].block_timestamps for i in spies]
#print(spies)
#print(spy_mapping[0])
#print(true_sources)
est = estimators.FirstSpyEstimator(spy_mapping, block_timestamps, true_sources, NUM_SPIES)
print("Precision: %f" % est.p)
print("Recall: %f" % est.r)
#print(block_timestamps)

#for ip in ip_to_node:
#    print("Node %d received blocks: " % ip_to_node[ip].kad_id, end='')
#    print(list(ip_to_node[ip].blocks))
