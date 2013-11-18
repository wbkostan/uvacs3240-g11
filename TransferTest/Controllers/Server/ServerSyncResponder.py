__author__ = 'wbk3zd'

import watchdog.events
import subprocess
import zmq
import os
import shutil
import threading
import encodings
import time
from Helpers.Encodings import *
from Helpers.Logging.OneDirLogger import EventLogger

class SyncResponder():
    def __init__(self, msg_identifier, rec_config):
        self.msg_identifier = msg_identifier
        self.config = rec_config
        self._logger_ = EventLogger()
        self.context = zmq.Context()
        self.internal_request_socket = self.context.socket(zmq.PUSH)
        self.sync_passthru_socket = self.context.socket(zmq.SUB)
        self.listen_flag = threading.Event()
        self.listen_flag.clear()
    def initialize(self):
        self._logger_.init_session(os.path.dirname(self.config["PATH_BASE"][:-1]) + "\\responder.log")
        self.internal_request_socket.connect("tcp://localhost:" + self.config["INTERNAL_REQUEST_PORT"])
        self._logger_.log("INFO", "Connecting responder to internal server controller over tcp port " + self.config["INTERNAL_REQUEST_PORT"] + "...")
        self.sync_passthru_socket.setsockopt(zmq.SUBSCRIBE, self.config["USERNAME"].encode('ascii', 'replace'))
        self.sync_passthru_socket.connect("tcp://localhost:" + self.config["SYNC_PASSTHRU_PORT"])
        self._logger_.log("INFO", "Subscribed to sync directives at tcp://localhost:" + self.config["SYNC_PASSTHRU_PORT"] + "for user " + self.config["USERNAME"] + "...")
    def _listen(self):
        self._logger_.log("INFO", "Responder is listening for sync directives at tcp://localhost:" + self.config["SYNC_PASSTHRU_PORT"] + "for user " + self.config["USERNAME"] + "...")
        while(self.listen_flag.is_set()):
            msg = self.sync_passthru_socket.recv_multipart()
            threading.Thread(target=self.dispatch, args=(msg,)).start()
            #Remove topic from message where topic is username
            msg.remove(msg[0])
            msg = decode(msg)
            #Strip away file contents before logging message
            if msg[0] == self.msg_identifier["FILESYNC"]:
                msg[-1] = "<contents omitted from log>"
            self._logger_.log("INFO","Sync Directive received: " + str(msg))
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen).start()
    def pause(self):
        self._logger_.log("INFO", "Responder has stopped listening over all ports")
        self.listen_flag.clear()
    def teardown(self):
        self._logger_.log("INFO", "Killing responder...")
        self.listen_flag.clear()
    def dispatch(self, decode_msg):
        if not decode_msg[0]:
            self._logger_.log("ERROR", "Empty message received")
            return
        msg = [self.msg_identifier["STOP_MONITORING"], self.config["USERNAME"], str(threading.current_thread().ident)]
        self.internal_request_socket.send_multipart(encode(msg))
        time.sleep(1) #wait for local activity to settle
        if decode_msg[0] == self.msg_identifier["FILESYNC"]:
            self.on_sync(decode_msg)
        elif decode_msg[0] == self.msg_identifier["MKDIR"]:
            self.on_mkdir(decode_msg)
        elif decode_msg[0] == self.msg_identifier["DELETE"]:
            self.on_remove(decode_msg)
        elif decode_msg[0] == self.msg_identifier["MOVE"]:
            self.on_move(decode_msg)
        elif decode_msg[0] == self.msg_identifier["KILL"]:
            msg = [self.msg_identifier["KILL"]]
            self.internal_request_socket.send_multipart(encode(msg))
        else:
            self._logger_.log("ERROR", "Unrecognized message. Closing without handle")
        self.on_finish()
    def on_sync(self, msg):
        dest_path = self.config["PATH_BASE"] + msg[1]
        if not os.path.exists(os.path.dirname(dest_path)):
            os.mkdir(os.path.dirname(dest_path))
        self._logger_.log("INFO", "Updating file at " + dest_path)
        with open(dest_path, 'wb') as user_file:
            user_file.write(msg[2])
        self.on_finish()
    def on_mkdir(self, msg):
        dest_path = self.config["PATH_BASE"] + msg[1]
        self._logger_.log("INFO", "Make directory command received, processing...")
        if(os.path.isdir(dest_path)):
            self._logger_.log("INFO", "Directory already exists, ignoring make command...")
            self.on_finish()
        else:
            self._logger_.log("INFO", "Creating directory at " + dest_path)
            os.mkdir(dest_path)
        self.on_finish()
    def on_remove(self, msg):
        dest_path = self.config["PATH_BASE"] + msg[1]
        self._logger_.log("INFO", "Remove command received, processing...")
        if not os.path.exists(dest_path):
            self._logger_.log("ERROR", dest_path + " does not exist. Can't remove.")
            self.on_finish()
            return
        if(os.path.isdir(dest_path)):
            self._logger_.log("INFO", "Removing entire file tree at " + dest_path)
            shutil.rmtree(dest_path)
        else:
            self._logger_.log("INFO", "Removing file at" + dest_path)
            os.remove(dest_path)
        self.on_finish()
    def on_move(self, msg):
        self._logger_.log("INFO", "Move command received, processing...")
        src_path = self.config["PATH_BASE"] + msg[1]
        dest_path = self.config["PATH_BASE"] + msg[2]
        if not os.path.exists(src_path):
            self._logger_.log("ERROR", "File system object at " + dest_path + " does not exist. Cannot move")
            self.on_finish()
            return
        if(os.path.isdir(src_path)):
            self._logger_.log("INFO", "Moving directory at " + src_path + " to " + dest_path)
            shutil.copytree(src_path, dest_path)
            shutil.rmtree(src_path)
        else:
            self._logger_.log("INFO", "Moving file at" + src_path + "to" + dest_path)
            shutil.copy2(src_path, dest_path)
            os.remove(src_path)
        self.on_finish()
    def on_finish(self):
        print("")
        msg = [self.msg_identifier["START_MONITORING"], self.config["USERNAME"], str(threading.current_thread().ident)]
        self.internal_request_socket.send_multipart(encode(msg))