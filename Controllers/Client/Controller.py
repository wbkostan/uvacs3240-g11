__author__ = 'wbk3zd'

from ClientFileDaemon import FileDaemon
from ClientSyncResponder import SyncResponder
import threading
import zmq

"""
    Sample of config dictionary which initializes controller:
    config = {
        "SERVER_ADDR":"localhost",
        "PATH_BASE":"C:\Test1\OneDir",
        "SERVER_SYNC_CATCH_PORT":"5558",
        "SERVER_SYNC_THROW_PORT":"5557",
        "SERVER_CONTACT_PORT":"5556"
    }
"""

class ClientController:
    def __init__(self):
        #Standardize message headers across all components
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
        self.config = None
        self.responder = SyncResponder(self.msg_identifier) #Listens for and responds to sync directives
        self.daemon = FileDaemon(self.msg_identifier) #Monitors file system and sends sync directives
        self.context = zmq.Context()
        self.internal_request_socket = self.context.socket(zmq.PULL)
        self.server_contact_socket = self.context.socket(zmq.REQ)
    def initialize(self, config):
        self.config = config
        self.config["INTERNAL_REQUEST_PORT"] = "5555" #Port for client components to request control actions
        self.internal_request_socket.bind("tcp://*:" + self.config["INTERNAL_REQUEST_PORT"])
        print("Client controller listening for internal requests over tcp port " + self.config["INTERNAL_REQUEST_PORT"] + "...")
        self.server_contact_socket.connect("tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_CONTACT_PORT"])
        print("Client controller connected to server at " + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_CONTACT_PORT"] + "...")
    def authenticate(self):
        """
            Responsible for authenticating client with server. Eventually, successful authentication server side
            will trigger a server_controller.connect_client() call to generate daemon/responder components for
            this client to connect to. Currently that generation is a result of calls in self.start() without auth.
            Also sets the username of the local client.
        """
        username = raw_input("Username: ")
        password = raw_input("Password: ")
        msg = [self.msg_identifier["LOGIN"], username, password]
        self.server_contact_socket.send_multipart(self.ascii_encode(msg))
        rep = self.decode(self.server_contact_socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.msg_identifier["TRUE"]:
            self.config["USERNAME"] = username
            return True
        elif rep[1] == self.msg_identifier["FALSE"]:
            print("Error: Bad username/password. Try again.")
            return False
        elif rep[0] != self.msg_identifier["ACK"]:
            print("Bad response from server. Going down")
            self.teardown()
            return False
        user = authenticate(username = username, password = password)
        if user is not None:
            if user.is_active:
                self.config["USERNAME"] = username
                return True #Always authenticate until actual authentication is added.
            else:
                print("The password is valid, but the account has been disabled.")
                return False
        else:
            print("The username and password were incorrect.")
            return False
    def start(self):
        """
            Brings the client controller online by establishing a connection with the server
            then bringing online client services (responder, daemon)
        """
        self.listen_flag = threading.Event()
        self.listen_flag.set()
        self.listen()#Begin listening for internal requests
        auth = False
        while not auth:
            auth = self.authenticate()
        print("Authenticated. Client going online...")
        self.start_connection()
    def start_connection(self):
        msg = [self.msg_identifier["CONNECT"], self.config["USERNAME"]]
        self.server_contact_socket.send_multipart(self.ascii_encode(msg))
        rep = self.decode(self.server_contact_socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.config["USERNAME"]:
            print("Connection to server established, starting services...")
            self.start_responder()
        else:
            print("Error: Bad response from server. Beginning teardown...")
            self.teardown()
            return
    def start_responder(self):
        print("Initializing client responder...")
        self.responder.initialize(self.config)
        print("Bringing client responder online...")
        self.responder.listen()
        msg = [self.msg_identifier["LISTENING"], self.config["USERNAME"]]
        print("Sending acknowledgement to server, awaiting intial directory sync...")
        self.server_contact_socket.send_multipart(self.ascii_encode(msg))
        rep = self.decode(self.server_contact_socket.recv_multipart())
        print("Server response received, responding with in-kind directory sync")
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.config["USERNAME"]:
            print("Responder service started, monitoring file system, full services started...")
        else:
            print("Error: Bad response from server")
        self.daemon.initialize(self.config)
    def disconnect(self):
        self.listen_flag.clear()
        msg = [self.msg_identifier["DISCONNECT"], self.config["USERNAME"]]
        self.server_contact_socket.send_multipart(self.ascii_encode(msg))
        rep = self.decode(self.server_contact_socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.config["USERNAME"]:
            print("Disconnected from server, going down peacefully")
        self.responder.teardown()
        self.daemon.teardown()
    def _listen(self):
        print("Client listening for internal requests...")
        blocking_threads = []
        while self.listen_flag.is_set():
            msg = self.decode(self.internal_request_socket.recv_multipart())
            if msg[0] == self.msg_identifier["STOP_MONITORING"]:
                blocking_threads.append(int(msg[1]))
                self.daemon.pause()
            elif msg[0] == self.msg_identifier["START_MONITORING"]:
                if int(msg[1]) in blocking_threads:
                    blocking_threads.remove(int(msg[1]))
                if not blocking_threads:
                    self.daemon.monitor()
            elif msg[0] == self.msg_identifier["KILL"]:
                print("Error: Forceful interrupt command received from server. Killing all services")
                self.teardown()
        print("Client stopped listening for internal requests")
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen).start()
    def teardown(self):
        self.listen_flag.clear()
        self.responder.teardown()
        self.daemon.teardown()
    def ascii_encode(self, msg):
        msg_clone = msg
        for i in range(0, len(msg_clone)):
            msg_clone[i] = msg_clone[i].encode('ascii', 'replace')
        return msg_clone
    def decode(self, msg):
        for i in range(0, len(msg)):
            msg[i] = unicode(msg[i])
        return msg
