__author__ = 'wbk3zd'

import watchdog.events
import subprocess
import zmq
import os
import shutil
import threading
import encodings
import time

class SyncResponder():
    def __init__(self, msg_identifier, rec_config):
        self.msg_identifier = msg_identifier
        self.config = rec_config
        self.context = zmq.Context()
        self.internal_request_socket = self.context.socket(zmq.PUSH)
        self.internal_request_socket.connect("tcp://localhost:" + self.config["INTERNAL_REQUEST_PORT"])
        print("Connecting responder to internal client controller over tcp port " + self.config["INTERNAL_REQUEST_PORT"] + "...")
        self.server_sync_throw_socket = self.context.socket(zmq.SUB)
        self.server_sync_throw_socket.setsocketopt(zmq.SUBSCRIBE, self.config["USERNAME"])
        self.server_sync_throw_socket.connect("tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_THROW_PORT"])
        print("Subscribed to sync directives at " + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_THROW_PORT"] + "for user " + self.config["USERNAME"] + "...")
        self.listen_flag = threading.Event()
        self.listen_flag.clear()
    def _listen(self):
        print("Responder is listening for sync directives at " + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_THROW_PORT"] + "for user " + self.config["USERNAME"] + "...")
        print("")
        while(self.listen_flag.is_set()):
            try:
                msg = self.socket.recv_multipart()
                threading.Thread(target=self.dispatch, args=(msg,)).start()
            except KeyboardInterrupt:
                return
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen).start()
    def pause(self):
        print("Responder has stopped listening over all ports")
        self.listen_flag.clear()
    def teardown(self):
        print("Killing responder...")
        self.listen_flag.clear()
    def dispatch(self, msg):
        decode_msg = self.decode(msg)
        msg.remove(msg[0]) #Remove topic from message
        if not decode_msg[0]:
            print("Error: Empty message received")
            return
        msg = [self.msg_identifier["STOP_MONITORING"], str(threading.get_ident())]
        self.internal_request_socket.send_multipart(self.ascii_encode(msg))
        time.sleep(1) #wait for local activity to settle
        if decode_msg[0] == self.msg_identifier["FILESYNC"]:
            self.on_sync(decode_msg)
        elif decode_msg[0] == self.msg_identifier["MKDIR"]:
            self.on_mkdir(decode_msg)
        elif decode_msg[0] == self.msg_identifier["DELETE"]:
            self.on_remove(decode_msg)
        elif decode_msg[0] == self.msg_identifier["MOVE"]:
            self.on_move(decode_msg)
        elif decode_msg[0] == self.msg_identifier["DISCONNECT"]:
            msg = [self.msg_identifier["KILL"]]
            self.internal_request_socket.send_multipart(self.ascii_encode(msg))
        else:
            print("Error: Unrecognized message. Closing without handle")
        self.on_finish()
    def on_sync(self, msg):
        dest_path = self.config["PATH_BASE"] + msg[1]
        if not os.path.exists(os.path.dirname(dest_path)):
            os.mkdir(os.path.dirname(dest_path))
        print("Updating file at " + dest_path)
        with open(dest_path, 'wb') as user_file:
            user_file.write(msg[2])
        self.on_finish()
    def on_mkdir(self, msg):
        dest_path = self.config["PATH_BASE"] + msg[1]
        print("Make directory command received, processing...")
        if(os.path.isdir(dest_path)):
            print("Directory already exists, ignoring make command...")
            return
        else:
            print("Creating directory at " + dest_path)
            os.mkdir(dest_path)
        self.on_finish()
    def on_remove(self, msg):
        dest_path = self.config["PATH_BASE"] + msg[1]
        print("Remove command received, processing...")
        if not os.path.exists(dest_path):
            print("Error: " + dest_path + " does not exist. Can't remove.")
            return
        if(os.path.isdir(dest_path)):
            print("Removing entire file tree at " + dest_path)
            shutil.rmtree(dest_path)
        else:
            print("Removing file at" + dest_path)
            os.remove(dest_path)
        self.on_finish()
    def on_move(self, msg):
        print("Move command received, processing...")
        src_path = self.config["PATH_BASE"] + msg[1]
        dest_path = self.config["PATH_BASE"] + msg[2]
        if not os.path.exists(src_path):
            print("Error: File system object at " + dest_path + " does not exist. Cannot move")
            return
        if(os.path.isdir(src_path)):
            print("Moving directory at " + src_path + " to " + dest_path)
            shutil.copytree(src_path, dest_path)
            shutil.rmtree(src_path)
        else:
            print("Moving file at" + src_path + "to" + dest_path)
            shutil.copy2(src_path, dest_path)
            os.remove(src_path)
        self.on_finish()
    def on_finish(self):
        print("")
        msg = [self.msg_identifier["START_MONITORING"]]
        self.internal_request_socket.send_multipart(self.ascii_encode(msg))
    def ascii_encode(self, msg):
        msg_clone = msg
        for i in range(0, len(msg_clone)):
            msg_clone[i] = msg_clone[i].encode('ascii', 'replace')
        return msg_clone
    def decode(self, msg):
        for i in range(0, len(msg)):
            msg[i] = unicode(msg[i])
        return msg