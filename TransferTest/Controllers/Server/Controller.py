__author__ = 'wbk3zd'

from ServerFileDaemon import FileDaemon
from ServerSyncResponder import SyncResponder
import threading
import zmq
from Helpers.Encodings import *
from Helpers.Logging.OneDirLogger import EventLogger
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

"""
    Sample of config dictionary which initializes controller
    config = {
        "PATH_BASE":"C:\Test2\\",
        "CLIENT_CONTACT_PORT":"3240",
        "SYNC_THROW_PORT":"3241",
        "SYNC_CATCH_PORT":"3242",
        "SYNC_PASSTHRU_PORT":"3243",
        "INTERNAL_REQUEST_PORT":"3244",
        "SYNC_PASSUP_PORT":"3245",
    }
"""

class ServerController:
    def __init__(self):
        #Standardize message headers across all components
        self.msg_identifier = {
            "FILESYNC":"1", "MKDIR":"2", "DELETE":"3", "MOVE":"4", #Sync directive commands
            "ACK":"5","LISTENING":"7","MONITORING":"8", #Client-Server commands
            "START_MONITORING":"9","STOP_MONITORING":"10","KILL":"11", #Internal request commands
            "LOGIN":"12","TRUE":"13","FALSE":"14", "LOGOUT":"15", "REGISTER":"16", "PASSCHANGE":"17" #Authentication commands
        }

        #Components
        self.client_components = {}
        self._logger_ = EventLogger()

        #Networking
        self.context = zmq.Context()
        self.internal_request_socket = self.context.socket(zmq.PULL) #Handles super-level control requests by components
        self.client_contact_socket = self.context.socket(zmq.REP) #P2P client-server communication
        self.sync_throw_socket = self.context.socket(zmq.PUB) #Sends sync directives to subscribed clients
        self.sync_catch_socket = self.context.socket(zmq.PULL) #Receives sync directives from subscribed clients
        self.sync_passthru_socket = self.context.socket(zmq.PUB) #Sends received sync directives to correct responder
        self.sync_passup_socket = self.context.socket(zmq.PULL) #Pulls sync directives and sends them to publisher

        #Attributes
        self.config = None
        self.listen_flag = threading.Event()
        self.listen_flag.clear()

    """
        Public methods
    """
    def configure(self, config):
        """
            Sets configuration values and binds sockets to ports.
            Must be called before any other controller function can be called
        """

        #Set configuration values
        self.config = config

        #Ensure our path base ends in a slash
        if config["PATH_BASE"][-1] != SLASH:
            config["PATH_BASE"] = config["PATH_BASE"] + SLASH

        logfile = "." + SLASH + "s_controller.log"
        self._logger_.init_session(logfile)

        ################################Server socket bindings######################################################
        """
            Internal communication sockets
        """
        self.internal_request_socket.bind("tcp://*:" + self.config["INTERNAL_REQUEST_PORT"])
        self._logger_.log("INFO", "Server controller listening for internal requests at tcp://localhost:" + self.config["INTERNAL_REQUEST_PORT"] + "...")

        self.sync_passthru_socket.bind("tcp://*:" + self.config["SYNC_PASSTHRU_PORT"])
        self._logger_.log("INFO", "Server controller ready to pass client sync directives to responders at tcp://localhost:" + self.config["SYNC_PASSTHRU_PORT"] + "...")

        self.sync_passup_socket.bind("tcp://*:" + self.config["SYNC_PASSUP_PORT"])
        self._logger_.log("INFO", "Server controller listening for daemon component sync directives at tcp://localhost:" + self.config["SYNC_PASSUP_PORT"] + "...")

        """
            External client-server communication sockets
        """
        self.client_contact_socket.bind("tcp://*:" + self.config["CLIENT_CONTACT_PORT"])
        self._logger_.log("INFO", "Server controller listening for client requests at tcp://localhost:" + self.config["CLIENT_CONTACT_PORT"] + "...")

        self.sync_throw_socket.bind("tcp://*:" + self.config["SYNC_THROW_PORT"])
        self._logger_.log("INFO", "Server controller ready to publish sync directives at tcp://localhost:" + self.config["SYNC_THROW_PORT"] + "...")

        self.sync_catch_socket.bind("tcp://*:" + self.config["SYNC_CATCH_PORT"])
        self._logger_.log("INFO", "Server controller listening for client sync directives at tcp://localhost:" + self.config["SYNC_CATCH_PORT"] + "...")
        #################################End socket bindings########################################################

    def start(self):
        """
            Kicks off four threads to listen over their respective sockets for messages. Threads will
            handle starting new client connections or handling sync directives/requests as they are made
            by clients or child components respectively
        """

        #Tell all threads we are good to go
        self.listen_flag.set()

        #Kick off threads
        threading.Thread(target=self._listen_internal_).start() #listening for internal requests
        threading.Thread(target=self._listen_client_).start() #client requests
        threading.Thread(target=self._listen_sync_catch_).start() #sync directives thrown by client
        threading.Thread(target=self._listen_sync_passup_).start() #sync directives meant for clients passed up internally

    """
        Protected methods
    """
    def _authenticate_client_(self, username, password):
        """
            Given a username and password, return true if combination is valid,
            return false otherwise.
        """

        user = authenticate(username = username, password = password)
        if user is not None:
            if user.is_active:
                return True #Always authenticate until actual authentication is added.
            else:
                #Disabled account
                return False
        else:
            #Bad user/pass combo
            return False

    def _register_client_(self, username, password, email):
        User.objects.create_user(username,password,email)
        return True

    def _change_client_password_(self, username, newPassword):
        user = User.objects.get(username__exact = username)
        user.set_password(newPassword)
        user.save()
        return True

    def _listen_internal_(self):
        """
            Run by a separate thread to listen for all super-level control requests made
            by client components. Control requests include daemon start/stop requests and
            kill commands.
        """

        #Keep track of all the threads asking us to not monitor client directory
        #If client performs multiple chanes in a short time, the sync responder will
        #kick off several threads at once to handle all these changes and each thread will
        #request that controller stop monitoring. We must make sure we don't start daemon again
        #until all threads have finished their work.
        blocking_threads = {}

        #listen flag set by controller. allows control over thread execution
        while self.listen_flag.is_set():
            msg = decode(self.internal_request_socket.recv_multipart())

            #Sync responder has received a request to write to client directory
            #Please stop monitoring directory while we write!
            if msg[0] == self.msg_identifier["STOP_MONITORING"]:
                #no active working threads for this user, start new list
                if not msg[1] in blocking_threads: #Pythonic notation for this key msg[1] does not exist in dict
                    blocking_threads[msg[1]] = []
                #append this thread id to list of working threads for this client, pause daemon
                blocking_threads[msg[1]].append(int(msg[2]))
                print(str(blocking_threads))
                self.client_components[msg[1]][0].stop()
            elif msg[0] == self.msg_identifier["START_MONITORING"]:
                try:
                    print(str(msg))
                    blocking_threads[msg[1]].remove(int(msg[2]))
                except ValueError:
                    self._logger_.log("WARNING", "Thread never told controller to block, but asked for unblock")
                if not blocking_threads[msg[1]]:
                    self.client_components[msg[1]][0].start()

    def _listen_client_(self):
        """
            Listens for requests made by a client and replies accordingly. Responsible for receiving initial
            logon requests and starting up client components
        """
        while self.listen_flag.is_set():
            msg = decode(self.client_contact_socket.recv_multipart())

            #New connection request
            if msg[0] == self.msg_identifier["LOGIN"]:
                if self._authenticate_client_(msg[1], msg[2]):
                    self._connect_client_(msg[1]) #Once authenticated, start up some pair components
                    msg = [self.msg_identifier["ACK"], self.msg_identifier["TRUE"]]
                else:
                    msg = [self.msg_identifier["ACK"], self.msg_identifier["FALSE"]]

            #Disconnection request
            elif msg[0] == self.msg_identifier["LOGOUT"]:
                self._disconnect_client_(msg[1])
                msg = [self.msg_identifier["ACK"], msg[1]]

            elif msg[0] == self.msg_identifier["REGISTER"]:
                self._register_client_(msg[1], msg[2], msg[3])
                msg = [self.msg_identifier["ACK"], self.msg_identifier["TRUE"]]

            #Client has started responder, requesting full directory sync
            elif msg[0] == self.msg_identifier["LISTENING"]:
                self.__start_client_daemon__(msg[1]) #client is listening? good, start up daemon and full sync
                msg = [self.msg_identifier["ACK"], msg[1]]

            #No matter the message, send a response
            self.client_contact_socket.send_multipart(encode(msg))

    def _listen_sync_catch_(self):
        """
            Catch point for sync directives thrown by all clients. Receives these sync directives and passes
            them down to the respective components through a publish/subscribe socket. Must exists to prevent
            client from having to bind to a port and share with server if we are to maintain minimal port bindings.
            All bound ports should be server side
        """
        while self.listen_flag.is_set():
            msg = self.sync_catch_socket.recv_multipart()
            self.sync_passthru_socket.send_multipart(msg)

    def _listen_sync_passup_(self):
        """
            Catches all sync requests sent up by file daemons and publishes them
            to all clients subscribed to appropriate username. Exists to prevent client from
            being forced to bind to a port so that server components can talk to client. Also
            encourages minimal port usage.
        """
        while self.listen_flag.is_set():
            msg = self.sync_passup_socket.recv_multipart()
            self.sync_throw_socket.send_multipart(msg)

    def _connect_client_(self, username):
        """
            Setup up pair daemon/responder components if they don't already exist.
            Increase count of connected clients. Start the responder component
        """
        if not username in self.client_components:
            #Set up configuration values
            daemon_config = responder_config = self.config
            daemon_config["USERNAME"] = responder_config["USERNAME"] = username
            daemon_config["PATH_BASE"] = responder_config["PATH_BASE"] = self.config["PATH_BASE"] + username + SLASH + "OneDir" + SLASH

            #Create new components
            daemon = FileDaemon(self.msg_identifier, daemon_config)
            responder = SyncResponder(self.msg_identifier, responder_config)

            #Initialize those components
            responder.initialize()
            daemon.initialize()

            #Start the responder
            responder.listen()

            #Map these components to the client username
            self.client_components[username] = (daemon, responder, 1)
        else:
            #Bump up count of logged in clients
            self.client_components[username][2] += 1

    def _disconnect_client_(self, username):
        """
            Brings client safely offline. Stops components if no online clients with same username
            or currently logged in.
        """
        if username in self.client_components:
            #Decrement count of online users under this name
            self.client_components[username][2] -= 1

            #If no more online users under this client name, shutdown this client
            if(self.client_components[username][2] == 0):
                self.client_components[username][0].__teardown__()
                self.client_components[username][1].__teardown__()
                del self.client_components[username] #Remove client username as key from dict

    """
        Private Methods
    """
    def __start_client_daemon__(self, username):
        """
            Called only once client responder is confirmed online. Bring daemon
            online and execute a full directory sync to merge offline changes
        """
        if username in self.client_components:
            self.client_components[username][0].full_sync()
            if not self.client_components[username][0].is_alive():
                self.client_components[username][0].start()

    def __teardown__(self):
        """
            Something bad happened. Everything must go. Tell all connected clients
            they must DC immediately. Server is no longer listening for requests.
        """
        self.listen_flag.clear()
        for key in self.client_components:
            self.client_components[key][0].__teardown__()
            self.client_components[key][1].__teardown__()
            self.client_components[key][2] = 0
            msg = [key, self.msg_identifier["DISCONNECT"]]
            self.sync_throw_socket.send_multipart(encode(msg))
            del self.client_components[key]
