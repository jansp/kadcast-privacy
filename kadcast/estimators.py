import ipaddress

class FirstSpyEstimator:
    def __init__(self, spy_mapping, block_timestamps, true_sources: {ipaddress.ip_address: [int]}, n_honest: int):
        self.p = 0.0
        self.r = 0.0

        txs = sorted([item for sublist in list(true_sources.values()) for item in sublist])

        times = [block_timestamps[spy] for spy in block_timestamps]
        spies = list(spy_mapping.keys())

        tx_ip_map = {}
        for tx in txs:
            timestamps_tx = [i[tx] for i in times]
            m_tx = min(timestamps_tx)  # earliest timestamp of tx
            idx = timestamps_tx.index(m_tx)
            observer = spies[idx]
            from_ip = spy_mapping[observer][tx]
            tx_ip_map[tx] = from_ip
            #print("Mapped TX %d to IP %s" % (tx, from_ip))

        #print(tx_ip_map)
        #print(true_sources)
        for ip in true_sources:
            tx = true_sources[ip][0]
            if tx_ip_map[tx] == ip:
                self.p += 1 / list(tx_ip_map.values()).count(ip)
                self.r += 1

        self.p /= len(true_sources)
        self.r /= len(true_sources)
