import ipaddress
import math

class FirstSpyEstimator:
    def __init__(self, tx_maps, true_sources: {ipaddress.ip_address: [int]}):
        self.p = 0.0
        self.r = 0.0
        self.r_old = 0.0

        benign_nodes = len(true_sources)
        observer_map = {}  # BLOCK_ID: observer

        txs = sorted([item for sublist in list(true_sources.values()) for item in sublist])

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


        ip_tx_map = {} # Mapping created by adversary

        for ip in true_sources.keys():
            ip_tx_map[ip] = []

        for tx, ip in tx_ip_map.items():
            if ip not in ip_tx_map:
                ip_tx_map[ip] = []
            ip_tx_map[ip].append(tx)

        for ip in true_sources.keys():
            fp = 0
            fn = 0
            tp = 0
            for tx in true_sources[ip]:
                if tx in ip_tx_map[ip]:
                    tp += 1
                else:
                    fn += 1

            if tp == 0:
                continue
            for tx in ip_tx_map[ip]:
                if tx not in true_sources[ip]:
                    fp += 1

            self.r += tp/(tp+fn)
            self.p += tp/(tp+fp)

        #print(len(true_sources.keys()))
        t_s = len(true_sources.keys())
        self.r = self.r/t_s
        self.p = self.p/t_s
