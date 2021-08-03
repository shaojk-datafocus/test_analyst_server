# -*- coding: utf-8 -*-
# @Time    : 2021/6/22 11:52
# @Author  : ShaoJK
# @File    : example.py
# @Remark  :
import json
import math

from flask import Blueprint, request
from sqlalchemy import func

import utils
from module import Test, db, Record, Task
from utils import get_post_form, wrap_response

example = Blueprint('example',__name__,url_prefix="/example")

@example.route('/<int:id>')
def detailExample(id):
    test = Test.query.filter_by(id=id).first()
    if test:
        return wrap_response(test.toJson())
    else:
        return wrap_response(errCode=10137,exception="用例不存在")

@example.route('/<int:id>/record')
def recordExample(id):
    records = Record.query.join(Task, Record.task_id == Task.id).filter(Record.test_id==id).order_by(db.desc(Record.start_time)).limit(20)
    datas = []
    for record in records:
        item = record.toJson()
        item["task_name"] = record.task.taskname if record.task else " - "
        datas.append(item)
    return wrap_response(datas)

@example.route('/list')
def listExample():
    page = int(request.args.get('page'))
    pageSize = int(request.args.get('pageSize'))
    testname = request.args.get('testname')
    modules = request.args.get('modules').split(',') if request.args.get('modules') else None
    creator = request.args.get('creator').split(',') if request.args.get('creator') else None
    status = request.args.get('status').split(',') if request.args.get('status') else None
    filter = Test.testname.ilike(f'%{testname}%')
    if modules:
        filter &= Test.module.in_(modules)
    if creator:
        filter &= Test.creator.in_(creator)
    if status:
        filter &= Test.status.in_(status)
    res = {
        "datas": [test.toJson() for test in Test.query.filter(filter).order_by(db.desc(Test.execute_time)).offset((page - 1) * pageSize).limit(pageSize).all()],
        "total": db.session.query(func.count(Test.id)).filter(filter).scalar()
    }
    return wrap_response(res)

@example.route('/options')
def options():
    """获取搜索条件的列中值"""
    res = {"module":[item[0] for item in Test.query.with_entities(Test.module).distinct().all()],
           "creator":[item[0] for item in Test.query.with_entities(Test.creator).distinct().all()]}
    return wrap_response(res)

@example.route('/add',methods=['POST'])
def addExample():
    test = Test(**get_post_form())
    test.execute_time = utils.get_current_time()
    db.session.add(test)
    return json.dumps({"data": None, "errCode": 0, "exception": "", "success": True})

@example.route('/update',methods=['POST'])
def updateExample():
    test = get_post_form()
    result = Test.query.filter_by(id=test.id).update(test.forUpdate())
    print("updateExample result", result)
    return json.dumps({"data": None, "errCode": 0, "exception": "", "success": True})

@example.route('/delete/<int:id>',methods=['POST'])
def deleteExample(id):
    Test.query.filter_by(id=id).delete()
    return json.dumps({"data": None, "errCode": 0, "exception": "", "success": True})

@example.route('/delete',methods=['POST'])
def deleteExamplesByBatch():
    tasks = get_post_form()["tasks"]
    Test.query.filter(Test.id.in_(tasks)).delete(synchronize_session=False)
    return wrap_response()

@example.route('/report')
def reportExample():
    result = Test.query.with_entities(Test.status, func.count(Test.id)).group_by(Test.status).order_by(Test.status).all()
    return wrap_response([[row[0],row[1]] for row in result]) # 这么写是为了适配linux
