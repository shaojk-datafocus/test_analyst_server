### focust_test manager 启动方法
1. set FLASK_APP=app.py
   python -m flask run
2. python app.py

### Linux环境部署

sudo yum install python3-devel

 sudo yum install postgresql-devel

python3 -m pip install -r requirements.txt

### Worker执行机部署

将CIWorker.py脚本放至执行机任意位置，将CIWorker starter.bat放到windows启动目录中（开机自启），配置bat脚本中的启动参数即可。