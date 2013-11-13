__author__ = 'wbk3zd'

from ServerFileDaemon import FileDaemon
from ServerSyncResponder import SyncResponder
import threading
import zmq
#from django.contrib.auth.models import User
#from django.contrib.auth import authenticate

"""
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
    config = {
        "PATH_BASE":"C:\Test2\\",
    }
"""

class ServerController:
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
            "KILL":"11",
            "LOGIN":"12",
            "TRUE":"13",
            "FALSE":"14",
        }
        self.config = config
        self.config["CLIENT_CONTACT_PORT"] = "5556"
        self.config["SYNC_THROW_PORT"] = "5557"
        self.config["SYNC_CATCH_PORT"] = "5558"
        self.config["SYNC_PASSTHRU_PORT"] = "5559"
        self.config["INTERNAL_REQUEST_PORT"] = "5560"
        self.config["SYNC_PASSUP_PORT"] = "5561"
        self.context = zmq.Context()
        self.internal_request_socket = self.context.socket(zmq.PULL)
        self.client_contact_socket = self.context.socket(zmq.REP)
        self.sync_throw_socket = self.context.socket(zmq.PUB)
        self.sync_catch_socket = self.context.socket(zmq.PULL)
        self.sync_passthru_socket = self.context.socket(zmq.PUB)
        self.sync_passup_socket = self.context.socket(zmq.PULL)
        self.internal_request_socket.bind("tcp://*:" + self.config["INTERNAL_REQUEST_PORT"])
        print("Server controller listening for internal requests over tcp port " + self.config["INTERNAL_REQUEST_PORT"] + "...")
        self.client_contact_socket.bind("tcp://*:" + self.config["CLIENT_CONTACT_PORT"])
        print("Server controller listening for client requests at tcp://localhost:" + self.config["CLIENT_CONTACT_PORT"] + "...")
        self.sync_throw_socket.bind("tcp://*:" + self.config["SYNC_THROW_PORT"])
        self.sync_catch_socket.bind("tcp://*:" + self.config["SYNC_CATCH_PORT"])
        self.sync_passthru_socket.bind("tcp://*:" + self.config["SYNC_PASSTHRU_PORT"])
        self.sync_passup_socket.bind("tcp://*:" + self.config["SYNC_PASSUP_PORT"])
        self.listen_flag = threading.Event()
        self.listen_flag.clear()
        self.client_components = {}
    def _listen_internal(self):
        blocking_threads = {}
        while self.listen_flag.is_set():
            msg = self.decode(self.internal_request_socket.recv_multipart())
            if msg[0] == self.msg_identifier["STOP_MONITORING"]:
                if not msg[1] in blocking_threads:
                    blocking_threads[msg[1]] = []
                blocking_threads[msg[1]].append(int(msg[2]))
                self.client_components[msg[1]][1].stop()
            elif msg[0] == self.msg_identifier["START_MONITORING"]:
                blocking_threads[msg[1]].remove(int(msg[2]))
                if not blocking_threads[msg[1]]:
                    self.client_components[msg[1]][1].monitor()
    def _listen_client(self):
        while self.listen_flag.is_set():
            msg = self.decode(self.client_contact_socket.recv_multipart())
            if msg[0] == self.msg_identifier["CONNECT"]:
                self.connect_client(msg[1])
                msg = [self.msg_identifier["ACK"], msg[1]]
            elif msg[0] == self.msg_identifier["LISTENING"]:
                self.start_client_daemon(msg[1])
                msg = [self.msg_identifier["ACK", msg[1]]]
            elif msg[0] == self.msg_identifier["LOGIN"]:
                if self.authenticate_client(msg[1], msg[2]):
                    msg = [self.msg_identifier["ACK"], self.msg_identifier["TRUE"]]
                else:
                    msg = [self.msg_identifier["ACK"], self.msg_identifier["FALSE"]]
            self.client_contact_socket.send_multipart(self.ascii_encode(msg))
    def _listen_sync_catch(self):
        while self.listen_flag.is_set():
            msg = self.decode(self.sync_catch_socket.recv_multipart())
            self.sync_passthru_socket.send_multipart(self.ascii_encode(msg))
    def _listen_sync_passup(self):
        """
            Catches all sync requests sent up by file daemons and publishes them
            to all clients subscribed to appropriate username
        """
        while self.listen_flag.is_set():
            msg = self.decode(self.sync_passup_socket.recv_multipart())
            self.sync_throw_socket.send_multipart(self.ascii_encode(msg))
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen_internal).start()
        threading.Thread(target=self._listen_client).start()
        threading.Thread(target=self._listen_sync_catch).start()
        threading.Thread(target=self._listen_sync_passup).start()
    def authenticate_client(self, username, password):
        return True
        """
        user = authenticate(username = username, password = password)
        if user is not None:
            if user.is_active():
                return True #Always authenticate until actual authentication is added.
            else:
                #Disabled account
                return False
        else:
            #Bad user/pass combo
            return False
        """
    def connect_client(self, username):
        if not username in self.client_components:
            daemon_config = responder_config = self.config
            daemon_config["USERNAME"] = responder_config["USERNAME"] = username
            daemon_config["PATH_BASE"] = responder_config["PATH_BASE"] = self.config["PATH_BASE"] + username + "\\OneDir\\"
            daemon = FileDaemon(self.msg_identifier, daemon_config)
            responder = SyncResponder(self.msg_identifier, responder_config)
            responder.initialize()
            daemon.initialize()
            responder.listen()
            self.client_components[username] = (daemon, responder, 1)
        else:
            self.client_components[username][2] += 1
    def disconnect_client(self, username):
        if username in self.client_components:
            self.client_components[username][2] -= 1
            if(self.client_components[username][2] == 0):
                self.client_components[username][0].teardown()
                self.client_components[username][1].teardown()
                del self.client_components[username]
    def start_client_daemon(self, username):
        if username in self.client_components:
            self.client_components[username][0].full_sync()
            if not self.client_components[username][0].is_alive():
                self.client_components[username][0].monitor()
    def start(self):
        self.listen()
    def teardown(self):
        self.listen_flag.clear()
        for key in self.client_components:
            self.client_components[key][0].teardown()
            self.client_components[key][1].teardown()
            self.client_components[key][2] = 0
            msg = [key, self.msg_identifier["DISCONNECT"]]
            self.sync_throw_socket.send_multipart(self.ascii_encode(msg))
            del self.client_components[key]
    def ascii_encode(self, msg):
        msg_clone = msg
        for i in range(0, len(msg_clone)):
            msg_clone[i] = msg_clone[i].encode('ascii', 'replace')
        return msg_clone
    def decode(self, msg):
        for i in range(0, len(msg)):
            msg[i] = unicode(msg[i])
        return msg
