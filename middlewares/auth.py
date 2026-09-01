from blueprints.user.models import LoginRecord
from sanic import response
from const import CommonResponse

PUBLIC_EXACT = {
    '/login',
    '/register',
    '/home',
    '/dashboard',
}

PUBLIC_PREFIXES = (
    '/media',
    '/static',
)

API_PREFIXES = (
    '/api',
    '/user',
    '/upload',
)


def _is_public(request):
    path = request.path or '/'
    method = (request.method or 'GET').upper()
    if path in PUBLIC_EXACT:
        return True
    if any(path == prefix or path.startswith(prefix + '/') for prefix in PUBLIC_PREFIXES):
        return True
    if method == 'GET' and (
        path == '/' or path.startswith('/login') or path.startswith('/register')
        or path.startswith('/home') or path.startswith('/dashboard')
    ):
        return True
    return False


def _is_api_path(path):
    return any(path == prefix or path.startswith(prefix + '/') for prefix in API_PREFIXES)


async def auth(request):
    if _is_public(request):
        return
    token = request.args.get('token')
    if not token:
        token = request.headers.get('Token', None)
    if not token:
        if request.method.upper() == 'GET' and not _is_api_path(request.path or '/'):
            return response.redirect('/login')
        return response.json(CommonResponse.ILLEGAL_TOKEN, status=200)
    user = await LoginRecord.token2user(token)
    request.ctx.user = user
    request.ctx.token = token
    if user is None:
        return response.json(CommonResponse.ILLEGAL_TOKEN, status=200)