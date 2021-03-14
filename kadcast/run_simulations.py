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
import json
import pickle
from message_handler import handle_message, init_ipnode, init_dandelion, init_broadcast
from message_handler import init_env as m_init_env
from bootstrap import init_env as b_init_env
from connection import init_env as c_init_env
import os
import numpy as np
import gevent



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


RANDOM_SEED = seed_handler.load_seed("seed_val.txt")+hash(filename)
SIM_DURATION = 200000000
USE_DANDELION = use_dand
DANDELION_Q = dand_q

FRACTION_SPIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


#seed_handler.save_seed(RANDOM_SEED)


NUM_NODES = 1000
NUM_TXS = 4000
num_samples = 3

proc_list = []


def init_message_handling(num_nodes_x, ip_list_x, id_list_n_x):
    for i in range(num_nodes_x):
        n = Node(ip_list_x[i], id_list_n_x[i])
        ip_to_node[ip_list_x[i]] = n
        id_to_node[id_list_n_x[i]] = n

    zips = np.array([handle_message(zips) for zips in zip(ip_list_x, id_list_n_x)])
    for z in zips:
        proc_list.append(env.process(z))


df = pd.DataFrame(columns=["TXS", "NODES", "FRAC_SPIES", "PRECISION", "RECALL", "KAD_K", "ID_LEN"])

folder = str(NUM_NODES) + "_" + str(NUM_TXS) + "_" + str(USE_DANDELION) + "_" + str(DANDELION_Q)+"/"
#os.mkdir("pickle/"+folder)

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
        init_env(env)

        init_message_handling(num_nodes, ip_list, id_list_n)

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

        # initialize empty list of sent broadcasts
        true_sources = {}

        #for node in ip_to_node.values():
        #    print(node.buckets)
        ### START BROADCAST PHASE
        for block in range(num_blocks):
            sender = random.choice(benign_nodes)
            sender_ip = ip_list[id_list_n.index(sender)]
            if sender_ip not in true_sources.keys():
                true_sources[sender_ip] = []

            #print("%s sending TX %d..." % (id_to_node[sender].ip_id_pair()[0], block))
            #print("Spies: %s" % [id_to_node[s].ip_id_pair()[0] for s in spies])
            init_broadcast(id_to_node[sender].ip_id_pair(), Block(block))
            true_sources[sender_ip].append(block)
            #env.run(env.now + 30000)

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
        mi = False
        for node in ip_to_node.values():
            if NUM_TXS != len(node.blocks):
                #print("BLOCK MISSING?")
                mi = True
                #print(node.blocks)
        if mi:
            continue

        #print(block_timestamps)
        #spy_mapping = [id_to_node[i].block_source for i in spies]
        #block_timestamps = [id_to_node[i].block_timestamps for i in spies]
        est = estimators.FirstSpyEstimator(tx_maps, true_sources)
        #for tx in range(num_blocks):
        #    print("Mapped TX %d to ip %s, spy: %s", (tx, est.tx_ip_map[tx], ip_list[id_list_n.index(est.observer_map[tx])]))

        # TODO pickle save: est.ip_tx_map, est.observer_map, true_sources, buckets of all nodes


        # print("Save observations to file")
        #
        # stringtx = {}
        # string_true_sources = {}
        #
        # for item in est.ip_tx_map.items():
        #     stringtx[str(item[0])] = item[1]
        #
        # for item in true_sources.items():
        #     string_true_sources[str(item[0])] = item[1]
        #
        # f1 = open("pickle/" + folder + "ip_tx_map_" + str(s_i) + "_" + str(fraction_spies) + ".json", "w")
        # json.dump(stringtx, f1)
        # f1.close()
        #
        # f2 = open("pickle/"+folder+"observer_map_"+str(s_i)+"_"+str(fraction_spies) + ".json", "w")
        # json.dump(est.observer_map, f2)
        # #pickle.dump(est.observer_map, f2)
        # f2.close()
        #
        # f3 = open("pickle/"+folder+"true_sources_"+str(s_i)+"_"+str(fraction_spies) + ".json", "w")
        # json.dump(string_true_sources, f3)
        # f3.close()
        #
        # f4 = open("pickle/"+folder+"spies_"+str(s_i)+"_"+str(fraction_spies) + ".json", "w")
        # json.dump(spies, f4)
        # f4.close()
        #
        # print("Save nodes to file")
        # #os.mkdir("pickle/"+folder+"nodes_"+str(s_i)+"_"+str(fraction_spies) + "/")
        # ip_id = {}
        # for i in range(num_nodes):
        #     ip_id[str(ip_list[i])] = id_list_n[i]
        #
        # f5 = open("pickle/"+folder+"ip_to_id_"+str(s_i)+"_"+str(fraction_spies) + ".json", "w")
        # json.dump(ip_id, f5)
        # f5.close()

        # nodes_dict = {}
        # d = "pickle/" + folder + "nodes_" + str(s_i) + "_" + str(fraction_spies)+ ".json"
        # for n in ip_to_node.values():
        #     nodes_dict["BLOCKHEIGHT " + str(n.kad_id)] = n.block_height
        #     bs = {}
        #     for i in n.block_source.items():
        #         bs[i[0]] = str(i[1])
        #
        #     nodes_dict["BLOCKSOURCE " + str(n.kad_id)] = bs
        #
        #     nodes_dict["BLOCKTIMESTAMPS " + str(n.kad_id)] = n.block_timestamps
        #     buckets = {}
        #     for i in n.buckets:
        #         m = {}
        #         for elem in n.buckets[i].items():
        #             m[str(elem[0])] = elem[1]
        #         buckets[i] = m
        #
        #     nodes_dict["BUCKETS " + str(n.kad_id)] = buckets
        #
        # f_n = open(d, "w")
        # json.dump(nodes_dict, f_n)
        # f_n.close()
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
        proc_list = []
        #df.to_csv("firstspy_large.csv", mode='a', header=None)


df.to_csv(filename)
