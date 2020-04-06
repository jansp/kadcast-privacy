import ipaddress

class FirstSpyEstimator:
    def __init__(self, spy_mapping, block_timestamps, true_sources: {ipaddress.ip_address: [int]}, num_nodes: int):
        self.p = 0.0
        self.r = 0.0
        num = 0
        #print(true_sources)
        #print(spy_mapping)
        for spy_data in spy_mapping:
            for ip in spy_data:
                #print(spy_data)
                times = [i[spy_data[ip]] for i in block_timestamps]
                if times.index(min(times)) == spy_mapping.index(spy_data):
                    num += 1
                    if spy_data[ip] in true_sources[ip]:
                        self.p += 1.0 / len(true_sources[ip])
                        self.r += 1.0
        self.p = self.p / num
        self.r = self.r / num