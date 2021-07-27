# -*- coding: utf-8 -*-
# @Time    : 2021/6/25 14:42
# @Author  : ShaoJK
# @File    : system.py
# @Remark  :
from datetime import timedelta

from flask import Blueprint, request
from sqlalchemy import Time, cast

from ci import master
from module import Worker, db, Record
from utils import wrap_response, get_post_form, timestamp_to_str

system = Blueprint('system', __name__, url_prefix="/system")

def initWorkers():
    """服务启动的时候需要尝试连接所有worker"""
    for worker in Worker.query.all():
        Worker.query.filter_by(id=worker.id).update({"status": connectWorker(worker.ip,worker.port)})

def connectWorker(addr,port):
    try:
        master.connect(addr,port)
        return True
    except Exception as e:
        print(e)
        return False

@system.route('/worker/list')
def listWorker():
    name = request.args.get('name')
    if name:
        return wrap_response([worker.toJson() for worker in Worker.query.filter(Worker.name.ilike(f'%{name}%')).order_by(db.desc(Worker.status)).all()])
    return wrap_response([worker.toJson() for worker in Worker.query.order_by(db.desc(Worker.status)).all()])

@system.route('/worker/add', methods=['POST'])
def addWorker():
    worker = Worker(**get_post_form())
    db.session.add(worker)
    db.session.flush()
    return wrap_response(worker.toJson())

@system.route('/worker/update', methods=['POST'])
def updateWorker():
    worker = get_post_form()
    Worker.query.filter_by(id=worker.id).update(worker.forUpdate())
    return wrap_response()

@system.route('/worker/delete/<int:id>', methods=['POST'])
def deleteWorker(id):
    Worker.query.filter_by(id=id).delete()
    return wrap_response()

@system.route('/worker/connect', methods=['POST'])
def loginWorker():
    worker = get_post_form()
    print(worker)
    worker = Worker.query.filter_by(ip=worker.ip,port=worker.port).first()
    if worker:
        if connectWorker(worker.ip,worker.port):
            Worker.query.filter_by(id=worker.id).update({"status": True})
            return wrap_response()
        else:
            Worker.query.filter_by(id=worker.id).update({"status": False})
            return wrap_response(errCode=10061,exception="无法连接到Worker")
    else:
        return wrap_response(errCode=10261,exception="Worker未登记")

@system.route('/record/clean', methods=['POST'])
def cleanRecord():
    form = get_post_form()
    deleteTime = form.deleteTime.split('.')[0]
    Record.query.filter(Record.start_time <= deleteTime).delete()
    return wrap_response()