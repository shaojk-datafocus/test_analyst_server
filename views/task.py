# -*- coding: utf-8 -*-
# @Time    : 2021/6/22 11:52
# @Author  : ShaoJK
# @File    : example.py
# @Remark  :
import json
import re
import time

from flask import Blueprint, request, copy_current_request_context
from flask_apscheduler import APScheduler
from sqlalchemy import func

from ci.CIMaster import master
from module import Task, db, Test, Record, Worker
from utils import get_post_form, get_current_time, wrap_response, timestamp_to_str

task = Blueprint('task',__name__,url_prefix="/task")
scheduler = APScheduler()

@task.route('/<int:id>')
def detailTask(id):
    task = Task.query.filter_by(id=id).first()
    if task:
        task = task.toJson()
        lastTask = task.last_task = Task.query.filter_by(next_task=id).with_entities(Task.id).first()
        if lastTask: task.last_task = lastTask[0]
        return wrap_response(task)
    else:
        return wrap_response(errCode=10137,exception="任务不存在")

@task.route('/list')
def listTask():
    page = int(request.args.get('page'))
    pageSize = int(request.args.get('pageSize'))
    taskname = request.args.get('taskname')
    filter = Task.taskname.ilike(f'%{taskname}%')
    return wrap_response({
        "datas": [task.toJson() for task in Task.query.filter(filter).order_by(db.desc(Task.execute_time)).offset((page - 1) * pageSize).limit(pageSize).all()],
        "total": db.session.query(func.count(Task.id)).filter(filter).scalar()
    })

@task.route('/add',methods=['POST'])
def addTask():
    task = get_post_form()
    task = createTask(task)
    return wrap_response(task.toJson())

@task.route('/update',methods=['POST'])
def updateTask():
    task = get_post_form()
    if task.worker_id:
        if task.schedule:
            schedule = json.loads(task.schedule)
            if scheduler.get_job(str(task.id)):
                scheduler.remove_job(str(task.id))
            job = scheduler.add_job(func=copy_current_request_context(executeTask), id=str(task.id), args=formulateTask(task), trigger='cron', replace_existing=True, **schedule)
            print("下一次执行时间",job.next_run_time)
            task.schedule_status = True
    if type(task.content) == list:
        task.content = ",".join([str(i) for i in task.content])
    Task.query.filter_by(id=task.id).update(task.forUpdate('taskname', 'description', 'creator', 'host', 'content', 'worker_id', 'schedule', 'next_task','branch'))
    return json.dumps({"data": None, "errCode": 0, "exception": "", "success": True})

@task.route('/switch/<int:id>',methods=['POST'])
def switchTask(id):
    task = Task.query.filter_by(id=id)
    if task.schedule_status: # 开→关
        scheduler.remove_job(str(task.id))
        Task.query.filter_by(id=task.id).update({"schedule_status":False})
        return wrap_response(True)
    elif task.schedule: # 关→开
        schedule = json.loads(task.schedule)
        scheduler.add_job(func=copy_current_request_context(executeTask), id=str(task.id), args=formulateTask(task), trigger='cron', replace_existing=True, **schedule)
        Task.query.filter_by(id=task.id).update({"schedule_status":True})
        return wrap_response(True)
    else: #关→开 fail
        return wrap_response(False)

@task.route('/delete',methods=['POST'])
def deleteTasksByBatch():
    tasks = get_post_form()["tasks"]
    for task in tasks:
        if scheduler.get_job(str(task)):
            scheduler.remove_job(str(task))
    Task.query.filter(Task.id.in_(tasks)).delete(synchronize_session=False)
    return wrap_response()

@task.route('/delete/<int:id>',methods=['POST'])
def deleteTask(id):
    if scheduler.get_job(str(task)):
        scheduler.remove_job(str(id))
    Task.query.filter_by(id=id).delete()
    return wrap_response()

