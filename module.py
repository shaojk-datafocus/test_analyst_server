from flask_sqlalchemy import SQLAlchemy

from utils import Dict

db = SQLAlchemy()

class Task(db.Model):
    # 定义表名
    __tablename__ = 'focus_task'
    # 定义列对象
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    taskname = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(256))
    creator = db.Column(db.String(256))
    host = db.Column(db.String(256))
    content = db.Column(db.String())
    execute_time = db.Column(db.TIMESTAMP)
    worker_id = db.Column(db.Integer, db.ForeignKey('focus_worker.id'))
    schedule = db.Column(db.String(256))
    sql_strategy = db.Column(db.String(256))
    branch = db.Column(db.String(64)) # tenantrelease: No.0 depot
    schedule_status = db.Column(db.Boolean, default=False)
    next_task = db.Column(db.Integer, db.ForeignKey('focus_task.id'))
    elapse_time = db.Column(db.Float)
    record = db.relationship('Record', backref='task', lazy='joined')

    def __repr__(self):
        return '<Task %s>' % self.taskname

    def keys(self):
        return ('id', 'taskname', 'description', 'creator', 'host', 'content','execute_time','worker_id','schedule', 'sql_strategy', 'schedule_status', 'next_task', 'elapse_time', 'branch')

    def __getitem__(self, item):
        return getattr(self, item)

    def toJson(self):
        d = Dict(self)
        d["execute_time"] = str(d["execute_time"])
        return d

class Test(db.Model):
    __tablename__ = 'focus_test'
    id = db.Column(db.Integer, primary_key=True)
    testname = db.Column(db.String(64), unique=True)
    module = db.Column(db.String(64), nullable=False)
    function = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(256))
    creator = db.Column(db.String(256))
    elapse_time = db.Column(db.Float)
    stability = db.Column(db.Integer)
    status = db.Column(db.String(16))
    execute_time = db.Column(db.TIMESTAMP)
    last_record = db.relationship('Record', backref='test', lazy='dynamic')

    def __repr__(self):
        return '<Test %s>' % self.testname

    def keys(self):
        return ('id', 'testname', 'module', 'function', 'description', 'creator', 'elapse_time', 'stability','status', 'execute_time')

    def __getitem__(self, item):
        return getattr(self, item)

    def toJson(self):
        d = Dict(self)
        d["execute_time"] = str(d["execute_time"])
        return d


class Record(db.Model):
    __tablename__ = 'focus_record'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    status = db.Column(db.String(16))
    start_time = db.Column(db.TIMESTAMP)
    elapse_time = db.Column(db.Float)
    end_time = db.Column(db.TIMESTAMP)
    info = db.Column(db.String())
    task_id = db.Column(db.Integer, db.ForeignKey('focus_task.id'))
    test_id = db.Column(db.Integer, db.ForeignKey('focus_test.id'))
    host = db.Column(db.String(64))
    branch = db.Column(db.String(32))

    def __repr__(self):
        return '<Record %s>' % self.id

    def keys(self):
        return ('id', 'status', 'start_time', 'elapse_time', 'end_time', 'info', 'task_id', 'test_id', 'host', 'branch')

    def __getitem__(self, item):
        return getattr(self, item)

    def toJson(self):
        d = Dict(self)
        d.start_time = str(d.start_time)
        d.end_time = str(d.end_time)
        return d

class Worker(db.Model):
    __tablename__ = 'focus_worker'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip = db.Column(db.String(16))
    port = db.Column(db.Integer)
    status = db.Column(db.Boolean)
    name = db.Column(db.String(255))
    branch = db.Column(db.String(255)) # { "tenantrelease": "No.0 depot", "hwsecurity": "No.0 depot_security" }

    def __repr__(self):
        return '<Worker %s>' % self.id

    def keys(self):
        return ('id', 'ip', 'port', 'status', 'name', 'branch')

    def __getitem__(self, item):
        return getattr(self, item)

    def toJson(self):
        return Dict(self)

