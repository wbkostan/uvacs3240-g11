__author__ = 'wbk3zd'

from daemon import FileDaemon
from syncutils import SyncResponder
import time
import threading

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
    daemon = FileDaemon(config["PATH_BASE"], msg_identifiers, config)
    try:
        signal_flag.set()
        daemon.monitor()
    except KeyboardInterrupt:
        print("Going down...")

def start_client_daemon(msg_identifiers, config, wait_flag):
    while not wait_flag.is_set():
        time.sleep(1)
    print("Client daemon going online...")
    daemon = FileDaemon(config["PATH_BASE"], msg_identifiers, config)
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
        "ACK":"5"
    }

    server_rec_config = {
        "REC_PORT":"5555",
        "PATH_BASE":"C:/Test2/wbk3zd/OneDir/",
    }

    client_rec_config = {
        "REC_PORT":"5556",
        "PATH_BASE":"C:/Test1/OneDir/",
    }

    client_sender_config = {
        "REC_ADDRESS":"localhost",
        "REC_PORT":"5555",
        "PATH_BASE":"C:/Test1/OneDir/",
    }
    server_sender_config = {
        "REC_ADDRESS":"localhost",
        "REC_PORT":"5556",
        "PATH_BASE":"C:/Test2/wbk3zd/OneDir/",
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