import simpy
import ipaddress
import random
import kadnode
import seed_handler
from helpers import Block
import estimators

RANDOM_SEED = 42
SIM_DURATION = 200000000
NUM_NODES = 2**8
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
    #env.process(n.main_loop())


env.run(env.now + 1000)
for ip in ip_to_node:
    ip_to_node[ip].bootstrap([ip_list[0]])
    env.run(env.now + 1000)


true_sources = {}
for ip in ip_list:
    true_sources[ip] = []

env.run(env.now + 30000000)


num_blocks = 18
benign_nodes = list(set(id_list) - set(spies))
for block in range(num_blocks):
    sender = random.choice(benign_nodes)
    id_to_node[sender].init_broadcast(Block(block))
    true_sources[ip_list[sender]].append(block)
    env.run(env.now + 20000)



env.run(until=SIM_DURATION)


#spy_mapping = [id_to_node[i].block_source for i in spies]
#block_timestamps = [id_to_node[i].block_timestamps for i in spies]
#est = estimators.FirstSpyEstimator(spy_mapping, block_timestamps, true_sources, NUM_SPIES)

#print("Precision: %f" % est.p)
#print("Recall: %f" % est.r)




##############################################################################################################################################################

nope = []
for ip in ip_to_node:
    #print(ip_to_node[ip].blocks)
    x = len(ip_to_node[ip].blocks)
    if x != num_blocks:
        nope.append(ip_to_node[ip].kad_id)
        #print("NO")
        #print(ip_to_node[ip].kad_id)
        #print(x)
    #print(len(ip_to_node[ip].blocks))

print(nope)
print(len(nope))
#for id in id_to_node:
    #for bucket in id_to_node[id].buckets:
        #print(bucket)
        #if not id_to_node[id].buckets[bucket]:
            #pass
            #print("Node %d has empty bucket (%d)" % (id, bucket))
    #print("Buckets of ", end='')
    #print(id, end='')
    #print(": ", end='')
    #print(id_to_node[id].buckets)
#print(id_to_node[50].buckets)
#print(id_to_node[31].find_k_closest_nodes(15))