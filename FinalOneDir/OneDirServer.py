__author__ = 'wbk3zd'

from Controllers.Server.Controller import ServerController
import time
import zmq
import os
import threading
from shutil import rmtree
from Helpers.Encodings import *
from django.db import connection
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def get_config():
    config = {
        "ONEDIRSERVER":"3239",
        "PATH_BASE":"C:\Test2\\",
        "CLIENT_CONTACT_PORT":"3240",
        "SYNC_THROW_PORT":"3241",
        "SYNC_CATCH_PORT":"3242",
        "SYNC_PASSTHRU_PORT":"3243",
        "INTERNAL_REQUEST_PORT":"3244",
        "SYNC_PASSUP_PORT":"3245",
    }
    return config

def get_msg_ids():
    msg_ids = {
        "AUTH":"1", "CREATE_USER":"5", "CHANGE_PASS":"6", "ALL_USERS":"8", "GET_FILES":"9", "REMOVE":"10", "CHANGE_PASS":"11", "LOG":"12",
        "ACK":"2", "TRUE":"3", "FALSE":"4", "NACK":"7",
    }
    return msg_ids

class OneDirServer:
    def __init__(self):
        self.config = get_config()
        self.msg_identifier = get_msg_ids()
        self.controller = ServerController()
        self.controller.configure(self.config)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.listen_flag = threading.Event()
    def initialize(self):
        self.socket.bind("tcp://*:" + self.config["ONEDIRSERVER"])
        self.listen_flag.clear()
    def launch(self):
        self.controller.start()
    def listen(self):
        self.listen_flag.set()
        threading.Thread(target=self._listen_).start()
    def stop(self):
        self.listen_flag.clear()
        self.controller.stop()
    def _listen_(self):
        while self.listen_flag.is_set():
            msg = decode(self.socket.recv_multipart())
            if msg[0] == self.msg_identifier["AUTH"]:
                msg = self._auth_(msg)
            elif msg[0] == self.msg_identifier["CREATE_USER"]:
                msg = self._create_(msg)
            elif msg[0] == self.msg_identifier["CHANGE_PASS"]:
                msg = self._change_(msg)
            elif msg[0] == self.msg_identifier["ALL_USERS"]:
                msg = self._ausers_(msg)
            elif msg[0] == self.msg_identifier["GET_FILES"]:
                msg = self._gfiles_(msg)
            elif msg[0] == self.msg_identifier["REMOVE"]:
                msg = self._remove_(msg)
            elif msg[0] == self.msg_identifier["CHANGE_T_PASS"]:
                msg = self._tchange_(msg)
            elif msg[0] == self.msg_identifier["LOG"]:
                msg = self._log_(msg)
            self.socket.send_multipart(encode(msg))
    def _auth_(self, msg):
        if self.__auth__(msg[1], msg[2]):
            return [self.msg_identifier["ACK"], self.msg_identifier["TRUE"]]
        else:
            return [self.msg_identifier["ACK"], self.msg_identifier["FALSE"]]
    def _create_(self, msg):
        User.objects.create_user(msg[1],msg[3],msg[2])
        user_dir = self.config["PATH_BASE"] + msg[1] + SLASH + "OneDir" + SLASH
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        return [self.msg_identifier["ACK"], self.msg_identifier["TRUE"]]
    def _change_(self, msg):
        if not self.__auth__(msg[1], msg[2]):
            return [self.msg_identifier["ACK"], self.msg_identifier["FALSE"]]
        else:
            user = User.objects.get(username__exact = msg[1])
            user.set_password(msg[3])
            user.save()
            return [self.msg_identifier["ACK"], self.msg_identifier["TRUE"]]
    def _ausers_(self, msg):
        if not self.__auth__(msg[1], msg[2]):
            return [self.msg_identifier["NACK"], "USER"]
        if not self.__is_admin__(msg[1]):
            return [self.msg_identifier["NACK"], "PRIV"]
        msg = [self.msg_identifier["ACK"]]
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM auth_user")
        row = cursor.fetchall()
        for entries in row:
            msg.append(str(entries))
        return msg
    def _gfiles_(self, msg):
        if not self.__auth__(msg[1], msg[2]):
            return [self.msg_identifier["NACK"], "USER"]
        if not self.__is_admin__(msg[1]):
            return [self.msg_identifier["NACK"], "PRIV"]
        user_dir = self.config["PATH_BASE"] + msg[3] + SLASH + "OneDir" + SLASH
        info = self.__enum_files__(user_dir)
        rep = [self.msg_identifier["ACK"], str(info[0])]
        for pair in info[1:]:
            rep.append(pair)
        print(str(rep))
        return rep
    def _remove_(self, msg):
        if not self.__auth__(msg[1], msg[2]):
            return [self.msg_identifier["NACK"], "USER"]
        if not self.__is_admin__(msg[1]):
            return [self.msg_identifier["NACK"], "PRIV"]
        dUser = User.objects.get(username__exact = msg[3])
        dUser.delete()
        print(msg)
        if(msg[4] == "YES"):
            user_dir = self.config["PATH_BASE"] + msg[3] + SLASH
            if os.path.exists(user_dir):
                rmtree(user_dir)
        msg = [self.msg_identifier["ACK"]]
        return msg
    def _tchange_(self, msg):
        if not self.__auth__(msg[1], msg[2]):
            return [self.msg_identifier["NACK"], "USER"]
        if not self.__is_admin__(msg[1]):
            return [self.msg_identifier["NACK"], "PRIV"]
        user = User.objects.get(username__exact = msg[3])
        user.set_password(msg[4])
        user.save()
        msg = [self.msg_identifier["ACK"]]
        return msg
    def _log_(self, msg):
        if not self.__auth__(msg[1], msg[2]):
            return [self.msg_identifier["NACK"], "USER"]
        if not self.__is_admin__(msg[1]):
            return [self.msg_identifier["NACK"], "PRIV"]
        with open("s_controller.log", "r") as logfile:
            msg = [self.msg_identifier["ACK"], logfile.read()]
        return msg
    def __enum_files__(self, top):
        res = [0]
        for parent, sub_dirs, files in os.walk(top):
            #Synchronize all files
            for user_file in files:
                res[0] += 1
                apath = os.path.join(parent, user_file)
                res.append((str(apath) + "$$" + str(os.path.getsize(apath))))
            #Recurse into sub-directories
            for sub_dir in sub_dirs:
                rec = self.__enum_files__((parent+sub_dir))
                res[0] += rec[0]
                for pair in rec[1:]:
                    if pair != "":
                        res.append(pair)
        return res
    def __auth__(self, uname, pword):
        user = authenticate(username=uname, password=pword)
        if user is not None:
            if user.is_active:
                return True
            else:
                return False
        else:
            return False
    def __is_admin__(self, uname):
        user = User.objects.get(username__exact = uname)
        return user.is_superuser

def setup_django():
    get_config()

if __name__ == "__main__":
    user = User.objects.get(username__exact = "test1")
    user.set_password("test1")
    user.save()
    server = OneDirServer()
    server.initialize()
    server.listen()
    server.launch()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()

