__author__ = 'wbk3zd'

import time

class EventLogger:
    def __init__(self, path_to_logfile="log.txt"):
        self.logfile = path_to_logfile
    def init_session(self):
        message = "============================{}============================\n".format(time.asctime())
        with open(self.logfile, "a") as logfile:
            logfile.write(message)
    def log(self, client_id, originator, message):
        message = ("SOURCE: {}\tCLIENT: {}\tDATE: {}\t" + message + "\n").format(originator, client_id, time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()))
        with open(self.logfile, "a") as logfile:
            logfile.write(message)

if __name__ == "__main__":
    logger = EventLogger()
    logger.init_session()
    logger.log("system", "main", "Logging successful")

