__author__ = 'wbk3zd'

import zmq
import os
import shutil
import threading
import time
from copy import deepcopy
from Helpers.Encodings import *
from Helpers.Logging.OneDirLogger import EventLogger

class SyncResponder():
    def __init__(self, msg_identifier):
        #Components
        self.context = zmq.Context()
        self.logger = EventLogger()

        #Attributes
        self.msg_identifier = msg_identifier
        self.config = None
        self.listen_flag = threading.Event()
        self.listen_flag.clear()

        #Networking
        self.internal_request_socket = self.context.socket(zmq.PUSH)
        self.server_sync_throw_socket = self.context.socket(zmq.SUB)

    """
        Public methods
    """
    def initialize(self, config):
        """
            Sets up configuration values and connects sockets
        """
        self.config = config

        #Initialize components
        logfile = "." + SLASH + "responder.log"
        self.logger.init_session(logfile)

        #Socket connections
        self.internal_request_socket.connect("tcp://localhost:" + self.config["INTERNAL_REQUEST_PORT"])
        self.logger.log("INFO","Connecting responder to internal client controller over tcp port " + self.config["INTERNAL_REQUEST_PORT"] + "...")

        #Subscribe to sync throws for configured username
        self.server_sync_throw_socket.setsockopt(zmq.SUBSCRIBE, self.config["USERNAME"].encode('ascii', 'replace'))
        self.server_sync_throw_socket.connect("tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_THROW_PORT"])
        self.logger.log("INFO","Subscribed to sync directives at tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_THROW_PORT"] + " for user " + self.config["USERNAME"] + "...")

    def start(self):
        """
            Spawns a new thread with target _listen_ to listen for sync
            directives published by server.
        """
        if self.listen_flag.is_set():
            return
        else:
            self.listen_flag.set()
            threading.Thread(target=self._listen_).start()
            self.logger.log("INFO","Responder is listening for sync directives at tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_SYNC_THROW_PORT"] + " for user " + self.config["USERNAME"] + "...")

    def pause(self):
        """
            Causes any thread in _listen_ to exit gracefully
        """
        self.logger.log("INFO","Responder has paused. No longer listening for sync directives")
        self.listen_flag.clear()

    def stop(self):
        """
            Like pause, but allows for additional cleanup.
            Causes any thread in _listen_ to exit gracefully
        """
        self.logger.log("INFO","Responder is being killed. Going down permanently.")
        self.listen_flag.clear()

    """
        Protected methods
    """
    def _listen_(self):
        """
            Run in a separate thread. Listens for sync directives published by server
            for the subscribed username. Dispatches caught directives to a new thread
            for processing.
        """
        while(self.listen_flag.is_set()):
            #Receive and dispatch until the end of time (or until listen_flag is cleared)
            msg = self.server_sync_throw_socket.recv_multipart()
            msg = decode(msg)

            #Remove topic from message where topic is username
            msg.remove(msg[0])

            #Dispatch command
            threading.Thread(target=self._dispatch_, args=(msg,)).start()

            #Strip away file contents before logging message
            msg_clone = deepcopy(msg)
            if msg_clone[0] == self.msg_identifier["FILESYNC"]:
                msg_clone[-1] = "<contents omitted from log>"

            #Log
            self.logger.log("INFO","Sync Directive received: " + str(msg_clone))


    def _dispatch_(self, msg):
        """
            Entry point for all threads spawned from a message received in
            _listen_. Identifies the sync directive type and calls the appropriate
            internal method to handle.
        """
        #Check to see if message was empty
        if not msg[0]:
            self.logger.log("ERROR","Empty message received from server")
            return

        #Send internal request to controller to stop daemon monitoring of directory, we are about to write
        out = [self.msg_identifier["STOP_MONITORING"], str(threading.current_thread().ident)]
        self.internal_request_socket.send_multipart(encode(out))

        #Give controller and daemon a moment to get their affairs in order
        time.sleep(1)

        #Dispatch
        if msg[0] == self.msg_identifier["FILESYNC"]:
            self._on_sync_(msg)
        elif msg[0] == self.msg_identifier["MKDIR"]:
            self._on_mkdir_(msg)
        elif msg[0] == self.msg_identifier["DELETE"]:
            self._on_remove_(msg)
        elif msg[0] == self.msg_identifier["MOVE"]:
            self._on_move_(msg)
        elif msg[0] == self.msg_identifier["KILL"]:
            msg = [self.msg_identifier["KILL"]]
            self.internal_request_socket.send_multipart(encode(msg)) #Notify controller of impending doom
        else:
            self.logger.log("ERROR","Unrecognized message. Closing without handle: " + str(msg))

        #Cleanup (resumes daemon)
        self._on_finish_()

    def _on_sync_(self, msg):
        """
            Handles file sync events by writing sent contents
            to disk.
        """
        #Get absolute path by appending path base
        dest_path = self.config["PATH_BASE"] + msg[1]

        #Create the target directory if it does not exist
        if not os.path.exists(os.path.dirname(dest_path)):
            os.makedirs(os.path.dirname(dest_path))

        #Log and write
        self.logger.log("INFO","Updating file at " + dest_path)
        with open(dest_path, 'wb') as user_file:
            user_file.write(msg[2])

    def _on_mkdir_(self, msg):
        """
            Creates a directory at the specified relative path if it does not exist
        """
        #Create final destination by appending path base
        dest_path = self.config["PATH_BASE"] + msg[1]

        #Create a directory, or not, the choice is yours
        if(os.path.isdir(dest_path)):
            self.logger.log("INFO","Directory already exists, ignoring make command: " + str(msg))
        else:
            self.logger.log("INFO","Creating directory at " + dest_path)
            os.makedirs(dest_path)

    def _on_remove_(self, msg):
        """
            Deletes the filesystem object at the specified target, recursively if relevant
        """
        dest_path = self.config["PATH_BASE"] + msg[1]

        #If object does not exist, all done
        if not os.path.exists(dest_path):
            self.logger.log("WARNING", dest_path + " does not exist. Can't remove: " + str(msg))
        #Otherwise, remove as appropriate
        elif(os.path.isdir(dest_path)):
            self.logger.log("INFO","Removing entire file tree at " + dest_path)
            shutil.rmtree(dest_path)
        else:
            self.logger.log("INFO","Removing file at" + dest_path)
            os.remove(dest_path)

    def _on_move_(self, msg):
        """
            Called anytime a file system object is moved
        """

        #Get absolute paths
        src_path = self.config["PATH_BASE"] + msg[1]
        dest_path = self.config["PATH_BASE"] + msg[2]

        #If source doesn't exist, throw an error
        if not os.path.exists(src_path):
            self.logger.log("ERROR","File system object at " + dest_path + " does not exist. Cannot move: " + str(msg))
        #Otherwise, handle as appropriate
        elif(os.path.isdir(src_path)):
            self.logger.log("INFO","Moving directory at " + src_path + " to " + dest_path)
            shutil.copytree(src_path, dest_path)
            shutil.rmtree(src_path)
        else:
            self.logger.log("INFO","Moving file at" + src_path + "to" + dest_path)
            shutil.copy2(src_path, dest_path)
            os.remove(src_path)

    def _on_finish_(self):
        """
            Called by every thread after it has finished its dispatch task.
            Asks controller to restore daemon operation. Other cleanup can go here
            as well.
        """
        msg = [self.msg_identifier["START_MONITORING"],str(threading.current_thread().ident)]
        self.internal_request_socket.send_multipart(encode(msg))