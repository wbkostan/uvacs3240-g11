__author__ = 'wbk3zd'

def encode(msg):
    """
        Helper functions. ZMQ won't send unicode (default python string) over network.
        Must recode to ascii before sending, then decode back for use in python.
    """
    msg_clone = msg
    for i in range(0, len(msg_clone)):
        msg_clone[i] = msg_clone[i].encode('ascii', 'replace')
    return msg_clone

def decode(msg):
    """
        Helper functions. ZMQ won't send unicode (default python string) over network.
        Must recode to ascii before sending, then decode back for use in python.
    """
    for i in range(0, len(msg)):
        msg[i] = unicode(msg[i])
    return msg
