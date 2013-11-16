__author__ = 'wbk3zd'

from Controllers.Server.Controller import ServerController
import time

def get_config():
    config = {
        "PATH_BASE":"C:\Test2\\",
        "CLIENT_CONTACT_PORT":"5556",
        "SYNC_THROW_PORT":"5557",
        "SYNC_CATCH_PORT":"5558",
        "SYNC_PASSTHRU_PORT":"5559",
        "INTERNAL_REQUEST_PORT":"5560",
        "SYNC_PASSUP_PORT":"5561",
    }
    return config

def setup_django():
    get_config()

def launch():
    controller = ServerController()
    config = get_config()
    setup_django()
    controller.configure(config)
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.__teardown__()

if __name__ == "__main__":
    launch()