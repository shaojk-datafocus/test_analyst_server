# -*- coding: utf-8 -*-
# @Time    : 2021/6/23 11:38
# @Author  : ShaoJK
# @File    : CIWorker.py
# @Remark  :
import json
import os
import socket
import threading
import time
from optparse import OptionParser

import requests


def wrap_response(command, response, errCode, **kwargs):
    return {"command": command, "response": response, "errCode": errCode, **kwargs}

class CIWorker():
    def __init__(self,connect,addr, master_url, root="", username="Jenkins Tester", compat2=True):
        """
        客户端worker
        :param connect: Master socket连接
        :param addr: Master所在地址
        :param master_url: Master服务器url
        :param root: 代码路径
        :param compat2: 环境中是否存在python 2
        """
        self.connect = connect
        self.addr = addr
        self.root = os.path.join(os.getcwd(),root).replace("/","\\")
        print("Start a worker assigned by %s:%d, and execute code folder at %s"%(*addr,self.root))
        self.quit = False
        self.python = "py -3" if compat2 else "python"
        self.username = username
        self.master_url = master_url
        self.master = requests.Session()
        self.working()

    def post(self, url,**kwargs):
        print("POST: "+self.master_url+url)
        self.master.post(self.master_url+url,**kwargs)

    def working(self):
        while not self.quit:
            info = self.recv()
            if info:
                print(info)
                thread = threading.Thread(target=getattr(self, info["command"]),args=info["args"],kwargs=info["kwargs"],daemon=True)
                thread.start()

    def send(self,data:dict):
        print("Send: ",data)
        self.connect.sendall((json.dumps(data)+'\n').encode('utf-8'))

    def recv(self) -> dict:
        try:
            data = self.connect.recv(65536)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(e)
            self.stop()

    def checkout(self,branch):
        print("切换分支")
        errCode = 0
        errCode += os.system(f'cd {self.root} && git reset --hard')
        errCode += os.system(f'cd {self.root} && git checkout %s' % branch)
        self.send({"response": "finished", "errCode": errCode, "command": "checkout"})

    def pull(self,branch):
        """拉取最新代码"""
        print("从github拉取代码")
        errCode = 0
        errCode += os.system(f'cd {self.root} && git reset --hard')
        errCode += os.system(f'cd {self.root} && git pull origin %s'%branch)
        self.send({"response": "finished", "errCode": errCode, "command": "pull"})

    def run(self,content,task_id,host,path=""):
        """开始执行测试任务"""
        print("开始执行测试用例",content)
        root = os.path.join(self.root,path) if path else self.root
        plan = os.path.join(root,"plan")
        if os.path.exists(plan):  # 清理旧执行计划
            for path, _, files in os.walk(plan):
                for file_tmp in files:
                    os.remove(os.path.join(path, file_tmp))
        else:
            os.mkdir(plan)
        task_plan = os.path.join(plan,"task_plan_%s.json"%(time.strftime("%Y%m%d%H%M%S",time.localtime())))
        with open(task_plan,"w") as f:
            f.write(content)
        self.send({"response": "start running", "errCode": 0, "command": "run"})
        print(f'cd {root} && {self.python} entry-free.py --host "{host}" -u "{self.username}" --plan "{task_plan}" -o "{root}"')
        start_time = time.time()
        errCode = os.system(f'cd {root} && {self.python} entry-free.py --host "{host}" -u "{self.username}" --plan "{task_plan}" -o "{root}"')
        elapse_time = time.time() - start_time
        self.send(wrap_response("run","finished",errCode))
        res = self.post("/api/task/%d/report"%task_id,json={"elapse_time":elapse_time, "execute_time": start_time})
        print(res)
        print("测试用例执行完成")

    def stop(self):
        self.close()
        self.quit = True

    def echo(self):
        print("echo")
        self.send({"response":"echo","errCode":0})

    def close(self):
        self.connect.close()

    def __del__(self):
        self.close()
        print("Dismiss a worker assigned by %s:%d"%addr)

def assign_worker(c,addr,root,master_url,username,compat2):
    CIWorker(c,addr,root,master_url,username,compat2)

if __name__ == '__main__':
    # Worker配置
    parse = OptionParser()
    parse.add_option("-r", "--root", dest="root", default="", action="store",
                     help="test code fold path")
    parse.add_option("-p", "--port", dest="port", default=8378, action="store",
                     help="connect port")
    parse.add_option("-u", "--username", dest="username", default="Jenkins Tester", action="store",
                     help="username")
    parse.add_option("-c", "--compat2", dest="compat2", default=False, action="store_true",
                     help="compat python 2")
    parse.add_option("--host", "--host", dest="host", default="http://localhost:8080", action="store",
                     help="set server address")
    option, args = parse.parse_args()

    port = option.port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", port))
        s.listen()
        print("Workstation started, listening port %d" % port)
        ip = next(filter(lambda ip: ip[:10]=="192.168.0.", socket.gethostbyname_ex(socket.gethostname())[-1]))
        print(option.host+"/api/system/worker/connect")
        try:
            res = requests.post(option.host+"/api/system/worker/connect", json={"ip": ip,"port":port})
            print("与服务器主动连接：",res.text)
        except:
            print("服务器连接失败，唤醒失败")
        while True:
            c, addr = s.accept()
            t = threading.Thread(target=assign_worker,args=(c,addr,option.host,option.root,option.username,option.compat2),daemon=True)
            t.start()
