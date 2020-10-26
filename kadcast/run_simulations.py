import simpy
import pandas as pd
import ipaddress
import random
from kadnode import Node
from bootstrap import bootstrap
import seed_handler
from helpers import Block
import estimators
import hashlib
import argparse
import pickle
from message_handler import handle_message, init_ipnode, init_dandelion, init_broadcast
from message_handler import init_env as m_init_env
from bootstrap import init_env as b_init_env
from connection import init_env as c_init_env
#from gmpy_cffi import mpz


def init_env(venv):
    m_init_env(venv)
    b_init_env(venv)
    c_init_env(venv)


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

FRACTION_SPIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


seed_handler.save_seed(RANDOM_SEED)


NUM_NODES = 100  # daily active nodes etherscan.io
NUM_TXS = 40
num_samples = 1


df = pd.DataFrame(columns=["TXS", "NODES", "FRAC_SPIES", "PRECISION", "RECALL", "KAD_K", "ID_LEN"])


for s_i in range(num_samples):
    random.seed(RANDOM_SEED+s_i)
    num_nodes = NUM_NODES
    for f in FRACTION_SPIES:
        fraction_spies = f
        num_spies = int(fraction_spies * num_nodes)
        num_blocks = NUM_TXS

        ip_to_node = {}
        id_to_node = {}

        env = simpy.Environment()
        sample = random.sample

        ip_list = list(map(ipaddress.ip_address, sample(range(4294967295), num_nodes)))
        id_bytes = ((int(ip)).to_bytes(20, byteorder='big') for ip in ip_list)
        id_list_n = [int(hashlib.sha1(bytestr).hexdigest(), 16) for bytestr in id_bytes]

        spies = sample(id_list_n, num_spies)
        benign_nodes = list(set(id_list_n) - set(spies))

        # CREATE NODES
        process = env.process
        init_env(env)
        for i in range(num_nodes):
            n = Node(ip_list[i], id_list_n[i])
            ip_to_node[ip_list[i]] = n
            id_to_node[id_list_n[i]] = n
            process(handle_message((ip_list[i], id_list_n[i])))

        init_ipnode(ip_to_node)
        init_dandelion(USE_DANDELION, DANDELION_Q)
        ### START NETWORK STABILIZATION PHASE
        #env.run(env.now + 1000)
        #print("Starting bootstrapping phase")

        #print("START BOOTSTRAPPING")
        for i_n in ip_to_node.values():
            rs = sample(ip_list, 30)
            bootstrap(i_n, rs)
            env.run(env.now + 100)

        env.run()
        #print("END BOOTSTRAPPING")
        ### FINISH NETWOK STABILIZATION PHASE

        # initialize empty list of sent broadcasts for every benign node
        true_sources = {}

        #for node in ip_to_node.values():
        #    print(node.buckets)
        ### START BROADCAST PHASE
        for block in range(num_blocks):
            sender = random.choice(benign_nodes)
            sender_ip = ip_list[id_list_n.index(sender)]
            if sender_ip not in true_sources.keys():
                true_sources[sender_ip] = []

            init_broadcast(id_to_node[sender].ip_id_pair(), Block(block))
            true_sources[sender_ip].append(block)
            env.run(env.now + 200000)

        env.run()
        ### FINISH BROADCAST PHASE

        ### START DEANONYMIZATION ATTACK PHASE

        #spy_mapping = [id_to_node[i].block_source for i in spies]
        spy_mapping = {}
        block_timestamps = {}
        tx_maps = {}  # SPY_ID: { BLOCK_ID: (ip, timestamp) }
        height_map = {}
        for id_n in spies:
            spy_mapping[id_n] = id_to_node[id_n].block_source
            block_timestamps[id_n] = id_to_node[id_n].block_timestamps
            tx_maps[id_n] = id_to_node[id_n].block_map
            height_map[id_n] = id_to_node[id_n].block_height
            #print(id_to_node[i].blocks)
            #print(id_to_node[i].block_source)
            #print(id_to_node[i].block_timestamps)
        #print(spy_mapping)
        #print(block_timestamps)
        #print(true_sources)
        #block_timestamps = [id_to_node[i].block_timestamps for i in spies]
        for node in ip_to_node.values():
            if NUM_TXS != len(node.blocks):
                print("BLOCK MISSING?")
                #print(node.blocks)


        #print(block_timestamps)
        #spy_mapping = [id_to_node[i].block_source for i in spies]
        #block_timestamps = [id_to_node[i].block_timestamps for i in spies]
        est = estimators.FirstSpyEstimator(tx_maps, true_sources)
        #for tx in range(num_blocks):
        #    print("Mapped TX %d to ip %s, spy: %s", (tx, est.tx_ip_map[tx], ip_list[id_list_n.index(est.observer_map[tx])]))

        # TODO pickle save: est.ip_tx_map, est.observer_map, true_sources, buckets of all nodes
        #f1 = open("pickle/ip_tx_map_"+str(s_i)+"_"+str(fraction_spies), "wb")
        #pickle.dump(est.ip_tx_map, f1)
        #f1.close()
        #f2 = open("pickle/observer_map_"+str(s_i)+"_"+str(fraction_spies), "wb")
        #pickle.dump(est.observer_map, f2)
        #f2.close()
        #f3 = open("pickle/true_sources_"+str(s_i)+"_"+str(fraction_spies), "wb")
        #pickle.dump(true_sources, f3)
        #f3.close()

        #for node in ip_to_node.values():
        #    print(node.buckets)
        #    f4 = open("pickle/buckets_"+str(node.kad_id)+"_"+str(s_i), "wb")
        #    pickle.dump(node.buckets, f4)
        #    f4.close()
        #for ip in est.ip_tx_map:
        #    for tx in est.ip_tx_map[ip]:
        #        n = est.observer_map[tx]
        #        print("TX %d observed by spy %s at height %d" % (tx, id_to_node[n].ip, height_map[n][tx]))
                #print("Bucket of true sender")
                #print(ip_to_node[ip].buckets[height_map[n][tx]])

        #for tx in est.observer_map:
        #honest_nodes_avg_nodes_per_bucket = 0
        #for ip in true_sources:
        #    #print("Buckets of %s" % ip)
        #    buckets = [len(x) for x in ip_to_node[ip].buckets.values()]
        #    for b in buckets:
        #        print("%d/20" % b)
        #        honest_nodes_avg_nodes_per_bucket += b

        #honest_nodes_avg_nodes_per_bucket = honest_nodes_avg_nodes_per_bucket/(160*len(true_sources))
        #print("Average nodes per bucket, honest nodes: %f" % honest_nodes_avg_nodes_per_bucket)
        #print("Average nodes %% per bucket, honest nodes: %f" % (honest_nodes_avg_nodes_per_bucket/20))


        print("%d TXs, %d NODES, %.2f FRACTION SPIES, " % (num_blocks, num_nodes, fraction_spies))
        print("Precision: %f" % est.p)
        print("Recall: %f" % est.r)
        #print("Recall (old): %f" % est.r_old)
        #print("SOURCE IPS")
        #print(set([ip_list[n] for n in spies]) - set(est.source_ips))
        dict_append = {"TXS": num_blocks, "NODES": num_nodes, "FRAC_SPIES": fraction_spies, "PRECISION": est.p,
                       "RECALL": est.r, "KAD_K": 20, "ID_LEN": 160}

        df = df.append(dict_append, ignore_index=True)
        #df.to_csv("firstspy_large.csv", mode='a', header=None)


df.to_csv(filename)
