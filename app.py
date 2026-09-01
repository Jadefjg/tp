from sanic import Sanic
from sanic.exceptions import NotFound
from sanic import response
import config
from blueprints import init_app as blueprint_init_app
from blueprints.user.views import _login_page
from extentions import init_app as extension_init_app
from middlewares import init_app as middlerware_init_app

import os
os.makedirs('media/casedata', exist_ok=True)
os.makedirs('media/casefile', exist_ok=True)
os.makedirs('media/taskfile/videos', exist_ok=True)

app = Sanic(__name__, load_env=False)
app.update_config(config.Config)

extension_init_app(app)
middlerware_init_app(app)
blueprint_init_app(app)

app.static('/media', './media')
app.static('/static', './static')


@app.route('/', methods=['GET'])
async def index(request):
    return await _login_page()


@app.exception(NotFound)
async def handle_not_found(request, exception):
    path = request.path or '/'
    if request.method.upper() == 'GET':
        if path.startswith('/home') or path.startswith('/dashboard'):
            return response.redirect('/dashboard')
        if path.startswith('/login'):
            return response.redirect('/login')
        if path.startswith('/register'):
            return response.redirect('/register')
        if path == '/':
            return await _login_page()
        return response.html(
            '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>页面不存在</title>
  <style>
    body { margin:0; min-height:100vh; display:grid; place-items:center;
      font-family:"PingFang SC","Microsoft YaHei",sans-serif; background:#0a7e8c; color:#fff; }
    .box { text-align:center; padding:32px; }
    a { display:inline-block; margin-top:16px; padding:10px 18px; border-radius:4px;
      color:#fff; background:#4d9eff; text-decoration:none; font-weight:600; }
    p { color:rgba(255,255,255,.8); }
  </style>
</head>
<body>
  <div class="box">
    <h1>页面不存在</h1>
    <p>请从登录页进入测试平台</p>
    <a href="/login">返回登录</a>
  </div>
</body>
</html>''',
            status=404
        )
    return response.json({
        'code': 40004,
        'message': '未找到该路径',
        'data': None
    }, status=404)


if __name__ == '__main__':
    app.run(
        debug=config.DEBUG,
        host='0.0.0.0',
        port=config.Config.PORT, 
        workers=config.Config.WORKERS
    )
    