__author__ = 'wbk3zd'

from Controllers.Client.Controller import ClientController
import time

def get_config():
    config = {
        #"SERVER_ADDR":"172.25.99.145",
        "SERVER_ADDR":"localhost",
        "PATH_BASE":"C:\Test1\OneDir\\",
        "INTERNAL_REQUEST_PORT":"3246",
        "SERVER_SYNC_CATCH_PORT":"3242",
        "SERVER_SYNC_THROW_PORT":"3241",
        "SERVER_CONTACT_PORT":"3240"
    }
    return config

def launch():
    controller = ClientController()
    config = get_config()
    controller.configure(config)
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()

if __name__ == "__main__":
    launch()

