__author__ = 'wbk3zd'

from Controllers.Client.Controller import ClientController
import time

def get_config():
    config = {
        "SERVER_ADDR":"localhost",
        "PATH_BASE":"C:\Test1\OneDir\\",
        "SERVER_SYNC_CATCH_PORT":"5558",
        "SERVER_SYNC_THROW_PORT":"5557",
        "SERVER_CONTACT_PORT":"5556"
    }
    return config

def launch():
    controller = ClientController()
    config = get_config()
    controller.initialize(config)
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()

if __name__ == "__main__":
    launch()

