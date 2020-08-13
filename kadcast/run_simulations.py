import simpy
import pandas as pd
import ipaddress
import random
import kadnode
import seed_handler
from helpers import Block
import estimators
import hashlib
import argparse
import sys

# Create the parser
parser = argparse.ArgumentParser(description='Run simulation')

# Add the arguments
parser.add_argument('filename',
                       metavar='filename',
                       type=str,
                       help='name of csv')

parser.add_argument('-q', metavar='N', type=float, default=0.5, help="dandelion Q parameter")

parser.add_argument('--use_dand', dest='use_dand', default=False, action='store_true', help='use dandelion')


# Execute the parse_args() method
args = parser.parse_args()

print(args)

use_dand = args.use_dand
dand_q = args.q
filename = args.filename
filename = "csv/"+filename


RANDOM_SEED = 42
SIM_DURATION = 200000000
USE_DANDELION = use_dand
DANDELION_Q = dand_q


NUM_NODES = range(10, 20)
FRACTION_SPIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
NUM_TXS = range(1, 10)
KAD_KS = range(20, 60)

seed_handler.save_seed(RANDOM_SEED)


NUM_NODES = [10000]
NUM_TXS = [5000]
num_samples = 20
#kad_ks = [20]

# import iplane latencies
with open("latencies.txt") as f:
    latencies = f.readlines()

latencies = [int(x.strip()) for x in latencies]

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

                #id_list = list(range(num_nodes))
                #id_list_n = id_list

                spies = random.sample(id_list_n, num_spies)
                benign_nodes = list(set(id_list_n) - set(spies))
                #spies = sorted(random.sample(id_list, num_spies))

                # CREATE NODES
                for i in range(num_nodes):
                    n = kadnode.Node(ip_list[i], id_list_n[i], env, ip_to_node, use_dandelion=USE_DANDELION, dand_q=DANDELION_Q, latencies=latencies)
                    ip_to_node[ip_list[i]] = n
                    id_to_node[id_list_n[i]] = n
                    env.process(n.handle_message())

                ### START NETWORK STABILIZING PHASE
                env.run(env.now + 1000)
                for ip in ip_to_node:
                    ip_to_node[ip].bootstrap([ip_list[0]])
                    env.run(env.now + 1000)


                env.run(env.now + 30000000)
                ### FINISH NETWOK STABILIZING PHASE


                # initialize empty list of sent broadcasts for every benign node
                true_sources = {}
                #for id_n in benign_nodes:
                #    true_sources[ip_list[id_list_n.index(id_n)]] = []

                ### START BROADCAST PHASE
                for block in range(num_blocks):
                    sender = random.choice(benign_nodes)
                    sender_ip = ip_list[id_list_n.index(sender)]
                    if sender_ip not in true_sources.keys():
                        true_sources[sender_ip] = []

                    id_to_node[sender].init_broadcast(Block(block))
                    true_sources[sender_ip].append(block)
                    env.run(env.now + 20000)

                env.run()
                sim_time = env.now
                ### FINISH BROADCAST PHASE

                ### START DEANONYMIZATION ATTACK PHASE

                #spy_mapping = [id_to_node[i].block_source for i in spies]
                spy_mapping = {}
                block_timestamps = {}
                tx_maps = {}  # SPY_ID: { BLOCK_ID: (ip, timestamp) }
                for id_n in spies:
                    spy_mapping[id_n] = id_to_node[id_n].block_source
                    block_timestamps[id_n] = id_to_node[id_n].block_timestamps
                    tx_maps[id_n] = id_to_node[id_n].block_map
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
                est = estimators.FirstSpyEstimator(tx_maps, true_sources)
                #for tx in range(num_blocks):
                #    print("Mapped TX %d to ip %s, spy: %s", (tx, est.tx_ip_map[tx], ip_list[id_list_n.index(est.observer_map[tx])]))


                print("%d TXs, %d NODES, %.2f FRACTION SPIES, " % (num_blocks, num_nodes, fraction_spies))
                print("Precision: %f" % est.p)
                print("Recall: %f" % est.r)
                print("Sim Time: %d" % sim_time)
                #print("Recall (old): %f" % est.r_old)
                #print("SOURCE IPS")
                #print(set([ip_list[n] for n in spies]) - set(est.source_ips))
                dict_append = {}
                dict_append["TXS"] = num_blocks
                dict_append["NODES"] = num_nodes
                dict_append["FRAC_SPIES"] = fraction_spies
                dict_append["PRECISION"] = est.p
                dict_append["RECALL"] = est.r
                dict_append["KAD_K"] = 60
                dict_append["ID_LEN"] = 160
                dict_append["SIM_TIME"] = sim_time

                #df.to_csv("firstspy200.csv", mode='a', header=None)
                df = df.append(dict_append, ignore_index=True)
                #df.to_csv("firstspy_large.csv", mode='a', header=None)

                #for kad_k in kad_ks:
                    #for id_len in id_lens:


df.to_csv(filename)
