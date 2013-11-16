__author__ = 'wbk3zd'

import zmq
import threading
from Helpers.Encodings import *
from ClientFileDaemon import FileDaemon
from ClientSyncResponder import SyncResponder

"""
    Sample of config dictionary which initializes controller:
    config = {
        "SERVER_ADDR":"localhost",
        "PATH_BASE":"C:\Test1\OneDir",
        "SERVER_SYNC_CATCH_PORT":"5558",
        "SERVER_SYNC_THROW_PORT":"5557",
        "SERVER_CONTACT_PORT":"5556"
    }
"""

class ClientController:
    """
        Singleton class which servers as the control point for the child components
        which monitor the system tree and respond to sync directives from server.
        Opens one port to serve as a contact point for child components requesting
        super level control actions. Binds to one port on the server to establish
        communication lines and provide authentication information
    """
    def __init__(self):
        #Standardize message headers across all components
        self.msg_identifier = {
            "FILESYNC":"1", "MKDIR":"2", "DELETE":"3", "MOVE":"4", #Sync directive commands
            "ACK":"5","LISTENING":"7","MONITORING":"8", #Client-Server commands
            "START_MONITORING":"9","STOP_MONITORING":"10","KILL":"11", #Internal request commands
            "LOGIN":"12","TRUE":"13","FALSE":"14","LOGOUT":"15", #Authentication commands
        }

        #Components
        self._responder = SyncResponder(self.msg_identifier) #Listens for and responds to sync directives
        self._daemon = FileDaemon(self.msg_identifier) #Monitors file system and sends sync directives

        #Networking
        self._context = zmq.Context()
        self._internal_request_socket = self._context.socket(zmq.PULL) #Listens for control requests from child components
        self._server_contact_socket = self._context.socket(zmq.REQ) #Connection establishment/teardown

        #Attributes
        self.config = None
        self._listen_flag = threading.Event()

    """
        Public Methods for Controller Interface
    """
    def configure(self, config):
        """
            Establish configuration values and bind sockets. Must be called before
            rest of controller is usable
        """
        self.config = config

        #Port bindings
        self._internal_request_socket.bind("tcp://*:" + self.config["INTERNAL_REQUEST_PORT"]) #For internal control requests
        print("Client controller listening for internal requests over tcp port " + self.config["INTERNAL_REQUEST_PORT"] + "...")

        #Port connections
        self._server_contact_socket.connect("tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_CONTACT_PORT"]) #Port for connection establishment
        print("Client controller connected to server at " + self.config["SERVER_ADDR"] + ":" + self.config["SERVER_CONTACT_PORT"] + "...")

    def start(self):
        """
            Brings the client controller online by establishing a connection with the server
            then bringing online client services (responder, daemon)
        """

        #Check if controller has been configured yet
        if self.config == None:
            print("Error: System must be initialized before use!")
            return

        #Start listening for internal requests
        self._listen_flag.set()
        self._listen_()

        #Open connection to server
        self._connect_()

    def stop(self):
        """
            Wrapper for protected disconnect function
        """

        #Check if controller has been configured yet
        if self.config == None:
            print("Error: System must be initialized before use!")
            return

        #Disconnect from server
        self._disconnect_()

    """
        Protected methods
    """
    def _listen_(self):
        """
            Launches a separate thread to listen for all internal requests made of controller.
            Internal requests are thrown by child components and are super-level control requests
            such as requests to cease directory monitoring or requests to kill all services
        """
        self._listen_flag.set()
        threading.Thread(target=self.__listen__).start()

    def _authenticate_(self):
        """
            Responsible for authenticating client with server. Successful authentication
            starts the pair daemon/responder components server side. With authentication,
            there will be no components server side listening for this clients requests
        """

        #Prompt for username/password
        username = raw_input("Username: ")
        password = raw_input("Password: ")

        #Package credentials, send to server, await response
        msg = [self.msg_identifier["LOGIN"], username, password]
        self._server_contact_socket.send_multipart(encode(msg))
        rep = decode(self._server_contact_socket.recv_multipart())

        #Parse response, decide whether or not credentials were approved
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.msg_identifier["TRUE"]: #Golden case
            self.config["USERNAME"] = username #Set the active user at this controller
            return True
        elif rep[1] == self.msg_identifier["FALSE"]: #Bad username/password combination
            print("Warning: Bad username/password. Try again.")
            return False
        elif rep[0] != self.msg_identifier["ACK"]: #Unknown message received
            print("Error: Bad response from server. Going down")
            self.__teardown__() #Kill everything!
            return False

    def _connect_(self):
        """
            Opens a connection to the server (which establishes a responder/daemon component set in this
            clients name). When connection is acked, starts the clients own components
        """

        #Authenticate current user
        #Server starts pair components when user successfully authenticates
        auth = False
        while not auth:
            auth = self._authenticate_()
        print("Authenticated current user. Going online...")

        #Start up the client responder and daemon
        self.__start_components__() #start a responder

    def _disconnect_(self):
        """
            Peaceful disconnect from server. Best method for closing existing connection.
            Server will close down pair components if this is the last client in this user's
            name.
        """

        #Stop listening for internal requests. No interruptions!
        self._listen_flag.clear()

        #Tell server that we're done
        msg = [self.msg_identifier["DISCONNECT"], self.config["USERNAME"]]
        self._server_contact_socket.send_multipart(encode(msg))
        rep = decode(self._server_contact_socket.recv_multipart())

        #Decide whether disconnect was successful
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.config["USERNAME"]:
            print("Disconnected from server, going down peacefully")
        else:
            print("Error: Bad disconnect. Going down anyway.")

        #Bring client components offline
        self._responder.teardown()
        self._daemon.teardown()

    """
        Private Methods
    """
    def __teardown__(self):
        """
            Forceful exit of all services. Makes no attempt to peacefully disconnect from server.
            Used when internal errors are tripped.
        """

        #Stop listening
        self._listen_flag.clear()

        #Kill client components
        self._responder.teardown()
        self._daemon.teardown()

    def __start_components__(self):
        """
            Starts the client-side components. Responder starts, then server is informed.
            Server does full directory sync back to client. Client starts daemon then does
            full directory sync back to server.
        """

        #Setup responder
        self._responder.initialize(self.config)
        print("Bringing client responder online...")

        #Bring responder online. Ready to respond to sync directives
        self._responder.listen()

        #Tell server we're ready for directory sync
        msg = [self.msg_identifier["LISTENING"], self.config["USERNAME"]]
        print("Sending acknowledgement to server, awaiting intial directory sync...")
        self._server_contact_socket.send_multipart(encode(msg))
        rep = decode(self._server_contact_socket.recv_multipart())

        #Server is done syncing full directory, time to sync ours
        if rep[0] == self.msg_identifier["ACK"] and rep[1] == self.config["USERNAME"]:
            print("Responder service started, monitoring file system, full services started...")
        else:
            print("Error: Bad response from server. Going down.")
            self.__teardown__()

        #Set up our daemon
        self._daemon.initialize(self.config)

        #Execute full sync back to server
        self._daemon.full_sync()

    def __listen__(self):
        """
            Run by a separate internal thread so long as listen_flag is set.
            Looks for internal requests and handles as appropriate.
        """

        #Keep track of all the threads asking for a daemon halt so we don't
        #restart daemon prematurely
        blocking_threads = []
        while self._listen_flag.is_set():

            #Get next internal request
            msg = decode(self._internal_request_socket.recv_multipart())

            #Request to halt daemon services while responder is writing to directory
            if msg[0] == self.msg_identifier["STOP_MONITORING"]:
                blocking_threads.append(int(msg[1])) #Record who asked for the block
                self._daemon.pause() #Stop the daemon while blocker works

            #Request to resume daemon services. Writing is done.
            elif msg[0] == self.msg_identifier["START_MONITORING"]:
                if int(msg[1]) in blocking_threads:
                    blocking_threads.remove(int(msg[1])) #Remove this thread from the list of blocking
                if not blocking_threads: #Pythonic notation for empty array
                    self._daemon.monitor() #Resume daemon once no more threads are blocking

            #Passup message. Server is trying to get in contact with client. Something bad happened
            #Kill all services immediately. Don't ask questions. Don't pass go. Don't collect $200
            elif msg[0] == self.msg_identifier["KILL"]:
                print("Error: Forceful interrupt command received from server. Killing all services")
                self.__teardown__()

        #Exited while loop. Someone killed our listen_flag
        print("Client stopped listening for internal requests")