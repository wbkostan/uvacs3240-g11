__author__ = 'wbk3zd'

import sys
import time
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from syncutils import SyncEventHandler
from syncutils import SyncResponder
import threading

class FileDaemon:
    def __init__(self, msg_identifier, send_config):
        self.on = False
        self.target_dir = send_config["PATH_BASE"]
        self.event_handler = SyncEventHandler(msg_identifier, send_config)
        self.observer = Observer()
        self.monitor_flag = threading.Event()
        self.monitor_flag.clear()
        print("Scheduling observation of " + self.target_dir + " tree...")
        self.observer.schedule(self.event_handler, self.target_dir, recursive=True)
    def _monitor(self):
        print("Client daemon is monitoring " + self.target_dir + "...")
        print("")
        self.observer.start()
        try:
            while (self.monitor_flag.is_set()):
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
    def monitor(self):
        self.monitor_flag.set()
        threading.Thread(target=self._monitor).start()
    def pause(self):
        self.monitor_flag.clear()
    def resume(self):
        self.monitor()




if __name__ == "__main__":
    msg_identifier = {
        "FILESYNC":"1",
        "MKDIR":"2",
        "DELETE":"3",
        "MOVE":"4",
        "ACK":"5"
    }

    send_config = {
        "REC_ADDRESS":"localhost",
        "REC_PORT":"5555",
        "PATH_BASE":"C:/Test1/OneDir/",
    }
    daemon = FileDaemon(send_config["PATH_BASE"], msg_identifier, send_config)
    try:
        daemon.monitor()
    except IndexError:
        print("Usage")