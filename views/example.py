# -*- coding: utf-8 -*-
# @Time    : 2021/6/22 11:52
# @Author  : ShaoJK
# @File    : example.py
# @Remark  :
import json

from flask import Blueprint, request
from sqlalchemy import func

import utils
from module import Test, db, Record, Task, Tag
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
def listRecord(id):
    records = Record.query.join(Task, Record.task_id == Task.id).filter(Record.test_id==id).order_by(db.desc(Record.start_time)).limit(50)
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
    tag = request.args.get('tag') if request.args.get('tag') else None
    filter = Test.testname.ilike(f'%{testname}%')
    if modules:
        filter &= Test.module.in_(modules)
    if creator:
        filter &= Test.creator.in_(creator)
    if status:
        filter &= Test.status.in_(status)
    if tag and tag != 'All':
        filter &= Test.tag_id == int(tag)
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
    counter = {}
    for tag in Tag.query.all():
        tests = Test.query.with_entities(Test.status, func.count(Test.id)).filter_by(tag_id=tag.id).group_by(Test.status).order_by(Test.status).all()
        counter[tag.name] = dict([tuple(test) for test in tests])
    return wrap_response(counter)

@example.route('/record', methods=['POST'])
def recordExample():
    """给用例报告当前执行状态"""
    report = get_post_form()
    info = {'status': report.status}
    if 'start_time' in report:
        info['execute_time'] = report.start_time
    elif 'elapse_time' in report:
        info['elapse_time'] = report.elapse_time
    Test.query.filter_by(id=report.test_id).update(info)
    info = report.forUpdate(*filter(lambda k: 'id' not in k, report.keys()))
    Record.query.filter_by(id=report.record_id).update(info)
    return wrap_response()