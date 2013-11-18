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

if __name__ == "__main__":
    logger = EventLogger()
    logger.init_session()
    logger.log("system", "main", "Logging successful")




