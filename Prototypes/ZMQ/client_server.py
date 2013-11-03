__author__ = 'wbk3zd'

from daemon import FileDaemon
from syncutils import SyncResponder
import time
import threading
import zmq

class ClientController:
    def __init__(self):
        self.msg_identifier = msg_identifier = {
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
        self.responder_config = {
            "REC_PORT":"5556",
            "PATH_BASE":"C:/Test1/OneDir/",
            "CONTROLLER":"5558",
        }
        self.sender_config = {
            "REC_ADDRESS":"localhost",
            "REC_PORT":"5555",
            "PATH_BASE":"C:/Test1/OneDir/",
            "CONTROLLER":"5558",
        }
        self.controller_config = {
            "REC_ADDRESS":"localhost",
            "REC_PORT":"5557",
            "USER":"wbk3zd",
            "CONTROLLER":"5558",
        }
        self.responder = SyncResponder(self.msg_identifier, self.responder_config)
        self.daemon = FileDaemon(self.msg_identifier, self.sender_config)
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket_local = self._context.socket(zmq.PULL)
        self._socket.connect("tcp://" + self.controller_config["REC_ADDRESS"] + ":" + self.controller_config["REC_PORT"])
        print("Client controller connected over tcp to " + self.controller_config["REC_ADDRESS"] + ":" + self.controller_config["REC_PORT"] + "...")
        self._socket_local.bind("tcp://*:" + self.controller_config["REC_PORT"])
        print("Client controller binded over tcp to " + self.controller_config["CONTROLLER"] + "...")
        self.listen_flag = threading.Event()
        self.listen_flag.clear()
        self.listen()
        self._start_connection()
        self._start_responder()
        self._start_daemon()
    def _start_connection(self):
        msg = [self.msg_identifier["CONNECT"], self.controller_config["USER"]]
        self._socket.send_multipart(self.ascii_encode(msg))
        rep = self.decode(self._socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.controller_config["USER"]:
            print("Connection to server established, starting services...")
        else:
            print("Error: Bad response from server...")
    def _start_responder(self):
        self.responder.listen()
        msg = self.ascii_encode([self.controller_config["LISTENING"]])
        self._socket.send_multipart(msg)
        rep = self.decode(self._socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.msg_identifier["LISTENING"]:
            print("Responder service started, beginning file monitoring...")
        else:
            print("Error: No acknowledgement from server...")
    def _start_daemon(self):
        self.daemon.monitor()
        msg = self.ascii_encode([self.controller_config["MONITORING"]])
        self._socket.send_multipart(msg)
        rep = self.decode(self._socket.recv_multipart())
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.msg_identifier["MONITORING"]:
            print("Monitoring file directories, full services online...")
        else:
            print("Error: No acknowledgement from server...")
    def _listen(self):
        while self.listen_flag.is_set():
            msg = self.decode(self._socket_local.recv_multipart())
            if msg[0] == self.msg_identifier["STOP_MONITOR"]:
                self.daemon.pause()
            elif msg[0] == self.msg_identifier["START_MONITOR"]:
                self.daemon.resume()
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen).start()
    def ascii_encode(self, msg):
        msg_clone = msg
        for i in range(0, len(msg_clone)):
            msg_clone[i] = msg_clone[i].encode('ascii', 'replace')
        return msg_clone
    def decode(self, msg):
        for i in range(0, len(msg)):
            msg[i] = unicode(msg[i])
        return msg

def start_server_responder(msg_identifiers, config, wait_flag, signal_flag):
    while not wait_flag.is_set:
        time.sleep(1)
    print("Server responder going online...")
    response_server = SyncResponder(msg_identifiers, config)
    try:
        response_server.listen()
        signal_flag.set()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        response_server.teardown()
        print("Forcible keyboard interrupt, listening aborted")

def start_client_responder(msg_identifiers, config, wait_flag, signal_flag):
    while not wait_flag.is_set:
        time.sleep(1)
    print("Client responder going online...")
    response_client = SyncResponder(msg_identifiers, config)
    try:
        response_client.listen()
        signal_flag.set()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        response_client.teardown()
        print("Forcible keyboard interrupt, listening aborted")

def start_server_daemon(msg_identifiers, config, wait_flag, signal_flag):
    while not wait_flag.is_set():
        time.sleep(1)
    print("Server file daemon going online...")
    daemon = FileDaemon(msg_identifiers, config)
    try:
        signal_flag.set()
        daemon.monitor()
    except KeyboardInterrupt:
        print("Going down...")

def start_client_daemon(msg_identifiers, config, wait_flag):
    while not wait_flag.is_set():
        time.sleep(1)
    print("Client daemon going online...")
    daemon = FileDaemon(msg_identifiers, config)
    try:
        daemon.monitor()
    except KeyboardInterrupt:
        print("Going down...")

def main():
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
    client_rec_config = {
        "REC_PORT":"5556",
        "PATH_BASE":"C:/Test1/OneDir/",
        "CONTROLLER":"5558",
    }
    client_sender_config = {
        "REC_ADDRESS":"localhost",
        "REC_PORT":"5555",
        "PATH_BASE":"C:/Test1/OneDir/",
        "CONTROLLER":"5558",
    }

    server_rec_config = {
        "REC_PORT":"5555",
        "PATH_BASE":"C:/Test2/wbk3zd/OneDir/",
    }

    server_sender_config = {
        "REC_ADDRESS":"localhost",
        "REC_PORT":"5556",
        "PATH_BASE":"C:/Test2/wbk3zd/OneDir/",
        "CONTROLLER":"5559",
    }

    server_rec_flag = threading.Event()
    client_rec_flag = threading.Event()
    server_send_flag = threading.Event()
    client_send_flag = threading.Event()

    server_rec_flag.clear()
    client_rec_flag.clear()
    server_send_flag.clear()
    client_send_flag.clear()

    threading.Thread(target=start_server_responder, args=(msg_identifier,server_rec_config, server_rec_flag, client_rec_flag)).start()
    threading.Thread(target=start_client_responder, args=(msg_identifier, client_rec_config, client_rec_flag, server_send_flag)).start()
    threading.Thread(target=start_server_daemon, args=(msg_identifier, server_sender_config, server_send_flag, client_send_flag)).start()
    threading.Thread(target=start_client_daemon, args=(msg_identifier, client_sender_config, client_send_flag)).start()

    server_rec_flag.set()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Forcible keyboard interrupt, going down...")

if __name__ == "__main__":
    main()