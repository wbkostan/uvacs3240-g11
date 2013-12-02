__author__ = 'wbk3zd'

from Controllers.Client.Controller import ClientController
import time
import sys
import threading
from django.db import connection
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

class OneDirClient:
    def __init__(self):
        self.controller = ClientController()
        self.sync_flag = threading.Event()
        self.sync_flag.clear()

    def authenticate(self):
        username = raw_input("Enter username: ")
        password = raw_input("Enter password: ")
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

    #Creates account
    def create_account(self):
        username = raw_input("Enter new username: ")
        password = raw_input("Enter new password: ")
        email = raw_input("Enter new e-mail: ")

        user = User.objects.create_user(username,email,password)

    #Turns automatic syncing on
    def _sync(self):
        config = get_config()
        self.controller.configure(config)
        self.controller.start()
        while self.sync_flag.is_set():
            time.sleep(1)
        self.controller.stop()

    def syncon(self):
        self.sync_flag.set()
        threading.Thread(target=self._sync).start()

    def syncoff(self):
        self.sync_flag.clear()

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
        print ("Command to stop sync: Quit")
        sync_response = raw_input(">>")
        if (sync_response == "Quit"):
            self.controller.stop()
    """

    #User command that changes signed on user's password
    def change_pass(self):
        print ("Please authenticate: ")
        auth = self.authenticate()

        if auth == True:
            print ("Please confirm: ")
            username = raw_input("Enter your username: ")
            newPassword = raw_input("Enter new password: ")

            user = User.objects.get(username__exact = username)
            user.set_password(newPassword)
            user.save()
        elif auth == False:
            print ("Incorrect username and/or password")

    #Prints user database
    def all_users(self):
        """
        ADMIN ONLY
        """
        print("Please log in.")
        username = raw_input("Enter username: ")
        password = raw_input("Enter password: ")
        user = authenticate(username = username, password = password)
        if user is not None:
            if user.is_superuser:
                cursor = connection.cursor()
                cursor.execute("SELECT username FROM auth_user")
                row = cursor.fetchall()
                for entries in row:
                    print entries
            else:
                #Disabled account
                print ("You are not an admin!")
        else:
            #Bad user/pass combo
            print ("Incorrect username and/or password")

    #Prints files associated with a user
    def print_user_files(self):
        """
        ADMIN ONLY
        """
        config = get_config()
        self.controller.configure(config)
        self.controller.print_flag = True
        self.controller.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.controller.__teardown__()

    #Removes user
    def remove(self):
        """
        ADMIN ONLY
        """
        print("Please log in.")
        username = raw_input("Enter username: ")
        password = raw_input("Enter password: ")
        user = authenticate(username = username, password = password)
        if user is not None:
            if user.is_superuser:
                delUser = raw_input("Enter username of User: ")

                confirm = raw_input("Are you sure you want to delete this user? (y/n): ")
                if confirm == "y":
                    dUser = User.objects.get(username__exact = delUser)
                    dUser.delete()
                    print delUser + " has been deleted."
                elif confirm == "n":
                    print "No users have been deleted."
                else:
                    print "Please enter y or n"
            else:
                #Disabled account
                print ("You are not an admin!")
        else:
            #Bad user/pass combo
            print ("Incorrect username and/or password")

    #Admin command that changes the password of the given user
    def change_user_pass(self):
        """
        ADMIN ONLY
        """

        print("Please log in.")
        username = raw_input("Enter username: ")
        password = raw_input("Enter password: ")
        user = authenticate(username = username, password = password)
        if user is not None:
            if user.is_superuser:
                username = raw_input("Enter username of User: ")
                newPassword = raw_input("Enter new password: ")

                user = User.objects.get(username__exact = username)
                user.set_password(newPassword)
                user.save()
            else:
                #Disabled account
                print ("You are not an admin!")
        else:
            #Bad user/pass combo
            print ("Incorrect username and/or password")

    def history(self):
        """
        ADMIN ONLY
        """

        print("Please log in.")
        username = raw_input("Enter username: ")
        password = raw_input("Enter password: ")
        user = authenticate(username = username, password = password)
        if user is not None:
            if user.is_superuser:
                fileClientLog = open("c_controller.log", "r")
                print (fileClientLog.read())
                fileServerLog = open("s_controller.log", "r")
                print (fileServerLog.read())
            else:
                #Disabled account
                print ("You are not an admin!")
        else:
            #Bad user/pass combo
            print ("Incorrect username and/or password")

def get_config():
    config = {
        #"SERVER_ADDR":"172.25.108.164",
        "SERVER_ADDR":"localhost",
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
    print "List of commands: CreateAccount, SyncOn, SyncOff, ChangePassword, UserInfo, PrintUserFiles, RemoveUser, ChangeUserPassword, History, Exit"
    sys.stdout.flush()
    response = raw_input(">>")
    while (response != "Exit"):
        if (response == "CreateAccount"):
            client.create_account()
        elif (response == "SyncOn"):
            client.syncon()
        elif (response == "SyncOff"):
            client.syncoff()
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

