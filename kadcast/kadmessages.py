from enum import Enum

#// define field sizes for the headers
#LEN_SIZE: int = 4 # length
#TYPE_SIZE: int = 1 # type
#KAD_PING_SIZE: int = 20 # senderID
#KAD_FINDNODE_SIZE: int = 8+8 # senderID + targetID
#KAD_NODES_SIZE: int =  8+8+2+(m_nodeCount * (8+4)) # senderID + targetID + nodeCount + 12 byte per node
#KAD_BROADCAST_SIZE: int = 8+8+2+8+4+2+2 // senderID+blockID+chunkID+prevID+blockSize+nChunks+height
#KAD_REQUEST_SIZE: int = 8+8 // senderID+blockID

class KadMsgType(Enum):
    PING = 0
    PONG = 1
    FINDNODE = 2
    NODES = 3
    BROADCAST = 4
    REQUEST = 5

class BaseMessage:
    def __init__(self, sender, data=None):
        self.sender = sender
        self.data = data

    def __str__(self):
        return "UNDEFINED"

class Ping(BaseMessage):
    def __str__(self):
        return "PING"
    pass

class Pong(BaseMessage):
    def __str__(self):
        return "PONG"
    pass

class FindNode(BaseMessage):
	#TODO
	pass

class Nodes(BaseMessage):
	#TODO
	pass

class Broadcast(BaseMessage):
	#TODO
	pass

class Request(BaseMessage):
	#TODO
	pass