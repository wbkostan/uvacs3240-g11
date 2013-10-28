__author__ = 'wbk3zd'

import watchdog.events
import subprocess
import zmq
import os
import shutil
import threading

"""
msg_identifier = {
    "FILESYNC":1,
    "MKDIR":2,
    "DELETE":3,
    "MOVE":4
}

send_config = {
    "REC_ADDRESS":"localhost",
    "REC_PORT":5555,
    "PATH_BASE":"C:/Test1/OneDir/",
}

rec_config = {
    "REC_PORT":5555,
    "SEND_ADDRESS":"localhost",
    "SEND_PORT":5556,
    "PATH_BASE":"C:/Test2/",
    "USER":"wbk3zd",
}
"""

class SyncEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, msg_identifier, send_config):
        self.msg_identifier = msg_identifier
        self.send_config = send_config
        self._context = zmq.Context(zmq.PUB)
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect("tcp://" + send_config["REC_ADDRESS"] + ":" + send_config["REC_PORT"])
        print("Client event responder connected over tcp to " + send_config["REC_ADDRESS"] + ":" + send_config["REC_PORT"])
        self._event_src_path = None
        self.sync_all()
    def sync_all(self):
        print("<executed full directory sync>")
    def on_any_event(self, event):
        self._event_src_path = event.src_path
        self._event_rel_path = os.path.relpath(self._event_src_path, self.send_config["PATH_BASE"])
    def on_created(self, event):
        if os.path.isdir(self._event_src_path):
            print("Sending mkdir command to server for directory at " + self._event_rel_path)
            self._socket.send_multipart([self.msg_identifier["MKDIR"], self._event_rel_path])
        else:
            self.file_sync()
        self.finish()
    def on_deleted(self, event):
        print("Sending delete command to server for file system object at " + self._event_rel_path)
        self._socket.send_multipart([self.msg_identifier["DELETE"], self._event_rel_path])
        self.finish()
    def on_modified(self, event):
        if os.path.isfile(self._event_src_path):
            self.file_sync()
        else:
            print("<handling a modified directory>")
        self.finish()
    def on_moved(self, event):
        event_dest_path = event.dest_path()
        rel_dest_path = os.path.relpath(event_dest_path, self.send_config["PATH_BASE"])
        print("Sending move command to server from " + self._event_rel_path + " to " + rel_dest_path)
        self._socket.send_multipart([self.msg_identifier["MOVE"], self._event_rel_path, rel_dest_path])
        self.finish()
    def file_sync(self):
        if self._event_src_path == None:
            print("Error: Told to sync, but not sync source not set!")
        with open(self._event_src_path, 'rb') as user_file:
            content = user_file.read()
        print("Sending filesync command to server for file at " + self._event_rel_path)
        self._socket.send_multipart([self.msg_identifier["FILESYNC"], self._event_rel_path, content])
    def finish(self):
        print("Cleaning up request")
        self._event_src_path = None

class SyncResponder():
    def __init__(self, msg_identifier, rec_config):
        self.msg_identifier = msg_identifier
        self.config = rec_config
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REP)
        print("Binding server to socket at tcp port " + self.config["REC_PORT"])
        self._socket.bind("tcp://*:" + self.config["REC_PORT"])
        self.listen_flag = threading.Event()
        self.listen_flag.clear()
    def _listen(self):
        print("Server is listening over tcp port " + self.config["REC_PORT"])
        while(self.listen_flag.is_set()):
            try:
                msg = self._socket.recv_multipart()
                print("Message received at tcp port " + self.config["REC_PORT"])
                threading.Thread(target=self.dispatch, args=(msg)).start()
            except KeyboardInterrupt:
                return
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen).start()
    def pause(self):
        print("Server has stopped listening over all ports")
        self.listen_flag.clear()
    def teardown(self):
        print("Killing server...")
        self.listen_flag.clear()
    def dispatch(self, msg):
        if not msg[0]:
            print("Error: Empty message received")
            return
        if msg[0] == self.config["FILESYNC"]:
            self.on_sync(msg)
        elif msg[0] == self.config["MKDIR"]:
            self.on_mkdir(msg)
        elif msg[0] == self.config["DELETE"]:
            self.on_remove(msg)
        elif msg[0] == self.config["MOVE"]:
            self.on_move(msg)
        else:
            print("Error: Unrecognized message. Closing without handle")
    def on_sync(self, msg):
        dest_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[1]
        print("Updating file at", dest_path)
        with open(dest_path, 'wb') as user_file:
            user_file.write(msg[2])
    def on_mkdir(self, msg):
        dest_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[1]
        print("Make directory command received, processing...")
        if(os.path.isdir(dest_path)):
            print("Directory already exists, ignoring make command...")
            return
        else:
            print("Creating directory at" + dest_path)
    def on_remove(self, msg):
        dest_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[1]
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
    def on_move(self, msg):
        print("Move command received, processing...")
        src_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[1]
        dest_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[2]
        if not os.path.exists(src_path):
            print("Error: File system object at " + dest_path + " does not exist. Cannot move")
            return
        if(os.path.isdir(src_path)):
            print("Moving directory at" + src_path + "to" + dest_path)
            shutil.copytree(src_path, dest_path)
            shutil.rmtree(src_path)
        else:
            print("Moving file at" + src_path + "to" + dest_path)
            shutil.copy2(src_path, dest_path)
            os.remove(src_path)

if __name__ == "__main__":
    print("Usage")
