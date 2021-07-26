# -*- coding: utf-8 -*-
# @Time    : 2021/6/23 11:38
# @Author  : ShaoJK
# @File    : CIMaster.py
# @Remark  :
import json
import socket

# from config import CIWORKER_PORT
from queue import Queue

CIWORKER_PORT = 8378

class CIMaster():
    def __init__(self):
        self.workers = dict()
        self.worker = None
        self.queue = Queue(maxsize=10)

    def connect(self,addr,port=CIWORKER_PORT):
        addr = (addr, port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((addr))
        print("CIMaster connected to <Worker %s:%d>" % (addr[0], addr[1]))
        self.workers["%s:%d"%(addr[0],addr[1])] = s
        self.worker = s

    def send(self,data:dict):
        self.worker.sendall(json.dumps(data).encode('utf-8'))

    def recv(self,**expect) -> dict:
        found = False
        while not found:
            self._recv()
            while not self.queue.empty():
                res = self.queue.get()
                res_kv = list(map(lambda item: item[0]+str(item[1]),res.items()))
                found = sum(list(map(lambda item: 0 if item[0]+str(item[1]) in res_kv else 1, expect.items()))) == 0
        return res

    def _recv(self,timeout=10) -> dict:
        self.worker.settimeout(timeout)
        info = self.worker.recv(1024)
        info = info.decode('utf-8')
        print("Receive: ",info)
        for info in info.split('\n'):
            if not self.queue.full() and info:
                self.queue.put(json.loads(info))

    def assign(self,addr,port):
        """指定当前默认发送给的worker"""
        self.worker = self.workers["%s:%d"%(addr,port)]

    def close(self,addr,port=CIWORKER_PORT):
        self.workers["%s:%d"%(addr,port)].close()
        print("Disconnected <Worker %s:%d>"%(addr,port))

    def __del__(self):
        if getattr(self,"workers"):
            for addr,s in self.workers.items():
                s.close()
                print("Disconnected <Worker %s>" % addr)

    def start_test(self,plan,folder=""):
        data = {"command": "run", "args": [{"plan": plan, "folder":folder}], "kwargs": {}}
        master.send(data)
        master.recv(command="run",response="start running")


master = CIMaster()


if __name__ == '__main__':
    import time
    master.connect("192.168.0.91",8378)
    data = {"command":"echo","args":[],"kwargs":{}}
    master.send(data)
    master.recv(response="echo")
    time.sleep(3)