@task.route('/trigger',methods=['POST'])
def triggerTemplateTask():
    task = get_post_form()
    if task.worker_id:
        worker = Worker.query.filter_by(id=task.worker_id).first()
    else:
        worker = Worker.query.filter_by(status=True).first() # TODO 这里以后需要，根据worker的工作量进行负载均衡
    del task["worker"]
    task.taskname = "临时任务_%s"%(time.strftime("%Y%m%d%H%M%S",time.localtime()))
    task = createTask(task)
    if executeTask(*formulateTask(task,worker)):
        return wrap_response(task.toJson())
    else:
        return wrap_response(task.toJson(),errCode=10506,exception="执行任务失败")

@task.route('/trigger/<int:id>',methods=['POST'])
def triggerTask(id):
    task = Task.query.filter_by(id=id).first()
    if task.worker_id:
        worker = Worker.query.filter_by(id=task.worker_id).first()
    else:
        worker = Worker.query.filter_by(status=True).first()
    if executeTask(*formulateTask(task,worker)):
        return wrap_response(task.toJson())
    else:
        return wrap_response(task.toJson(),errCode=10506,exception="执行任务失败")

    return wrap_response(task.toJson())


@task.route('/<int:id>/report',methods=['POST'])
def reportTask(id):
    result = get_post_form()
    task = Task.query.filter_by(id=id).first()
    Task.query.filter_by(id=task.id).update({"elapse_time":result.elapse_time,"execute_time":timestamp_to_str(result.execute_time)})
    if task.next_task:
        triggerTask(task.next_task)
    return wrap_response()

def createTask(task=None)->Task:
    if not task:
        task = get_post_form()
    if type(task.content) == list:
        task.content = ",".join(map(lambda x: str(x),task.content))
    task = Task(**task)
    db.session.add(task)
    db.session.flush()
    return task

def formulateTask(task,worker=None):
    if not worker:
        worker = Worker.query.filter_by(id=task.worker_id).first()
    return worker.toJson(), task.toJson()

def executeTask(worker, task):
    """执行测试任务"""
    print("执行测试任务", task.taskname)
    master.assign(worker["ip"],worker["port"])
    tests = dict()
    contents = task.content if type(task.content) == list else task.content.split(",")
    host = re.findall("^https?://([\w.:]+)", task.host)
    for test in Test.query.filter(Test.id.in_(contents)).all():
        # 创建用例执行记录
        record = Record(status="pending",start_time=get_current_time(),task_id=task.id,test_id=test.id,branch=task.branch,host=host)
        db.session.add(record)
        db.session.flush()
        Test.query.filter_by(id=test.id).update({"status": "pending"})
        # 需要把同一个module的function规整到一起
        if tests.get(test.module, None):
            tests[test.module].append({"func":test.function,"record_id":record.id,"id":test.id})
        else:
            tests[test.module] = [{"func":test.function,"record_id":record.id,"id":test.id}]
    plan = json.dumps([{'module': key, 'tests': value} for key, value in tests.items()])

    Task.query.filter_by(id=task.id).update({"execute_time":timestamp_to_str(time.time())})
    try:
        master.send({"command":"run","args":[plan,task.id,task.host,json.loads(worker.branch)[task.branch]],"kwargs":{}})
        res = master.recv(command="run",response="start running")
    except Exception as e:
        print(e)
        return False
    return res["errCode"] == 0

def initSchedules(app):
    """webserver启动的时候，给所有已有的任务添加定时任务"""
    for task in Task.query.filter(Task.schedule.isnot(None)).all():
        schedule = json.loads(task.schedule)
        try:
            def wrapper(*args, **kwargs):
                with app.app_context():
                    return executeTask(*args, **kwargs)
            scheduler.add_job(func=wrapper, id=str(task.id), args=formulateTask(task), trigger='cron',
                              replace_existing=True, **schedule)
            print("添加定时任务<%s>"%task.taskname)
        except Exception as e:
            print(e)
