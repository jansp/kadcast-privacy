import ipaddress

class FirstSpyEstimator:
    def __init__(self, spy_mapping, true_sources: {ipaddress.ip_address: [int]}, num_nodes: int):
        self.p = 0.0
        self.r = 0.0
        for spy_data in spy_mapping:
            for ip in spy_data:
                if spy_data[ip] in true_sources[ip]:
                    self.p += 1.0 / len(true_sources[ip])
                    self.r += 1.0
        self.p = self.p / num_nodes
        self.r = self.r / num_nodes