from blueprints.user.models import LoginRecord
from sanic import response
from config import Config
from const import ResponseCode, CommonResponse

async def auth(request):
    path = request.path
    if any(path.startswith(item) for item in Config.WHITE_LIST):
        return
    token = request.args.get('token')
    if not token:
        token = request.headers.get('Token', None)
    if not token:
        return response.json(CommonResponse.ILLEGAL_TOKEN, status=200)
    user = await LoginRecord.token2user(token)
    request.ctx.user = user
    request.ctx.token = token
    if user is None:
        return response.json(CommonResponse.ILLEGAL_TOKEN, status=200)