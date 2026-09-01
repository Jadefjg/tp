# 简介
本项目为一个python开发的自动化测试平台，目前已实现接口自动化测试，定时任务等功能，项目需要python3.8+

# Docker 部署（推荐）

依赖 Docker 与 Docker Compose。将同时启动 MySQL、Redis 和应用服务。

```bash
cp .env.example .env   # 可选，按需修改管理员账号、端口、数据库密码
docker compose up -d --build
```

启动后访问 `http://localhost:18081`。默认管理员：

- 用户名：`admin`
- 密码：`admin123`（请在 `.env` 中修改 `TP_ADMIN_PASSWORD`）

宿主机端口默认 `18081`，避免与本机已占用的 `8081` 冲突；可在 `.env` 中修改 `TP_PORT`。

常用命令：

```bash
docker compose ps
docker compose logs -f app
docker compose down          # 停止容器，保留数据卷
docker compose down -v       # 停止并删除数据（MySQL / Redis / 上传文件）
```

数据卷：

- `mysql_data`：数据库
- `redis_data`：任务队列与调度
- `media_data`：用例附件等上传文件

生产环境建议用 Nginx 反代 `/api`、`/login`、`/user`、`/media`；`media` 也可以直接由 Nginx 提供静态文件。钉钉报告链接中的前端地址通过 `TP_HOST` 配置。

# 本地部署
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
5. 配置项目。系统的整个配置在config.py文件，开发状态下是`DEBUG=True`（也可用环境变量 `TP_DEBUG` 控制）。该状态下会同步初始调试数据，修改代码会自动重启服务。debug 模式下 workers 不要超过 1。
6. 启动项目
```
    python app.py
```
7. 生产部署。推荐使用nginx反代，`api/login/user/media`开头的路径需要代理，另外`media`开头的路径也可以直接由nginx来处理静态文件。数据库、Redis 地址可通过 `MYSQL_HOST`、`REDIS_URL` 等环境变量覆盖，不必改代码。
# TODO
1. YAPI接口管理同步 (Done)
2. 用例的数据驱动 (Done)
3. UI自动化
4. 系统的配置（LOW PRIORITY）
5. ...
