__author__ = 'wbk3zd'

from Controllers.Server.Controller import ServerController
import time
import sys
import threading

class OneDirServer():
    def __init__(self):
        self.controller = ServerController()
        self.sync_flag = threading.Event()
        self.sync_flag.clear()

    #Creates account
    def create_account(self):
        print("Enter user name")
        user_name = raw_input()
        print("Enter password")
        password = raw_input()
    #######
        #Code goes here
    #######

    #Turns automatic syncing on
    def _sync(self):
        config = get_config()
        setup_django()
        self.controller.configure(config)
        self.controller.start()
        while self.sync_flag.is_set():
            time.sleep(1)
        self.controller.__teardown__()

    def sync(self):
        self.sync_flag.set()
        threading.Thread(target=self._sync).start()

    #User command that changes signed on user's password
    def change_pass(self):
        print("Nothing yet")
    #######
        #Code goes here
    #######

    #Prints user database
    def all_users(self):
        print("Nothing yet")
    #######
        #Code goes here
    #######

    #Prints files associated with a user
    def print_user_files(self):
        print("Enter username:")
        username = raw_input()
        self.controller.print_user_files(username)

    #Removes user
    def remove(self):
        print("Enter username:")
        username = raw_input()
    #######
        #Code goes here
    #######

    #Admin command that changes the password of the given user
    def change_user_pass(self):
        print("Enter username:")
        username = raw_input()

    def history(self):
        print("Nothing yet")
    #######
        #Code goes here
    #######

def get_config():
    config = {
        "PATH_BASE":"C:\Test2\\",
        "CLIENT_CONTACT_PORT":"3240",
        "SYNC_THROW_PORT":"3241",
        "SYNC_CATCH_PORT":"3242",
        "SYNC_PASSTHRU_PORT":"3243",
        "INTERNAL_REQUEST_PORT":"3244",
        "SYNC_PASSUP_PORT":"3245",
    }
    return config

def setup_django():
    get_config()

def launch():
    server = OneDirServer()
    #Starts command line prompt
    print "List of commands: CreateAccount, Sync, ChangePassword, UserInfo, PrintUserFiles, RemoveUser, ChangeUserPassword, History, Exit"
    sys.stdout.flush()
    response = raw_input(">>")
    while (response != "Exit"):
        if (response == "CreateAccount"):
            server.create_account()
            response = raw_input()
        elif (response == "Sync"):
            server.sync(server)
            response = raw_input()
        elif (response == "ChangePassword"):
            server.change_pass()
            response = raw_input()
        elif (response == "UserInfo"):
            server.all_users()
            response = raw_input()
        elif (response == "PrintUserFiles"):
            server.print_user_files()
            response = raw_input()
        elif (response == "RemoveUser"):
            server.remove()
            response = raw_input()
        elif (response == "ChangeUserPassword"):
            server.change_user_pass()
            response = raw_input()
        elif (response == "History"):
            server.history()
            response = raw_input()
        else:
            print "Invalid Command"
            response = raw_input(">>")
    print("Exited")

if __name__ == "__main__":
    launch()

