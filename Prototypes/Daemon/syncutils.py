__author__ = 'wbk3zd'

import watchdog.events
import subprocess

class SyncEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, source, dest):
        self.source_dir = source
        self.dest_dir = dest
        self.sync()
    def on_any_event(self, event):
        self.sync()
    def sync(self):
        subprocess.call(['python', 'rsync.py', '--delete', '--recursive', self.source_dir, self.dest_dir])
if __name__ == "__main__":
    print("Usage")
