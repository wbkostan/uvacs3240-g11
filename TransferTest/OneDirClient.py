__author__ = 'wbk3zd'

from Controllers.Client.Controller import ClientController
import time
import sys
import threading

class OneDirClient:
    def __init__(self):
        self.controller = ClientController()
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
    """
    def _sync(self):
        config = get_config()
        self.controller.configure(config)
        self.controller.start()
        while self.sync_flag.is_set():
            time.sleep(1)
        self.controller.__teardown__()
    """

    """
    def sync(self):
        self.sync_flag.set()
        threading.Thread(target=self._sync).start()
    """

    def sync(self):
        config = get_config()
        self.controller.configure(config)
        self.controller.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.controller.__teardown__()

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
        "SERVER_ADDR":"172.25.99.208",
        #"SERVER_ADDR":"localhost",
        "PATH_BASE":"C:\Test1\OneDir\\",
        "INTERNAL_REQUEST_PORT":"3246",
        "SERVER_SYNC_CATCH_PORT":"3242",
        "SERVER_SYNC_THROW_PORT":"3241",
        "SERVER_CONTACT_PORT":"3240"
    }
    return config

def launch():
    client = OneDirClient()
    #Starts command line prompt
    print "List of commands: CreateAccount, Sync, ChangePassword, UserInfo, PrintUserFiles, RemoveUser, ChangeUserPassword, History, Exit"
    sys.stdout.flush()
    response = raw_input(">>")
    while (response != "Exit"):
        if (response == "CreateAccount"):
            client.create_account()
        elif (response == "Sync"):
            client.sync()
        elif (response == "ChangePassword"):
            client.change_pass()
        elif (response == "UserInfo"):
            client.all_users()
        elif (response == "PrintUserFiles"):
            client.print_user_files()
        elif (response == "RemoveUser"):
            client.remove()
        elif (response == "ChangeUserPassword"):
            client.change_user_pass()
        elif (response == "History"):
            client.history()
        else:
            print("Invalid Command")
        response = raw_input(">>")
    print("Exited")

if __name__ == "__main__":
    launch()

