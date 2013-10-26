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
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect("tcp://" + send_config["REC_ADDRESS"] + ":" + send_config["REC_PORT"])
        self._event_src_path = None
        self.sync_all()
    def on_any_event(self, event):
        self._event_src_path = event.src_path()
        self._event_rel_path = os.path.relpath(self._event_src_path, self.send_config["PATH_BASE"])
    def on_created(self, event):
        if os.path.isdir(self._event_src_path):
            self._socket.send_multipart([self.msg_identifier["MKDIR"], self._event_rel_path])
        else:
            self.file_sync()
        self.finish()
    def on_deleted(self, event):
        self._socket.send_multipart([self.msg_identifier["DELETE"], self._event_rel_path])
        self.finish()
    def on_modified(self, event):
        if os.path.isfile(self._event_src_path):
            self.sync()
        else:
            print("handle modified directory")
        self.finish()
    def on_moved(self, event):
        event_dest_path = event.dest_path()
        rel_dest_path = os.path.relpath(event_dest_path, self.send_config["PATH_BASE"])
        self._socket.send_multipart([self.msg_identifier["MOVE"], self._event_src_path, rel_dest_path])
        self.finish()
    def file_sync(self):
        if self._event_src_path == None:
            print("No directory!")
        with open(self._event_src_path, 'rb') as file:
            content = file.read()
        self._socket.send_multipart([self.msg_identifier["FILESYNC"], self._event_rel_path, content])
    def finish(self):
        self._event_src_path = None
    def sync_all(self):
        print("syncing")

class SyncResponder():
    def __init__(self, msg_identifier, rec_config):
        self.msg_identifier = msg_identifier
        self.config = rec_config
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REP)
        self._socket.bind("tcp://*:" + self.config["REC_PORT"])
        self.listen_flag = threading.Event()
        self.listen_flag.clear()
    def _listen(self):
        while(self.listen_flag.is_set()):
            try:
                msg = self._socket.recv_multipart()
                threading.Thread(target=self.dispatch, args=(msg)).start()
            except KeyboardInterrupt:
                return
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen).start()
    def pause(self):
        self.listen_flag.clear()
    def teardown(self):
        self.listen_flag.clear()
    def dispatch(self, msg):
        if not msg[0]:
            print("lol what?")
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
            print("lol what?")
    def on_sync(self, msg):
        dest_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[1]
        with open(dest_path, 'wb') as user_file:
            user_file.write(msg[2])
    def on_mkdir(self, msg):
        dest_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[1]
        if(os.path.isdir(dest_path)):
            return
        else:
            os.mkdir(dest_path)
    def on_remove(self, msg):
        dest_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[1]
        if not os.path.exists(dest_path):
            return
        if(os.path.isdir(dest_path)):
            shutil.rmtree(dest_path)
        else:
            os.remove(dest_path)
    def on_move(self, msg):
        src_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[1]
        dest_path = self.config["PATH_BASE"] + self.config["USER"] + "/OneDir/" + msg[2]
        if not os.path.exists(src_path):
            return
        if(os.path.isdir(src_path)):
            shutil.copytree(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)

if __name__ == "__main__":
    print("Usage")
