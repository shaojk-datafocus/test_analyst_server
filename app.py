# encoding=utf-8
import json
from datetime import datetime

from flask import Flask, request, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

from module import db, Test, Record, Task
from views import example, task, system
from views.system import initWorkers
from views.task import scheduler, initSchedules

app = Flask(__name__)
# app.wsgi_app = ProxyFix(app.wsgi_app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@192.168.0.93:5432/focustest'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True # 自动commit
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# app.config['SQLALCHEMY_ECHO'] = True
db.init_app(app)
scheduler.init_app(app)
scheduler.start()

app.register_blueprint(example)
app.register_blueprint(task)
app.register_blueprint(system)
with app.app_context(): # 在本地debug不连接worker和启动定时任务
    initWorkers()
    initSchedules(app)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/record/list')
def listRecord():
    records = [record.toJson() for record in Record.query.all()]
    return json.dumps({"data": records, "errCode": 0, "success": True})


if __name__ == '__main__':
    app.run()