__author__ = 'wbk3zd'

import sys
import time
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from Prototypes.syncutils import SyncEventHandler

class FileDaemon:
    def __init__(self, target, sync_dest):
        self.on = False
        self.target_dir = target
        self.sync_dir = sync_dest
    def monitor(self):
        #logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        #self.event_handler = LoggingEventHandler()
        self.event_handler = SyncEventHandler(self.target_dir, self.sync_dir)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.target_dir, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()


if __name__ == "__main__":
    try:
        #daemon = FileDaemon(sys.argv[1])
        daemon = FileDaemon(sys.argv[1], sys.argv[2])
        daemon.monitor()
    except IndexError:
        print("Usage")