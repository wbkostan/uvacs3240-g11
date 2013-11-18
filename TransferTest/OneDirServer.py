__author__ = 'wbk3zd'

from Controllers.Server.Controller import ServerController
import time
import sys

def __init__(self):
    self.controller = ServerController()

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

#Turns automatic syncing on
def sync(self):
    config = get_config()
    setup_django()
    self.controller.configure(config)
    self.controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        self.controller.__teardown__()

#Prints files associated with a user
def print_user_files(self, username):
    self.controller.print_user_files(username)

#PRINTS USER DATABASE
#def users_info(self):
    #print all user info

def launch():
    #Starts command line prompt
    print "List of commands: Sync, PrintUserFiles, UserInfo"
    sys.stdout.flush()
    response = raw_input()
    if (response == "Sync"):
        sync()
    elif (response == "PrintUserFiles"):
        print "Enter username:"
        sys.stdout.flush()
        userresponse = raw_input()
        print_user_files(userresponse)
#    elif (response == "UserInfo"):
#        users_info()

if __name__ == "__main__":
    launch()

