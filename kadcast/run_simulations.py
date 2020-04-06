import simpy
import pandas as pd
import ipaddress
import random
import kadnode
import seed_handler
from helpers import Block
import estimators

RANDOM_SEED = 42
SIM_DURATION = 200000000


num_nodes = range(10, 20)
fraction_spies = list(map(lambda x: 1/x, range(2, 11)))
num_txs = range(1, 10)
kad_ks = range(20, 60)

random.seed(RANDOM_SEED)
seed_handler.save_seed(RANDOM_SEED)


num_nodes = [10, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
num_txs = [1, 5, 10, 20, 50, 100]
kad_ks = [20]


df = pd.DataFrame(columns=["TXS", "NODES", "FRAC_SPIES", "PRECISION", "RECALL", "KAD_K", "ID_LEN"])

for n in num_nodes:
    NUM_NODES = n
    for f in fraction_spies:
        FRACTION_SPIES = f
        NUM_SPIES = int(FRACTION_SPIES * NUM_NODES)
        for n_tx in num_txs:
            NUM_BLOCKS = n_tx

            ip_to_node = {}
            id_to_node = {}

            env = simpy.Environment()

            ip_list = list(map(ipaddress.ip_address, random.sample(range(4294967295), NUM_NODES)))
            id_list = list(range(NUM_NODES))
            spies = sorted(random.sample(id_list, NUM_SPIES))

            for i in range(NUM_NODES):
                n = kadnode.Node(ip_list[i], id_list[i], env, ip_to_node)
                ip_to_node[ip_list[i]] = n
                id_to_node[id_list[i]] = n
                env.process(n.handle_message())

            env.run(env.now + 1000)
            for ip in ip_to_node:
                ip_to_node[ip].bootstrap([ip_list[0]])
                env.run(env.now + 1000)

            true_sources = {}
            for ip in ip_list:
                true_sources[ip] = []

            env.run(env.now + 30000000)

            #num_blocks = 1
            benign_nodes = list(set(id_list) - set(spies))
            for block in range(NUM_BLOCKS):
                sender = random.choice(benign_nodes)
                id_to_node[sender].init_broadcast(Block(block))
                true_sources[ip_list[sender]].append(block)
                env.run(env.now + 20000)

            env.run()

            spy_mapping = [id_to_node[i].block_source for i in spies]
            block_timestamps = [id_to_node[i].block_timestamps for i in spies]
            est = estimators.FirstSpyEstimator(spy_mapping, block_timestamps, true_sources, NUM_SPIES)

            print("%d TXs, %d NODES, %.2f FRACTION SPIES, " % (NUM_BLOCKS, NUM_NODES, FRACTION_SPIES))
            print("Precision: %f" % est.p)
            print("Recall: %f" % est.r)
            dict_append = {}
            dict_append["TXS"] = NUM_BLOCKS
            dict_append["NODES"] = NUM_NODES
            dict_append["FRAC_SPIES"] = FRACTION_SPIES
            dict_append["PRECISION"] = est.p
            dict_append["RECALL"] = est.r
            dict_append["KAD_K"] = 20
            dict_append["ID_LEN"] = 8

            df = df.append(dict_append, ignore_index=True)

            #for kad_k in kad_ks:
                #for id_len in id_lens:





df.to_csv("firstspy.csv")


