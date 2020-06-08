import ipaddress
import math

class FirstSpyEstimator:
    def __init__(self, tx_maps, true_sources: {ipaddress.ip_address: [int]}):
        self.p = 0.0
        self.r = 0.0
        self.r_old = 0.0

        benign_nodes = len(true_sources)
        observer_map = {}  # BLOCK_ID: observer

        txs = sorted([item for sublist in list(true_sources.values()) for item in sublist]) #TODO sort unneccesary? also rather pass txs as arg?

        tx_ip_map = {}
        for tx in txs:
            first_time = math.inf
            for spy in tx_maps:
                spy_data = tx_maps[spy]
                obs_time = spy_data[tx][1]
                if obs_time < first_time:
                    first_time = obs_time
                    from_ip = spy_data[tx][0]
                    tx_ip_map[tx] = from_ip
                    observer_map[tx] = spy

            #print("Mapped TX %d to IP %s, first spy: %d" % (tx, from_ip, observer_map[tx]))


        ip_tx_map = {} # Mapping created by adversary #TODO directly create this mapping, instead of reversing tx_ip_map

        for ip in true_sources.keys():
            ip_tx_map[ip] = []

        for tx, ip in tx_ip_map.items():
            if ip not in ip_tx_map:
                ip_tx_map[ip] = []
            ip_tx_map[ip].append(tx)

        #print("TX TO IP MAP:")
        #print(tx_ip_map)
        #print("IP TO TX MAP:")
        #print(ip_tx_map)
        #print(true_sources)

        hits = 0
        misses = 0
        for ip in true_sources.keys():
            for tx in true_sources[ip]:
                if tx in ip_tx_map[ip]:
                    hits += 1
                else:
                    misses += 1
            for tx in ip_tx_map[ip]:
                if tx not in true_sources[ip]:
                    misses += 1

        self.r = hits/len(txs)
        self.p = hits/(len(txs)+misses)

        #found_tx_list = []
        #for tx in txs:
        #    ip = tx_ip_map[tx]
        #    if ip not in true_sources:
        #        continue
        #    if tx in true_sources[ip]:
        #        #found_tx_list.append(tx)
        #        self.r += 1#

        #self.r /= len(txs)
        #self.p = self.r

        # for ip in true_sources.keys():
        #     #TODO das ist falsch, hier wird nicht geguckt welche tx es eigentlich sind
        #     # TODO need ip_tx_map for easy impl: then check  found_tx/overhead_tx+wronly_found_tx
        #     # normalize by amount benign nodes ?!= len(true_sources)
        #
        #     true_pos = 0
        #     false_pos = 0
        #     false_neg = 0
        #
        #     for tx in ip_tx_map[ip]:
        #         if tx in true_sources[ip]:
        #             true_pos += 1
        #         elif tx not in true_sources[ip]:
        #             false_pos += 1
        #
        #     for tx in true_sources[ip]:
        #         if tx not in ip_tx_map[ip]:
        #             false_neg += 1
        #
        #     p_ip = true_pos / (true_pos + false_pos)
        #     r_ip = true_pos / (true_pos + false_neg)
        #
        #     self.p += p_ip
        #     self.r += r_ip
        #
        # self.p /= benign_nodes
        # self.r /= benign_nodes
