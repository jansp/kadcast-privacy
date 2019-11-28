import random
import ipaddress

KAD_ID_LEN: int = 160
KAD_PING_TIMEOUT: float = 10.0
KAD_BUCKET_REFRESH_TIMEOUT: float = 3600.0
KAD_PORT: int = 8334
KAD_PACKET_SIZE: int = 1433


class Node:
    def __init__(self, ip: ipaddress.IPv4Address = None, kad_id: int = None):
        self.kad_k = 20
        self.kad_alpha = 3
        self.kad_beta = 3

        self.buckets = dict({int: [(ipaddress.IPv4Address, int)]})
        for i in range(KAD_ID_LEN):
            self.buckets[i] = []

        if ip is None:
            self.ip = random_ip()
        else:
            assert isinstance(ip, ipaddress.IPv4Address), "ip is not of type ipaddress.IPv4Address: %r" % ip
            self.ip = ip

        if kad_id is None:
            self.kad_id = random.getrandbits(KAD_ID_LEN)
        else:
            assert isinstance(kad_id, int), "kad_id is not of type int: %r" % kad_id
            self.kad_id = kad_id

    def distance(self, id_b: int) -> int:
        return self.kad_id ^ id_b

    def id_to_bucket_index(self, id_b: int) -> int:
        """Returns bucket_index for node with id 'id_b', starting from 0"""
        dist = self.distance(id_b)
        for i in range(KAD_ID_LEN):
            if pow(2, i) <= dist < pow(2, i + 1):
                return i

    def random_address_from_bucket(self, bucket: int) -> str:
        return random.choice(self.buckets[bucket])[0]

    def update_bucket(self, ip_id_pair: (ipaddress.IPv4Address, int)):
        assert isinstance(ip_id_pair, tuple) and list(map(type, ip_id_pair)) == [ipaddress.IPv4Address, int], "ip_id_pair is not of type (ipaddress.IPv4Address, int): %r" % ip_id_pair
        ip_b, id_b = ip_id_pair

        if self.kad_id == id_b:
            return

        bucket = self.buckets[self.id_to_bucket_index(id_b)]
        ips = [i[0] for i in bucket] # list of all ip addr in bucket
        if ip_b in ips:
            #TODO optimize to don't double check list
            idx = ips.index(ip_b)
            del bucket[idx]
            bucket.append((ip_b, id_b))
        else: # ip not found in bucket
            if len(bucket) < self.kad_k:
                bucket.append((ip_b, id_b))
            else:
                # TODO ping last recently seen node, drop only if no answer, not always
                del bucket[0]
                bucket.append((ip_b, id_b))



def distance(id_a: int, id_b: int) -> int:
    return id_a ^ id_b


def random_ip() -> ipaddress.IPv4Address:
    return ipaddress.ip_address(random.getrandbits(32))