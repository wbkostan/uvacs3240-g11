__author__ = 'wbk3zd'

from ClientFileDaemon import FileDaemon
from ClientSyncResponder import SyncResponder
import threading
import zmq

"""
    msg_identifier = {
        "FILESYNC":"1",
        "MKDIR":"2",
        "DELETE":"3",
        "MOVE":"4",
        "ACK":"5",
        "CONNECT":"6",
        "LISTENING":"7",
        "MONITORING":"8",
        "START_MONITORING":"9",
        "STOP_MONITORING":"10",
    }
    config = {
        "SERVER_ADDR":"localhost",
        "PATH_BASE":"C:\Test1\OneDir",
        "SERVER_SYNC_CATCH_PORT":"5558",
        "SERVER_SYNC_THROW_PORT":"5557",
        "SERVER_CONTACT_PORT":"5556"
    }
"""

class ClientController:
    def __init__(self, config):
        self.msg_identifier = {
            "FILESYNC":"1",
            "MKDIR":"2",
            "DELETE":"3",
            "MOVE":"4",
            "ACK":"5",
            "CONNECT":"6",
            "LISTENING":"7",
            "MONITORING":"8",
            "START_MONITORING":"9",
            "STOP_MONITORING":"10",
        }
        self.config = config
        self.config["INTERNAL_REQUEST_PORT"] = "5555"
        self.daemon_config = {
            "PATH_BASE":self.config["PATH_BASE"],
            "SERVER_ADDR":self.config["SERVER_ADDR"],
            "SERVER_SYNC_CATCH_PORT":self.config["SERVER_SYNC_CATCH_PORT"],
        }
        self.responder_config = {
            "PATH_BASE":self.config["PATH_BASE"],
            "SERVER_ADDR":self.config["SERVER_ADDR"],
            "INTERNAL_REQUEST_PORT":self.config["INTERNAL_REQUEST_PORT"],
            "SERVER_SYNC_THROW_PORT":self.config["SERVER_SYNC_THROW_PORT"],
        }
        self.responder = SyncResponder(self.msg_identifier, self.responder_config)
        self.daemon = FileDaemon(self.msg_identifier, self.daemon_config)
        self.context = zmq.Context()
        self.internal_request_socket = self.context.socket(zmq.PULL)
        self.server_contact_socket = self.context.socket(zmq.REQ)
        self.internal_request_socket.bind("tcp://*:" + self.config["INTERNAL_REQUEST_PORT"])
        print("Client controller listening for internal requests over tcp port " + self.config["INTERNAL_REQUEST_PORT"] + "...")
        self.server_contact_socket.connect("tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_CONTACT_PORT"])
        print("Client controller connected to server at " + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_CONTACT_PORT"] + "...")
    def authenticate(self):
        self.config["USERNAME"] = self.daemon_config["USERNAME"] = self.responder_config["USERNAME"] = "wbk3zd"
        return True
    def start(self):
        self.listen_flag = threading.Event()
        self.listen_flag.clear()
        self.listen()
        auth = False
        while not auth:
            auth = self.authenticate
        self.start_connection()
    def start_connection(self):
        msg = [self.msg_identifier["CONNECT"], self.config["USERNAME"]]
        self.server_contact_socket.send_multipart(self.ascii_encode(msg))
        rep = self.decode(self.server_contact_socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.config["USERNAME"]:
            print("Connection to server established, starting services...")
        else:
            print("Error: Bad response from server...")
            return
        self.start_responder()
    def start_responder(self):
        self.responder.listen()
        msg = [self.msg_identifier["LISTENING"], self.config["USERNAME"]]
        self.server_contact_socket.send_multipart(self.ascii_encode(msg))
        rep = self.decode(self.server_contact_socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.config["USERNAME"]:
            print("Responder service started, monitoring file system, full services started...")
        else:
            print("Error: Bad response from server")
    def disconnect(self):
        msg = [self.msg_identifier["DISCONNECT"], self.config["USERNAME"]]
        self.server_contact_socket.send_multipart(self.ascii_encode(msg))
        rep = self.decode(self.server_contact_socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.config["USERNAME"]:
            print("Disconnected from server, going down")
            self.responder.teardown()
            self.daemon.teardown()
            self.teardown()
    def _listen(self):
        blocking_threads = []
        while self.listen_flag.is_set():
            msg = self.decode(self.internal_request_socket.recv_multipart())
            if msg[0] == self.msg_identifier["STOP_MONITORING"]:
                blocking_threads.append(int(msg[1]))
                self.daemon.pause()
            elif msg[0] == self.msg_identifier["START_MONITORING"]:
                blocking_threads.remove(int(msg[1]))
                if not blocking_threads:
                    self.daemon.monitor()
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen).start()
    def teardown(self):
        self.listen_flag.clear()
    def ascii_encode(self, msg):
        msg_clone = msg
        for i in range(0, len(msg_clone)):
            msg_clone[i] = msg_clone[i].encode('ascii', 'replace')
        return msg_clone
    def decode(self, msg):
        for i in range(0, len(msg)):
            msg[i] = unicode(msg[i])
        return msg
