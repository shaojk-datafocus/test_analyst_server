# -*- coding: utf-8 -*-
# @Time    : 2021/6/22 11:52
# @Author  : ShaoJK
# @File    : example.py
# @Remark  :
import json

from flask import Blueprint, request, copy_current_request_context
from flask_apscheduler import APScheduler
from sqlalchemy import func

from module import Tag, db
from utils import get_post_form, wrap_response

tag = Blueprint('tag',__name__,url_prefix="/tag")
scheduler = APScheduler()

@tag.route('/<int:id>')
def detailTag(id):
    tag = Tag.query.filter_by(id=id).first()
    if tag:
        tag = tag.toJson()
        lastTag = tag.last_tag = Tag.query.filter_by(next_tag=id).with_entities(Tag.id).first()
        if lastTag: tag.last_tag = lastTag[0]
        return wrap_response(tag)
    else:
        return wrap_response(errCode=10137,exception="任务不存在")

@tag.route('/list')
def listTag():
    return wrap_response([t.toJson() for t in Tag.query.all()])

@tag.route('/add',methods=['POST'])
def createTag():
    tag = get_post_form()
    db.session.add(tag)
    return wrap_response(tag.toJson())

@tag.route('/update',methods=['POST'])
def updateTag():
    tag = get_post_form()
    if tag.worker_id:
        if scheduler.get_job(str(tag.id)):
            scheduler.remove_job(str(tag.id))
        if tag.schedule:
            schedule = json.loads(tag.schedule)
            if 'trigger' not in schedule.keys():
                schedule['trigger'] = 'cron'
            job = scheduler.add_job(func=copy_current_request_context(executeTag), id=str(tag.id), args=formulateTag(tag), replace_existing=True, **schedule)
            print("下一次执行时间",job.next_run_time)
            tag.schedule_status = True
    if type(tag.content) == list:
        tag.content = ",".join([str(i) for i in tag.content])
    Tag.query.filter_by(id=tag.id).update(tag.forUpdate('tagname', 'description', 'creator', 'host', 'content', 'worker_id', 'schedule', 'next_tag','branch','sql_strategy'))
    return json.dumps({"data": None, "errCode": 0, "exception": "", "success": True})

@tag.route('/delete/<int:id>',methods=['POST'])
def deleteTag(id):
    if scheduler.get_job(str(tag)):
        scheduler.remove_job(str(id))
    Tag.query.filter_by(id=id).delete()
    return wrap_response()