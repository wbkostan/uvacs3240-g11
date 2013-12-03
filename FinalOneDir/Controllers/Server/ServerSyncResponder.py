__author__ = 'wbk3zd'

import os
import shutil
import threading
import time
from copy import deepcopy

import zmq

try:
    from Helpers.Encodings import *
    from Helpers.Logging.OneDirLogger import EventLogger
except ImportError:
    from FinalOneDir.Helpers.Encodings import *
    from FinalOneDir.Logging.OneDirLogger import EventLogger

class SyncResponder():
    def __init__(self, msg_identifier, rec_config):
        #Attributes
        self.msg_identifier = msg_identifier
        self.config = rec_config
        self.listen_flag = threading.Event()

        #Components
        self._logger_ = EventLogger()

        #Networking
        self.context = zmq.Context()
        self.internal_request_socket = self.context.socket(zmq.PUSH)
        self.sync_passthru_lock = threading.RLock()
        self.sync_passthru_socket = self.context.socket(zmq.SUB)

    """
        Public methods
    """
    def initialize(self):
        """
            Must be called before any other public functions can be used. Connects sockets,
            initializes logging, and preps responder for listening for network traffic
        """
        #Ready to listen
        self.listen_flag.clear()

        #Setup logging
        logfile = os.path.dirname(self.config["PATH_BASE"][:-1]) + SLASH + "responder.log"
        self._logger_.init_session(logfile)

        #Connect to controller for internal requests
        self.internal_request_socket.connect("tcp://localhost:" + self.config["INTERNAL_REQUEST_PORT"])
        self._logger_.log("INFO", "Connecting responder to internal server controller over tcp port " + self.config["INTERNAL_REQUEST_PORT"] + "...")

        #Connect to controller for sync directives
        self.sync_passthru_socket.setsockopt(zmq.SUBSCRIBE, self.config["USERNAME"].encode('ascii', 'replace'))
        self.sync_passthru_socket.connect("tcp://localhost:" + self.config["SYNC_PASSTHRU_PORT"])
        self._logger_.log("INFO", "Subscribed to sync directives at tcp://localhost:" + self.config["SYNC_PASSTHRU_PORT"] + "for user " + self.config["USERNAME"] + "...")

    def start(self):
        """
            Public facing handle to start sync responder on new thread
        """
        if self.listen_flag.is_set():
            return
        else:
            self.listen_flag.set()
            threading.Thread(target=self._listen_).start()

    def pause(self):
        """
            Public facing handling to pause sync responder with intent to resume
        """
        self._logger_.log("INFO", "Responder has stopped listening over all ports")
        self.listen_flag.clear()

    def stop(self):
        """
            Public facing handling to stop sync responder with no intent to resume
        """
        self.__teardown__()

    """
        Protected methods
    """
    def _listen_(self):
        """
            Run on a separate thread to listen for all messages sent by controller over internal port for specified client.
            Messages are received and processed according to message directive and content. All messages logged.
        """
        self._logger_.log("INFO", "Responder is listening for sync directives at tcp://localhost:" + self.config["SYNC_PASSTHRU_PORT"] + " for user " + self.config["USERNAME"] + "...")
        while(self.listen_flag.is_set()):
            #Get latest msg
            msg = decode(self.sync_passthru_socket.recv_multipart())

            #Remove topic from message where topic is username
            msg.remove(msg[0])

            #Dispatch
            threading.Thread(target=self._dispatch_, args=(msg,)).start()

            #Strip away file contents before logging message
            msg_clone = deepcopy(msg) #Must be used to prevent msg from being changed while another thread is handling it in dispatch
            if msg_clone[0] == self.msg_identifier["FILESYNC"]:
                msg_clone[-1] = "<contents omitted from log>"

            #Log latest message
            self._logger_.log("INFO","Sync Directive received: " + str(msg_clone))

    def _dispatch_(self, msg):
        """
            Run on a separate thread to handle and individual sync directive. Uses message header
            to identify sync command and defers to appropriate internal method for processing.
        """

        #Check if the message is empty
        if not msg:#Pythonic notation for empty array
            self._logger_.log("ERROR", "Empty message received")
            return #Error recovery

        #Ask controller to bring the file daemon offline before any writing is done
        """
        out = [self.msg_identifier["STOP_MONITORING"], self.config["USERNAME"], str(threading.current_thread().ident)]
        self.internal_request_socket.send_multipart(encode(out))
        time.sleep(1) #wait for local activity to settle
        """

        #Dispatch by header
        if msg[0] == self.msg_identifier["FILESYNC"]:
            self.__on_sync__(msg)
        elif msg[0] == self.msg_identifier["MKDIR"]:
            self.__on_mkdir__(msg)
        elif msg[0] == self.msg_identifier["DELETE"]:
            self.__on_remove__(msg)
        elif msg[0] == self.msg_identifier["MOVE"]:
            self.__on_move__(msg)
        elif msg[0] == self.msg_identifier["KILL"]:
            msg = [self.msg_identifier["KILL"]]
            self.internal_request_socket.send_multipart(encode(msg))#Let controller know client crashed
        else:
            self._logger_.log("ERROR", "Unrecognized message. Closing without handle: " + str(msg))

        #Cleanup
        self.__on_finish__()

    """
        Private methods
    """
    def __teardown__(self):
        """
            Internal method for quick teardown of responder
        """
        #Stop listening over all ports
        self.listen_flag.clear()
        self._logger_.log("INFO", "Sync responder for " + self.config["USERNAME"] + " going down")

    def __on_sync__(self, msg):
        """
            Instructions for processing a file sync command
        """
        #Compose file path using path base and relative path (provided in message)
        dest_path = self.config["PATH_BASE"] + msg[1]

        #If the directory tree doesn't exist, create it
        if not os.path.exists(os.path.dirname(dest_path)):
            os.makedirs(os.path.dirname(dest_path))

        #Log the action
        self._logger_.log("INFO", "Updating file at " + dest_path)

        #Write the bytes
        with open(dest_path, 'wb') as user_file:
            user_file.write(msg[2])

    def __on_mkdir__(self, msg):
        """
            Instructions for processing a make directory command
        """
        #Compose directory path using path base and relative path (provided in message)
        dest_path = self.config["PATH_BASE"] + msg[1]

        #Check if exists, create if not
        if(os.path.isdir(dest_path)):
            self._logger_.log("INFO", "Directory already exists, ignoring make command...")
        else:
            self._logger_.log("INFO", "Creating directory at " + dest_path)
            os.makedirs(dest_path)

    def __on_remove__(self, msg):
        """
            Instructions for processing a delete command
        """
        #Compose absolute path from relative components
        dest_path = self.config["PATH_BASE"] + msg[1]

        #If item doesn't exist, skip
        if not os.path.exists(dest_path):
            self._logger_.log("WARNING", dest_path + " does not exist. Can't remove.")
            return

        #Otherwise, check if directory or file
        if(os.path.isdir(dest_path)):
            self._logger_.log("INFO", "Removing entire file tree at " + dest_path)
            shutil.rmtree(dest_path)
        else:
            self._logger_.log("INFO", "Removing file at" + dest_path)
            os.remove(dest_path)

    def __on_move__(self, msg):
        """
            Instructions for handling moved files/directories
        """
        #construct absolute source and destination paths
        src_path = self.config["PATH_BASE"] + msg[1]
        dest_path = self.config["PATH_BASE"] + msg[2]

        #Check if source exists
        if not os.path.exists(src_path):
            self._logger_.log("ERROR", "File system object at " + dest_path + " does not exist. Cannot move")
            return

        #Check if we should process file or directory
        if(os.path.isdir(src_path)):
            self._logger_.log("INFO", "Moving entire directory at " + src_path + " to " + dest_path)
            shutil.copytree(src_path, dest_path)
            shutil.rmtree(src_path)
        else:
            self._logger_.log("INFO", "Moving file at" + src_path + "to" + dest_path)
            shutil.copy2(src_path, dest_path)
            os.remove(src_path)

    def __on_finish__(self):
        """
        with self.sync_passthru_lock:
            msg = [self.msg_identifier["START_MONITORING"], self.config["USERNAME"], str(threading.current_thread().ident)]
            self.internal_request_socket.send_multipart(encode(msg))
        """