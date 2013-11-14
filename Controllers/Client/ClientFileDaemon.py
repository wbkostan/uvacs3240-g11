__author__ = 'wbk3zd'

import time
import zmq
from watchdog.observers import Observer
import threading
import watchdog.events
import subprocess
import os
import shutil
import encodings
from Helpers.Encodings import *

class SyncEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, msg_identifier):
        self.msg_identifier = msg_identifier
        self.config = None
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.event_src_path = None
        self.event_rel_path = None
    def initialize(self, config):
        self.config = config
        self.socket.connect("tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_CATCH_PORT"])
        print("Daemon connected to server at " + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_CATCH_PORT"] + "...")
        self.dir_sync(self.config["PATH_BASE"])
        self.finish()
    def on_any_event(self, event):
        self.event_src_path = event.src_path
        self.event_rel_path = os.path.relpath(self.event_src_path, self.config["PATH_BASE"])
    def on_created(self, event):
        if os.path.isdir(self.event_src_path):
            print("Sending mkdir command to server for directory at " + self.event_rel_path)
            msg = [self.config["USERNAME"], self.msg_identifier["MKDIR"], self.event_rel_path]
            self.socket.send_multipart(encode(msg))
        else:
            self.file_sync()
        self.finish()
    def on_deleted(self, event):
        print("Sending delete command to server for file system object at " + self.event_rel_path)
        msg = [self.config["USERNAME"], self.msg_identifier["DELETE"], self.event_rel_path]
        self.socket.send_multipart(encode(msg))
        self.finish()
    def on_modified(self, event):
        if os.path.isfile(self.event_src_path):
            self.file_sync()
        else:
            print("<handling a modified directory>")
        self.finish()
    def on_moved(self, event):
        event_dest_path = event.dest_path
        rel_dest_path = os.path.relpath(event_dest_path, self.config["PATH_BASE"])
        print("Sending move command to server from " + self.event_rel_path + " to " + rel_dest_path)
        msg = [self.config["USERNAME"], self.msg_identifier["MOVE"], self.event_rel_path, rel_dest_path]
        self.socket.send_multipart(encode(msg))
        self.finish()
    def file_sync(self):
        if self.event_src_path == None:
            print("Error: Told to sync, but sync source not set!")
            return
        with open(self.event_src_path, 'rb') as user_file:
            content = user_file.read()
        print("Sending filesync command to server for file at " + self.event_rel_path)
        msg = [self.config["USERNAME"], self.msg_identifier["FILESYNC"], self.event_rel_path, content]
        self.socket.send_multipart(encode(msg))
    def dir_sync(self, top):
        copy_src_path = self.event_src_path
        copy_rel_path = self.event_rel_path
        msg = [self.config["USERNAME"], self.msg_identifier["MKDIR"], os.path.relpath(top, self.config["PATH_BASE"])]
        self.socket.send_multipart(encode(msg))
        for parent, sub_dirs, files in os.walk(top):
            for user_file in files:
                self.event_src_path = parent + user_file
                self.event_rel_path = os.path.relpath(self.event_src_path, self.config["PATH_BASE"])
                self.file_sync()
                self.finish()
            for sub_dir in sub_dirs:
                self.dir_sync((parent+sub_dir))
        self.event_src_path = copy_src_path
        self.event_rel_path = copy_rel_path
    def finish(self):
        print("")
        self.event_src_path = None
        self.event_rel_path = None
    def encode(self, msg):
        msg_clone = msg
        for i in range(0, len(msg_clone)):
            msg_clone[i] = msg_clone[i].encode('ascii', 'replace')
        return msg_clone
    def decode(self, msg):
        for i in range(0, len(msg)):
            msg[i] = unicode(msg[i])
        return msg

class FileDaemon:
    def __init__(self, msg_identifier):
        #Components
        self.event_handler = SyncEventHandler(msg_identifier)
        self.observer = Observer()

        #Attributes
        self.config = None
        self.target_dir = None

        #Flags
        self.monitor_flag = threading.Event()
        self.monitor_flag.clear()
    def _monitor(self):
        """
            Function run on separate thread which acts as parent to observer thread(s).
            Used to control operation flow of observer using monitor_flag
        """
        print("Client daemon is monitoring " + self.target_dir + "...")
        print("")
        self.observer.start()
        while (self.monitor_flag.is_set()):
            time.sleep(1)
        self.observer.stop()
        self.observer.join()
    def monitor(self):
        self.monitor_flag.set()
        threading.Thread(target=self._monitor).start()
    def initialize(self, config):
        self.config = config
        self.target_dir = self.config["PATH_BASE"]
        self.event_handler.initialize(self.config)
        print("Scheduling observation of " + self.target_dir + " tree...")
        self.observer.schedule(self.event_handler, self.target_dir, recursive=True)
    def full_sync(self):
        self.event_handler.dir_sync(self.target_dir)
    def pause(self):
        self.monitor_flag.clear()
    def teardown(self):
        self.monitor_flag.clear()