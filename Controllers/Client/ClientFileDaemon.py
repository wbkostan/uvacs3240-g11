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
    def __init__(self, msg_identifier):
        #Attributes
        self.msg_identifier = msg_identifier
        self.config = None
        self._event_src_path_ = None
        self._event_rel_path_ = None
        self.__lock__ = threading.RLock()

        #Components
        self._context_ = zmq.Context()
        self._logger_ = EventLogger()

        #Networking
        self._socket_ = self._context_.socket(zmq.PUSH)

    def initialize(self, config):
        """
            Sets configuration values, connects sockets, and initializes components
        """
        self.config = config

        #Initialize components
        self._logger_.join_session(".\\daemon.log")

        #Setup networking
        self._socket_.connect("tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_CATCH_PORT"])
        self._logger_.log("INFO","Daemon connected to server at " + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_CATCH_PORT"] + "...")

    def dir_sync(self, top):
        """
            Recursively synchronizes a directory on the client side. Creates any structure which does not
            exist. Does not send delete commands for file system objects server side which should not exist.
        """

        #Acquire access to source and dest paths
        self.__lock__.acquire()

        #Preserve source absolute and relative paths
        copy_src_path = self._event_src_path_
        copy_rel_path = self._event_rel_path_

        #Tell server this top level directory should exist
        msg = [self.config["USERNAME"], self.msg_identifier["MKDIR"], os.path.relpath(top, self.config["PATH_BASE"])]
        self._socket_.send_multipart(encode(msg))

        #Recurse over objects in this directory
        for parent, sub_dirs, files in os.walk(top):
            #Synchronize all files
            for user_file in files:
                self._event_src_path_ = parent + user_file
                self._event_rel_path_ = os.path.relpath(self._event_src_path_, self.config["PATH_BASE"])
                self._file_sync_()
                self._finish_()
            #Recurse into sub-directories
            for sub_dir in sub_dirs:
                self.dir_sync((parent+sub_dir))

        #Restore saved values for src and dest paths
        self._event_src_path_ = copy_src_path
        self._event_rel_path_ = copy_rel_path

        #Give up source paths
        self.__lock__.release()

    def on_any_event(self, event):
        """
            Called by a watchdog.observer whenever a filesystem event occurs
            Record references to source path of event, deduce the relative path
            that the server cares about
        """

        #Access source paths
        self.__lock__.acquire()

        self._event_src_path_ = event.src_path
        self._event_rel_path_ = os.path.relpath(self._event_src_path_, self.config["PATH_BASE"]) #Chop off the path base

    def on_created(self, event):
        """
            Called by a watchdog.observer whenever a new filesystem object is created
            in the observed directory. Sends the creation command to the server
        """
        if os.path.isdir(self._event_src_path_):
            self._logger_.log("INFO","Sending mkdir command to server for directory at " + self._event_rel_path_)
            msg = [self.config["USERNAME"], self.msg_identifier["MKDIR"], self._event_rel_path_]
            self._socket_.send_multipart(encode(msg))
        else:
            #Synchronizing a file will also create if file doesn't exist
            self._file_sync_()
        self._finish_() #Cleanup

    def on_deleted(self, event):
        """
            Called by a watchdog.observer whenever a filesystem object is deleted
            in the observed directory. Sends a delete command to the server
        """
        self._logger_.log("INFO","Sending delete command to server for file system object at " + self._event_rel_path_)
        msg = [self.config["USERNAME"], self.msg_identifier["DELETE"], self._event_rel_path_]
        self._socket_.send_multipart(encode(msg))
        self._finish_()
    def on_modified(self, event):
        """
            Called by a watchdog.observer whenever a filesystem object is modified
            in the observed directory. Sends the modification information to the server.
        """
        if os.path.isfile(self._event_src_path_):
            self._file_sync_()
        else:
            #Currently don't know how to react to this command
            self._logger_.log("INFO","<handling a modified directory>")
        self._finish_()

    def on_moved(self, event):
        """
            Called by a watchdog.observer whenever a filesystem object is moved
            in the observed directory. Sends the source and dest information to the server.
        """

        #Record absolute and relative path information for the destination
        event_dest_path = event.dest_path
        rel_dest_path = os.path.relpath(event_dest_path, self.config["PATH_BASE"])

        #Log and send
        self._logger_.log("INFO","Sending move command to server from " + self._event_rel_path_ + " to " + rel_dest_path)
        msg = [self.config["USERNAME"], self.msg_identifier["MOVE"], self._event_rel_path_, rel_dest_path]
        self._socket_.send_multipart(encode(msg))
        self._finish_()

    """
        Protected Methods
    """
    def _file_sync_(self):
        """
            Sends the contents of the file in self.event_src_path to the server.
            If file does not exist on server it is created. If file exists, it is
            overwritten with these contents
        """

        #If someone tries to call this method without setting a path
        if self._event_src_path_ == None:
            self._logger_.log("ERROR","File daemon attempted to execute a file sync without a source directory")
            return

        #Read as bytes
        with open(self._event_src_path_, 'rb') as user_file:
            content = user_file.read()

        #Log and send
        self._logger_.log("INFO","Sending filesync command to server for file at " + self._event_rel_path_)
        msg = [self.config["USERNAME"], self.msg_identifier["FILESYNC"], self._event_rel_path_, content]
        self._socket_.send_multipart(encode(msg))

    def _finish_(self):
        """
            Must be called after any event. Releases the lock held by the managing thread
            and resets source and destination paths
        """
        self._event_src_path_ = None
        self._event_rel_path_ = None
        self.__lock__.release()

class FileDaemon:
    def __init__(self, msg_identifier):
        #Components
        self._event_handler_ = SyncEventHandler(msg_identifier)
        self._observer_ = Observer()
        self._logger_ = EventLogger()

        #Attributes
        self.config = None
        self.target_dir = None
        self.__watch__ = None

        #Flags
        self._monitor_flag_ = threading.Event()
        self._monitor_flag_.clear()

    def initialize(self, config):
        """
            Sets up configuration values, initializes components
        """
        self.config = config
        self.target_dir = self.config["PATH_BASE"]

        #Initialize components
        self._logger_.init_session(".\\daemon.log")
        self._event_handler_.initialize(self.config)
        self._observer_.start()

    def start(self):
        """
            Starts/resumes observing a target directory. Wraps up the monitor method
            which is used as the target for a separate thread.
        """
        if self._monitor_flag_.is_set():
            return #Already running
        else:
            self._monitor_flag_.set()
            threading.Thread(target=self._monitor_).start()

    def full_sync(self):
        """
            Handle for the directory sync method of event_handler which
            allows controller to request a sync of entire directory
        """
        self._event_handler_.dir_sync(self.target_dir)

    def pause(self):
        """
            Pause observation with intent to resume
        """
        self._monitor_flag_.clear()

    def stop(self):
        """
            End observation with no intent to resume
        """
        self._monitor_flag_.clear()
        self._observer_.stop() #stop observing
        self._observer_.join() #wait for all threads to be done

    """
        Protected methods
    """
    def _monitor_(self):
        """
            Function run on separate thread which acts as parent to observer thread(s).
            Used to control operation flow of observer using monitor_flag
        """
        self._logger_.log("INFO","Scheduling observation of " + self.target_dir + " tree...")
        self.__watch__ = self._observer_.schedule(self._event_handler_, self.target_dir, recursive=True)
        while (self._monitor_flag_.is_set()):
            time.sleep(1)
        self._observer_.observer.unschedule(self.__watch__)