__author__ = 'wbk3zd'

import time
import sys

class EventLogger:
    def __init__(self):
        self.logfile = None
        self.file_info = False
    def init_session(self, path_to_logfile=".\log.txt"):
        self.logfile = path_to_logfile
        message = "============================{}============================\n".format(time.asctime())
        with open(self.logfile, "a") as logfile:
            logfile.write(message)
    def join_session(self, path_to_logfile=".\log.txt"):
        self.logfile = path_to_logfile
    def log(self, status, message):
        message = ("STATUS: {}\tDATE: {}\t" + message + "\n").format(status, time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()))
        with open(self.logfile, "a") as logfile:
            logfile.write(message)

    #Log user information from user database, how to access database
    def user_info(self):
        message = ("Users: ...")
        with open(self.logfile, "a") as logfile:
            logfile.write(message)

if __name__ == "__main__":
    logger = EventLogger()
    logger.init_session()
    logger.log("INFO", "Logging successful")

    #Admin commands, how to check if user type is admin
    # if (user_type == "admin"):
    #     print "List of admin commands: userinfo, fileinfo"
    #     sys.stdout.flush()
    #     response = raw_input()
    #     if (response == "userinfo"):
    #         logger.user_info()
    #     if (response == "fileinfo"):
    #         logger.file_info = True



