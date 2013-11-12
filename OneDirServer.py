__author__ = 'wbk3zd'

from Controllers.Server.Controller import ServerController
import time

def get_config():
    config = {
        "PATH_BASE":"C:\Test2\\",
    }
    return config

def launch():
    config = get_config()
    controller = ServerController(config)
    controller.listen()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.teardown()

if __name__ == "__main__":
    launch()