from enum import IntEnum
from sanic import response

class ResponseCode(IntEnum):
    OK = 20000
    
    OBJECT_NOT_FOUND = 40004
    DUPLICATE_KEY = 40000
    DELETE_NOT_ALLOWED = 40006
    METHOD_NOT_ALLOWED = 40005
    BAD_REQUEST_ARGS = 40007
    INVALID_STATE = 40010

    WRONG_LOGIN_INFO = 40001
    FORBIDDEN = 40003
    ILLEGAL_TOKEN = 50008
    OTHER_CLIENTS_LOGGED_IN = 50012
    TOKEN_EXPIRE = 50014
    
class CommonResponse:
    OBJECT_NOT_FOUND = {
        "code": ResponseCode.OBJECT_NOT_FOUND,
        "message": "未找到该对象",
        "data": None 
    }
    DUPLICATE_KEY = {
        "code": ResponseCode.DUPLICATE_KEY,
        "message": "重复的Key",
        "data": None 
    }
    DELETE_NOT_ALLOWED = {
        "code": ResponseCode.DELETE_NOT_ALLOWED,
        "message": "不允许删除",
        "data": None 
    }
    METHOD_NOT_ALLOWED = {
        "code": ResponseCode.METHOD_NOT_ALLOWED,
        "message": "不允许使用此方法请求",
        "data": None 
    }
    FORBIDDEN = {
        "code": ResponseCode.FORBIDDEN,
        "message": "禁止访问",
        "data": None
    }
    WRONG_LOGIN_INFO = {
        "code": ResponseCode.WRONG_LOGIN_INFO,
        "message": "登录信息错误",
        "data": None
    }
    ILLEGAL_TOKEN = {
        "code": ResponseCode.ILLEGAL_TOKEN,
        "message": "非法的Token",
        "data": None
    }
    OTHER_CLIENTS_LOGGED_IN = {
        "code": ResponseCode.OTHER_CLIENTS_LOGGED_IN,
        "message": "其他客户端登录，导致你被迫登出。",
        "data": None
    }
    TOKEN_EXPIRE = {
        "code": ResponseCode.TOKEN_EXPIRE,
        "message": "Token过期",
        "data": None
    }
    BAD_REQUEST = {
        "code": ResponseCode.BAD_REQUEST_ARGS,
        "message": "参数错误",
        "data": None
    }
    OK = {
        "code": ResponseCode.OK,
        "message": "操作成功"
    }

CONTENT_TYPE_MAP = {
    'text': 'text/plain',
    'javascript': 'application/javascript',
    'json': 'application/json',
    'html': 'text/html',
    'xml': 'application/xml'
}