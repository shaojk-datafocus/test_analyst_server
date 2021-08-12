# -*- coding: utf-8 -*-
# @Time    : 2021/6/21 16:02
# @Author  : ShaoJK
# @File    : utils.py
# @Remark  :
import json
import time

from flask import make_response as _make_response, jsonify, request


class Dict(dict):
    """用属性的形式使用字典"""
    def __getattr__(self, key):
        if key not in self.keys():
            return None
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value

    def forUpdate(self,*args):
        """返回更新数据的字典，去除对象中的id
            *args: 为属性值，存在则仅返回所给的更新项
        """
        if len(args)>0:
            keys = self.keys()
            return dict([(key,None if self[key] == '' else self[key]) for key in args if key!='id' and key in keys ])
        else:
            return dict([(key,value) for key,value in self.items() if key!='id'])

    def toJson(self):
        return self

def make_response(data):
    """跨域使用"""
    response = _make_response(jsonify(data))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    response.headers['Access-Control-Allow-Headers'] = 'X-Requested-With,Content-Type'
    return response

def wrap_response(data=None,errCode=0, exception="",**kwargs):
    """包装返回的json格式，确保全站统一
        可是输入额外的键值对，改键值对讲附加在response信息中
    """
    return json.dumps({"data": data, "errCode": errCode, "exception": exception, "success": errCode==0, **kwargs})

def get_post_form() -> Dict:
    req = request.data.decode('utf-8')
    if req:
        return Dict(json.loads(req))
    return Dict()

def get_current_time() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def timestamp_to_str(t) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))

def str_to_timestamp(s,pattern="%Y-%m-%d %H:%M:%S") -> float:
    return time.strptime(s, pattern)
