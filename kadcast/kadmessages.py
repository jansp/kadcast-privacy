class BaseMessage:
    def __init__(self, sender, data=None):
        self.sender = sender
        self.data = data

    def __str__(self):
        return "UNDEFINED"

    def __repr__(self):
        return "UNDEFINED"


class Ping(BaseMessage):
    def __str__(self):
        return "PING"

    def __repr__(self):
        return "PING"


class Pong(BaseMessage):
    def __str__(self):
        return "PONG"

    def __repr__(self):
        return "PONG"


class FindNode(BaseMessage):
    def __init__(self, sender, target_id: int):
        #BaseMessage.__init__(self, sender, data)
        self.sender = sender
        self.target_id = target_id

    def __str__(self):
        return "FINDNODE"

    def __repr__(self):
        return "FINDNODE"


class Nodes(BaseMessage):
    #TODO assert correct nodelist format
    def __init__(self, sender, target_id, node_list):
        #BaseMessage.__init__(self, sender, data)
        self.sender = sender
        self.target_id = target_id
        self.node_list = node_list

    def __str__(self):
        return "NODES"

    def __repr__(self):
        return "NODES"

class Broadcast(BaseMessage):
    def __init__(self, sender, block, height):
        #BaseMessage.__init__(self, sender, data)
        self.sender = sender
        self.block = block
        self.height = height

    def __str__(self):
        return "BROADCAST"

    def __repr__(self):
        return "BROADCAST"

class Forward(BaseMessage):
    def __init__(self, sender, block, visited_hops):
        #BaseMessage.__init__(self, sender, data)
        self.sender = sender
        self.block = block
        self.visited_hops = visited_hops

    def __str__(self):
        return "DANDELION FORWARD"

    def __repr__(self):
        return "DANDELION FORWARD"

