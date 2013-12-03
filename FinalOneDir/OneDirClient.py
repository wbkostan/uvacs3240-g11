__author__ = 'wbk3zd'

import time
import sys
import threading

import zmq

from Controllers.Client.Controller import ClientController
from Helpers.Encodings import *


def get_config():
    config = {
        "SERVER_ADDR":"172.25.203.214",
        #"SERVER_ADDR":"localhost",
        "ONEDIRSERVER":"3239",
        "PATH_BASE":"C:\Test1\OneDir\\",
        "INTERNAL_REQUEST_PORT":"3246",
        "SERVER_SYNC_CATCH_PORT":"3242",
        "SERVER_SYNC_THROW_PORT":"3241",
        "SERVER_CONTACT_PORT":"3240"
    }
    return config

def get_msg_ids():
    msg_ids = {
        "AUTH":"1", "CREATE_USER":"5", "CHANGE_PASS":"6", "ALL_USERS":"8", "GET_FILES":"9", "REMOVE":"10", "CHANGE_T_PASS":"11", "LOG":"12",
        "ACK":"2", "TRUE":"3", "FALSE":"4", "NACK":"7",
    }
    return msg_ids

class OneDirClient:
    def __init__(self):
        self.config = get_config()
        self.msg_identifiers = get_msg_ids()
        self.controller = ClientController()
        self.sync_flag = threading.Event()
        self.credentials = (None, None)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.child_threads = []
        self.controller = ClientController()
        self.controller.configure(self.config)

    def initialize(self):
        self.socket.connect("tcp://" + self.config["SERVER_ADDR"] + ":" + self.config["ONEDIRSERVER"])
        self.sync_flag.clear()

    def launch(self):
        #Starts command line prompt
        print "List of commands: Logon, CreateAccount, SyncOn, SyncOff, ChangePassword, "
        print "UserInfo, PrintUserFiles, RemoveUser, ChangeUserPassword, History, Exit, "
        sys.stdout.flush()
        response = raw_input(">>")
        response = response.lower()
        while (response != "Exit".lower()):
            try:
                if (response == "CreateAccount".lower()):
                    self.create_account()
                elif (response == "Logon".lower()):
                    self.authenticate()
                elif (response == "SyncOn".lower()):
                    self.syncon()
                elif (response == "SyncOff".lower()):
                    self.syncoff()
                elif (response == "ChangePassword".lower()):
                    self.change_pass()
                elif (response == "UserInfo".lower()):
                    self.all_users()
                elif (response == "PrintUserFiles".lower()):
                    self.print_user_files()
                elif (response == "RemoveUser".lower()):
                    self.remove()
                elif (response == "ChangeUserPassword".lower()):
                    self.change_user_pass()
                elif (response == "History".lower()):
                    self.history()
                else:
                    print("Invalid Command")
                response = raw_input(">>")
                response = response.lower()
            except KeyboardInterrupt:
                response = raw_input(">>")
                response = response.lower()
            except EOFError:
                return


    def authenticate(self):
        username = raw_input("Enter username: ")
        password = raw_input("Enter password: ")
        msg = [self.msg_identifiers["AUTH"], username, password]
        self.socket.send_multipart(encode(msg))
        rep = decode(self.socket.recv_multipart())
        if rep[0] == self.msg_identifiers["ACK"] and rep[1] == self.msg_identifiers["TRUE"]:
            self.credentials = (username, password)
            print("Successfully authenticated as " + username)
        elif rep[1] == self.msg_identifiers["FALSE"]:
            print("Failure. Bad username/password combination")
        else:
            print("Error: Unknown response from server")

    #Creates account
    def create_account(self):
        username = raw_input("Enter new username: ")
        password = raw_input("Enter new password: ")
        email = raw_input("Enter new e-mail: ")

        msg = [self.msg_identifiers["CREATE_USER"], username, password, email]
        self.socket.send_multipart(encode(msg))
        rep = decode(self.socket.recv_multipart())
        if(rep[0] == self.msg_identifiers["ACK"] and rep[1] == self.msg_identifiers["TRUE"]):
            print("Account successfully created")
        else:
            print("Error: Could not create account")

    #Turns automatic syncing on
    def _sync(self):
        self.controller.set_credentials(self.credentials)
        self.controller.start()
        while self.sync_flag.is_set():
            time.sleep(1)
        self.controller.stop()

    def syncon(self):
        while self.credentials == (None, None):
            self.authenticate()
        self.sync_flag.set()
        self.child_threads.append(threading.Thread(target=self._sync))
        for thread in self.child_threads:
            thread.daemon = True
            thread.start()

    def syncoff(self):
        self.sync_flag.clear()
        for thread in self.child_threads:
            self.child_threads.remove(thread)

    #User command that changes signed on user's password
    def change_pass(self):
        while self.credentials == (None, None):
            self.authenticate()

        password = raw_input("Enter your new password: ")
        newPassword = raw_input("Confirm new password: ")

        if password != newPassword:
            print("Error: Passwords do not match")
            return

        msg = [self.msg_identifiers["CHANGE_PASS"], self.credentials[0], self.credentials[1], password]
        self.socket.send_multipart(encode(msg))
        rep = decode(self.socket.recv_multipart())
        if rep[0] == self.msg_identifiers["ACK"] and rep[1] == self.msg_identifiers["TRUE"]:
            print("Password changed successfully")
        else:
            print("Error: Could not change password")

    #Prints user database
    def all_users(self):
        """
        ADMIN ONLY
        """
        while self.credentials == (None, None):
            self.authenticate()

        msg = [self.msg_identifiers["ALL_USERS"], self.credentials[0], self.credentials[1]]
        self.socket.send_multipart(encode(msg))
        rep = decode(self.socket.recv_multipart())

        if rep[0] == self.msg_identifiers["ACK"]:
            for entries in rep[1:]:
                print entries
        elif rep[0] == self.msg_identifiers["NACK"]:
            if rep[1] == "USER":
                print("Error: Invalid credentials")
            else:
                print("Error: Not enough privileges")

    #Prints files associated with a user
    def print_user_files(self):
        """
        ADMIN ONLY
        """
        while self.credentials == (None, None):
            self.authenticate()

        user = raw_input("Enter target username: ")
        msg = [self.msg_identifiers["GET_FILES"], self.credentials[0], self.credentials[1], user]
        self.socket.send_multipart(encode(msg))
        rep = decode(self.socket.recv_multipart())
        if(rep[0] == self.msg_identifiers["ACK"]):
            print("Total files for " + user + ": " + rep[1])
            print("Listed file name/size pairs (in bytes):")
            for obj in rep[2:]:
                info = obj.split("$$")
                print(str(info))
        elif rep[0] == self.msg_identifiers["NACK"]:
            if rep[1] == "USER":
                print("Error: Invalid credentials")
            else:
                print("Error: Not enough privileges")

    #Removes user
    def remove(self):
        """
        ADMIN ONLY
        """
        while self.credentials == (None, None):
            self.authenticate()

        username = raw_input("Enter username: ")
        files = raw_input("Delete all files too?(y/n): ")
        if files.lower() == 'y' or files.lower() == 'yes':
            files = "YES"
        else:
            files = "NO"
        msg = [self.msg_identifiers["REMOVE"], self.credentials[0], self.credentials[1], username, files]
        self.socket.send_multipart(encode(msg))
        rep = decode(self.socket.recv_multipart())
        if rep[0] == self.msg_identifiers["ACK"]:
            print("User account successfully deleted")
        elif rep[0] == self.msg_identifiers["NACK"]:
            if rep[1] == "USER":
                print("Error: Invalid credentials")
            else:
                print("Error: Not enough privileges")

    #Admin command that changes the password of the given user
    def change_user_pass(self):
        """
        ADMIN ONLY
        """
        while self.credentials == (None, None):
            self.authenticate()

        username = raw_input("Enter target username: ")
        newPassword = raw_input("Enter new password: ")

        msg = [self.msg_identifiers["CHANGE_T_PASS"], self.credentials[0], self.credentials[1], username, newPassword]
        self.socket.send_multipart(encode(msg))
        rep = decode(self.socket.recv_multipart())

        if rep[0] == self.msg_identifiers["ACK"]:
            print("Password for " + username + " successfully changed")
        elif rep[0] == self.msg_identifiers["NACK"]:
            if rep[1] == "USER":
                print("Error: Invalid credentials")
            else:
                print("Error: Not enough privileges")

    def history(self):
        """
        ADMIN ONLY
        """
        while self.credentials == (None, None):
            self.authenticate()

        msg = [self.msg_identifiers["LOG"], self.credentials[0], self.credentials[1]]
        self.socket.send_multipart(encode(msg))
        rep = decode(self.socket.recv_multipart())

        if rep[0] == self.msg_identifiers["ACK"]:
            print(rep[1])
        elif rep[0] == self.msg_identifiers["NACK"]:
            if rep[1] == "USER":
                print("Error: Invalid credentials")
            else:
                print("Error: Not enough privileges")

if __name__ == "__main__":
    client = OneDirClient()
    client.initialize()
    client.launch()

