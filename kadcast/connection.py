import simpy
import functools

env = None


@functools.lru_cache(maxsize=1)
def init_env(environment):
    global env
    env = environment


class Connection(object):
    def __init__(self):
        self.store = simpy.Store(env)

    def latency(self, value, delay=20):
        yield env.timeout(delay)
        self.store.put(value)

    def put(self, value, delay=20):
        env.process(self.latency(value, delay))

    def get(self):
        return self.store.get()
