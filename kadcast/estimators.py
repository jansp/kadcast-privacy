import ipaddress
import math

class FirstSpyEstimator:
    def __init__(self, tx_maps, true_sources: {ipaddress.ip_address: [int]}):
        self.p = 0.0
        self.r = 0.0
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


        #print(tx_ip_map)
        #print(true_sources)
        for ip in true_sources:
            tx = true_sources[ip][0]
            if tx_ip_map[tx] == ip:
                self.p += 1 / list(tx_ip_map.values()).count(ip)
                self.r += 1

        self.p /= len(true_sources)
        self.r /= len(true_sources)
