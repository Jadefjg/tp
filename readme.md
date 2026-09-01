# 简介
本项目为一个python开发的自动化测试平台，目前已实现接口自动化测试，定时任务等功能，项目需要python3.8+

# 部署
1. 安装redis服务， 参考官方网站：https://redis.io/， linux系统可以直接通过包管理器安装
```
    apt/yum install redis-server
```
2. 克隆项目，进入目录
3. 推荐使用虚拟环境管理依赖，如果不想使用虚拟环境可以跳过，执行
```
    python -m venv env
    source env/bin/activate  # linux
    env/bin/activate.bat   # windows
```
4. 安装依赖
```
    python -m pip install -r requirements.txt
```
5. 配置项目。系统的整个配置在config.py文件，开发状态下是`DEBUG=True`, 该状态下，会同步初始调试数据，修改代码会自动重启服务，并且会重新刷新数据（debug模式下,使用内存下的sqlite，配置的workers不要超过1,否则每个实例的数据会不一致。）
6. 启动项目
```
    python app.py
```
7. 生产部署。 推荐使用nginx反代，`api/login/user/media`开头的路径需要代理，另外`media`开头的路径也可以直接由nginx来处理静态文件。
# TODO
1. YAPI接口管理同步 (Done)
2. 用例的数据驱动 (Done)
3. UI自动化
4. 系统的配置（LOW PRIORITY）
5. ...