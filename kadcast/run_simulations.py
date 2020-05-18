import simpy
import pandas as pd
import ipaddress
import random
import kadnode
import seed_handler
from helpers import Block
import estimators
import hashlib
#import sys

RANDOM_SEED = 42
SIM_DURATION = 200000000


NUM_NODES = range(10, 20)
FRACTION_SPIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
NUM_TXS = range(1, 10)
KAD_KS = range(20, 60)

seed_handler.save_seed(RANDOM_SEED)


NUM_NODES = [16]
NUM_TXS = [1]
num_samples = 2
#kad_ks = [20]


df = pd.DataFrame(columns=["TXS", "NODES", "FRAC_SPIES", "PRECISION", "RECALL", "KAD_K", "ID_LEN"])
for s_i in range(num_samples):
    random.seed(RANDOM_SEED+s_i)
    for n in NUM_NODES:
        num_nodes = n
        for f in FRACTION_SPIES:
            fraction_spies = f
            num_spies = int(fraction_spies * num_nodes)
            for n_tx in NUM_TXS:
                num_blocks = n_tx

                ip_to_node = {}
                id_to_node = {}

                env = simpy.Environment()

                ip_list = list(map(ipaddress.ip_address, random.sample(range(4294967295), num_nodes)))
                id_bytes = [(int(ip)).to_bytes(20, byteorder='big') for ip in ip_list]
                id_list_n = [int(hashlib.sha1(bytestr).hexdigest(), 16) for bytestr in id_bytes]
                id_list_n = [5,4,3,2,1,0,15,14,13,12,11,10,9,8,7,6]
                #print(len(id_list_n) == len(set(id_list_n)))


                id_list = list(range(num_nodes))
                #id_list_n = id_list

                spies = sorted(random.sample(id_list, num_spies))

                for i in range(num_nodes):
                    n = kadnode.Node(ip_list[i], id_list_n[i], env, ip_to_node)
                    ip_to_node[ip_list[i]] = n
                    id_to_node[id_list_n[i]] = n
                    env.process(n.handle_message())

                env.run(env.now + 1000)
                for ip in ip_to_node:
                    ip_to_node[ip].bootstrap([ip_list[0]])
                    env.run(env.now + 1000)

                true_sources = {}
                #for ip in ip_list:
                #    true_sources[ip] = []

                env.run(env.now + 30000000)

                #num_blocks = 1
                benign_nodes = list(set(id_list) - set(spies))

                senders = random.sample(benign_nodes, num_blocks)
                for n_id in senders:
                    true_sources[ip_list[n_id]] = []


                for block in range(num_blocks):
                    #sender = random.choice(benign_nodes)
                    sender = senders[block]
                    id_to_node[id_list_n[sender]].init_broadcast(Block(block))
                    true_sources[ip_list[sender]].append(block)
                    env.run(env.now + 20000)

                env.run()

                #spy_mapping = [id_to_node[i].block_source for i in spies]
                spy_mapping = {}
                block_timestamps = {}
                for i in spies:
                    spy_mapping[i] = id_to_node[id_list_n[i]].block_source
                    block_timestamps[i] = id_to_node[id_list_n[i]].block_timestamps
                    #print(id_to_node[i].blocks)
                    #print(id_to_node[i].block_source)
                    #print(id_to_node[i].block_timestamps)
                #print(spy_mapping)
                #print(block_timestamps)
                #print(true_sources)
                #block_timestamps = [id_to_node[i].block_timestamps for i in spies]



                #print(block_timestamps)
                #spy_mapping = [id_to_node[i].block_source for i in spies]
                #block_timestamps = [id_to_node[i].block_timestamps for i in spies]
                est = estimators.FirstSpyEstimator(spy_mapping, block_timestamps, true_sources, (num_nodes - num_spies))

                print("%d TXs, %d NODES, %.2f FRACTION SPIES, " % (num_blocks, num_nodes, fraction_spies))
                print("Precision: %f" % est.p)
                print("Recall: %f" % est.r)
                #print("SOURCE IPS")
                #print(set([ip_list[n] for n in spies]) - set(est.source_ips))
                dict_append = {}
                dict_append["TXS"] = num_blocks
                dict_append["NODES"] = num_nodes
                dict_append["FRAC_SPIES"] = fraction_spies
                dict_append["PRECISION"] = est.p
                dict_append["RECALL"] = est.r
                dict_append["KAD_K"] = 20
                dict_append["ID_LEN"] = 160

                #df.to_csv("firstspy200.csv", mode='a', header=None)
                df = df.append(dict_append, ignore_index=True)
                #df.to_csv("firstspy_large.csv", mode='a', header=None)

                #for kad_k in kad_ks:
                    #for id_len in id_lens:





df.to_csv("csv/firstspy_mul.csv")


