class BaseMessage:
    def __init__(self, sender, data=None):
        self.sender = sender
        self.data = data

    def __str__(self):
        return "UNDEFINED"

class Ping(BaseMessage):
    def __str__(self):
        return "PING"

class Pong(BaseMessage):
    def __str__(self):
        return "PONG"

class FindNode(BaseMessage):
    def __str__(self):
        return "FINDNODE"
    #TODO

class Nodes(BaseMessage):
    def __str__(self):
        return "NODES"
    #TODO

class Broadcast(BaseMessage):
    def __str__(self):
        return "BROADCAST"
    #TODO

class Request(BaseMessage):
    def __str__(self):
        return "REQUEST"
    #TODO
