from sanic.response import HTTPResponse
from sanic.request import Request

def cors_middle_req(request: Request):
    if request.method.lower() == 'options':
        allow_headers = [
            'Token',
            'content-type'
        ]
        headers = {
            'Access-Control-Allow-Methods': '*',
                #', '.join(request.app.router.get_supported_methods(request.path)),
            'Access-Control-Max-Age': '86400',
            'Access-Control-Allow-Headers': ', '.join(allow_headers),
        }
        return HTTPResponse('', headers=headers)

def cors_middle_res(request: Request, response: HTTPResponse):
    """跨域处理"""
    allow_origin = '*'
    response.headers.update(
        {
            'Access-Control-Allow-Origin': allow_origin,
        }
    )
