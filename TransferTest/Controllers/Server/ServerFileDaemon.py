__author__ = 'wbk3zd'

import time
import zmq
from watchdog.observers import Observer
import threading
import watchdog.events
import os
from Helpers.Encodings import *
from Helpers.Logging.OneDirLogger import EventLogger

class SyncEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, msg_identifier, send_config):
        #Components
        self._logger_ = EventLogger()
        self.msg_identifier = msg_identifier
        self.config = send_config
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.event_src_path = None
        self.event_rel_path = None
        self.lock = threading.RLock()
    """
        Public Methods
    """
    def initialize(self):
        """
            Initializes components. Connects sockets
        """

        #Initialize components
        logfile = os.path.dirname(self.config["PATH_BASE"][:-1]) + SLASH + "daemon.log"
        self._logger_.join_session(logfile)

        #Connect sockets
        self.socket.connect("tcp://localhost:" + self.config["SYNC_PASSUP_PORT"])
        self._logger_.log("INFO", "Daemon connected to server at tcp://localhost:" + self.config["SYNC_PASSUP_PORT"] + "...")
    def print_files(self, top):
        self.lock.acquire()
        self._logger_.log("INFO", "Printing files belonging to " + top)
        for parent, sub_dirs, files in os.walk(top):
            self._logger_.log("INFO", "Containing " + parent + "including " + str(sub_dirs) + " and " + str(files))
    def dir_sync(self, top):
        self.lock.acquire()
        self._logger_.log("INFO", "Directory sync command received for " + top)
        copy_src_path = self.event_src_path
        copy_rel_path = self.event_rel_path
        msg = [self.config["USERNAME"], self.msg_identifier["MKDIR"], os.path.relpath(top, self.config["PATH_BASE"])]
        self.socket.send_multipart(encode(msg))
        for parent, sub_dirs, files in os.walk(top):
            self._logger_.log("INFO", "Iterating over " + parent + " including " + str(sub_dirs) + " and " + str(files))
            for user_file in files:
                self.event_src_path = parent + user_file
                self.event_rel_path = os.path.relpath(self.event_src_path, self.config["PATH_BASE"])
                self._file_sync_()
            for sub_dir in sub_dirs:
                self.dir_sync((parent+sub_dir))
        self.event_src_path = copy_src_path
        self.event_rel_path = copy_rel_path
        self.lock.release()
    def on_any_event(self, event):
        self.lock.acquire()
        self.event_src_path = event.src_path
        self.event_rel_path = os.path.relpath(self.event_src_path, self.config["PATH_BASE"])
    def on_created(self, event):
        if os.path.isdir(self.event_src_path):
            self._logger_.log("INFO", "Sending mkdir command to server for directory at " + self.event_rel_path)
            msg = [self.config["USERNAME"], self.msg_identifier["MKDIR"], self.event_rel_path]
            self.socket.send_multipart(encode(msg))
        else:
            self._file_sync_()
        self._finish_()
    def on_deleted(self, event):
        self._logger_.log("INFO", "Sending delete command to server for file system object at " + self.event_rel_path)
        msg = [self.config["USERNAME"], self.msg_identifier["DELETE"], self.event_rel_path]
        self.socket.send_multipart(encode(msg))
        self._finish_()
    def on_modified(self, event):
        if os.path.isfile(self.event_src_path):
            self._file_sync_()
        else:
            self._logger_.log("INFO", "<handling a modified directory>")
        self._finish_()
    def on_moved(self, event):
        event_dest_path = event.dest_path
        rel_dest_path = os.path.relpath(event_dest_path, self.config["PATH_BASE"])
        self._logger_.log("INFO", "Sending move command to server from " + self.event_rel_path + " to " + rel_dest_path)
        msg = [self.config["USERNAME"], self.msg_identifier["MOVE"], self.event_rel_path, rel_dest_path]
        self.socket.send_multipart(encode(msg))
        self._finish_()

    """
        Protected methods
    """
    def _file_sync_(self):
        if self.event_src_path == None:
            self._logger_.log("ERROR", "Told to sync, but sync source not set!")
            return
        self._logger_.log("INFO", "Syncing file at " + self.event_src_path)
        with open(self.event_src_path, 'rb') as user_file:
            content = user_file.read()
        self._logger_.log("INFO", "Sending filesync command to server for file at " + self.event_rel_path)
        msg = [self.config["USERNAME"], self.msg_identifier["FILESYNC"], self.event_rel_path, content]
        self.socket.send_multipart(encode(msg))

    def _finish_(self):
        self.event_src_path = None
        self.event_rel_path = None
        self.lock.release()

class FileDaemon:
    def __init__(self, msg_identifier, send_config):
        self.target_dir = send_config["PATH_BASE"]
        self._logger_ = EventLogger()
        self.event_handler = SyncEventHandler(msg_identifier, send_config)
        self.observer = Observer()
        self.monitor_flag = threading.Event()
        self.monitor_flag.clear()
        self.watch = None
    def initialize(self):
        self.observer.start()
        self.event_handler.initialize()
        logfile = os.path.dirname(self.target_dir[:-1]) + SLASH + "daemon.log"
        self._logger_.init_session(logfile)

        #Logging
        if (self._logger_.file_info == True):
            self.event_handler.print_files(self.target_dir)

    def _monitor(self):
        self._logger_.log("INFO", "Scheduling observation of " + self.target_dir + " tree...")
        self.watch = self.observer.schedule(self.event_handler, self.target_dir, recursive=True)
        self._logger_.log("INFO", "Server daemon is monitoring " + self.target_dir + "...")
        self.observer.start()
        while (self.monitor_flag.is_set()):
            time.sleep(1)
        self.observer.unschedule(self.watch)
    def full_sync(self):
        self._logger_.log("INFO", "Throwing full directory sync directive from server...")
        self.event_handler.dir_sync(self.target_dir)
    def start(self):
        if self.monitor_flag.is_set:
            return
        else:
            self._logger_.log("INFO", "Server daemon is monitoring at " + self.target_dir + " tree...")
            self.monitor_flag.set()
            threading.Thread(target=self._monitor).start()
    def is_alive(self):
        return self.monitor_flag.is_set()
    def stop(self):
        self.monitor_flag.clear()
        self.observer.stop()
        self.observer.join()