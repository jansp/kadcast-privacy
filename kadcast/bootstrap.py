from helpers import id_to_bucket_index, KAD_ID_LEN
from random import randrange
from message_handler import send_ping, init_lookup

env = None


def init_env(environment):
    global env
    env = environment


def bootstrap(n, ips):
    ip_a, id_a = n.ip_id_pair()
    for ip in ips:
        try:
            send_ping((ip_a, id_a), ip)
        except:
            pass

    env.timeout(0).callbacks.append(lambda _: init_lookup(n, id_a))
    env.timeout(3000).callbacks.append(lambda _: refresh_buckets(n))
    env.timeout(30000000).callbacks.append(lambda _: refresh_buckets(n))


def bucket_refresh(n, node_iterator):
    kad_id = n.kad_id
    timeout = env.timeout
    for id_to_find in node_iterator:
        yield timeout(100)
        if id_to_bucket_index(kad_id, id_to_find) not in n.buckets:
            init_lookup(n, id_to_find)


def node_refresh_it(n):
    kad_id = n.kad_id
    min_max_list_all = ((2 ** i, 2 ** (i + 1)) for i in range(KAD_ID_LEN))
    itermap = map(lambda z: kad_id ^ randrange(*z), min_max_list_all)
    filterlist = filter(lambda y: id_to_bucket_index(kad_id, y) not in n.buckets, itermap)
    return filterlist


def refresh_buckets(n):
    it = node_refresh_it(n)
    env.process(bucket_refresh(n, it))
