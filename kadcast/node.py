import random

KAD_ID_LEN: int = 160
KAD_PING_TIMEOUT: float = 10.0
KAD_BUCKET_REFRESH_TIMEOUT: float = 3600.0
KAD_PORT: int = 8334
KAD_PACKET_SIZE: int = 1433


class Node:
    def __init__(self, ip: str = None, kad_id: int = None):
        self.kad_k = 20
        self.kad_alpha = 3
        self.kad_beta = 3

        self.buckets = dict({int: ['Node']})
        for i in range(KAD_ID_LEN):
            self.buckets[i] = []

        if ip is None:
            self.ip = random_ip()
        else:
            self.ip = ip

        if kad_id is None:
            self.kad_id = random.randint(1, pow(2, KAD_ID_LEN))
        else:
            self.kad_id = kad_id

    def distance(self, node_b: 'Node') -> int:
        return self.kad_id ^ node_b.kad_id

    def get_bucket_index(self, node_b: 'Node') -> int:
        """Returns bucket_index for node, starting from 0"""
        dist = self.distance(node_b)
        for i in range(KAD_ID_LEN):
            if pow(2, i) <= dist < pow(2, i + 1):
                return i

    def random_address_from_bucket(self, bucket: int) -> str:
        return random.choice(self.buckets[bucket]).ip

    def update_bucket(self, node_b: 'Node'):
        #TODO unfinished
        if self.kad_id == node_b.kad_id:
            return

        ips = [i.ip for i in self.buckets[self.get_bucket_index(node_b)]] # list of all ip addr in bucket
        if node_b.ip in ips:
            #TODO
        #self.buckets[self.get_bucket_index(node_b)].append()



def distance(node_a: Node, node_b: Node) -> int:
    return node_a.kad_id ^ node_b.kad_id


def random_ip() -> str:
    return ".".join(str(random.randint(0, 255)) for _ in range(4))
