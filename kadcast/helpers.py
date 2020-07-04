import simpy

class Connection(object):
    # TODO implement latency in a better way
    def __init__(self, env):
        self.env = env
        #self.delay = delay
        self.store = simpy.Store(env)

    def latency(self, value, delay=20):
        yield self.env.timeout(delay)
        self.store.put(value)

    def put(self, value, delay=20):
        self.env.process(self.latency(value, delay))

    def get(self):
        return self.store.get()


class Block:
    def __init__(self, b_id: int, data=None):
        self.b_id = b_id
        self.data = data

    def __str__(self):
        return "BLOCK " + str(self.b_id)