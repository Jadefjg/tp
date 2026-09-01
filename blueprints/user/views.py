from sanic import views, response
from sanic.request import Request
from .models import User, UserInfo, LoginRecord
from tortoise.exceptions import DoesNotExist, IntegrityError
# import jwt
import time
from config import Config
from utils import to_str, to_bytes
from hashlib import sha1
import hmac
from urllib.parse import urlencode, quote
from const import CommonResponse, ResponseCode
from framework.api import BaseApi, ReadMixin, WriteMixin, DeleteMixin

class Login(views.HTTPMethodView):
    async def post(self, request:Request):
        params =  request.form or request.json
        username = params.get('username')
        password = params.get('password')
        try:
            user:User = await User.get(username=username)
            if user.status != 1:
                return response.json({'message': '用户被禁用了'})
            if user.check_password(password):
                token = await LoginRecord.login(user)
                return response.json({
                    'code': ResponseCode.OK,
                    'message': '',
                    'data': {"token": token}
                })
        except DoesNotExist as e:
            pass
        return response.json({
            'code': ResponseCode.WRONG_LOGIN_INFO,
            'message': '用户名或者密码不正确',
            'data': None
        }, status=200)

class Logout(views.HTTPMethodView):
    async def post(self, request: Request):
        user = request.ctx.user
        token = request.ctx.token
        await LoginRecord.logout(user, token)
        return response.json({
            'code': ResponseCode.OK,
            'message': '登出成功',
            'data': None
        })

class GetUserInfo(views.HTTPMethodView):
    async def get(self, request):
        user = request.ctx.user
        if user:
            try:
                user_info:UserInfo = await UserInfo.get(user=user)
                user_info = user_info.to_dict()
                user_info.update(isAdmin=user.isAdmin)
                return response.json({
                    'code': ResponseCode.OK,
                    'data': user_info,
                    'message': ''
                })
            except DoesNotExist:
                return response.text(CommonResponse.WRONG_LOGIN_INFO,
                                     status=401)
        return response.text(CommonResponse.ILLEGAL_TOKEN,
                             status=401)

class UploadView(views.HTTPMethodView):
    def _sha1(self, s):
        s = to_bytes(s)
        return sha1(s).hexdigest()

    def _quote(self, s, *args, **kw):
        return quote(s, '-_.~', *args[1:], **kw)

    def _hmac_sha1(self, s, key):
        s = to_bytes(s)
        key = to_bytes(key)
        return hmac.new(key, s, sha1).hexdigest()

    def get_auth(self, method, url, headers=None, params=None):
        if headers is None:
            headers = {}
        if params is None:
            params = {}
        headers = {k.lower(): v for k, v in headers.items() }
        options = {
            'q-sign-algorithm': 'sha1',
            'q-ak': Config.COS_SECRET_ID,
            'q-sign-time': None,
            'q-key-time': None,
            'q-header-list': None,
            'q-url-param-list': None,
            'q-signature': None
        }
        t = time.time()
        options['q-sign-time'] = options['q-key-time']='%d;%d'%(t - 60, t + Config.COS_AUTH_EXPIRE)
        options['q-header-list'] = ';'.join(sorted(headers.keys()))
        options['q-url-param-list'] = ';'.join(sorted(params.keys()))
        skey = self._hmac_sha1(options['q-sign-time'])
        http_str = '\n'.join([method.lower(),
            url,
            urlencode(sorted(params.items()),
                quote_via=self._quote).replace('+', '%2B'),
            urlencode(sorted(headers.items()),
                quote_via=self._quote)]) + '\n'
        # print(http_str)
        s_str = '\n'.join([options['q-sign-algorithm'],
            options['q-sign-time'],
            self._sha1(http_str)]) + '\n'
        # print(s_str)
        sig = self._hmac_sha1(s_str, skey)
        options['q-signature']=sig
        auth = urlencode(options, quote_via=lambda x, *args, **kw:x)
        return auth

    async def post(self, request):
        data = request.form or request.json
        method = data.get('method')
        pathname = data.get('pathname')
        hd = data.get('hd')
        qs = data.get('qs')
        if any(x is None for x in [method, pathname]):
            return response.text('', status=400)
        auth = self.get_auth(method, pathname, hd, qs)
        return response.json({'Authorization': auth})

class UserView(BaseApi, ReadMixin, WriteMixin, DeleteMixin):
    model = User
    excludes_fields = ['_password']
    search_fields = ('username',)

    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        # print(params)
        try:
            obj = cls.model(**params)
            await obj.save()
        except IntegrityError as e:
            return response.json({
                "message": "该用户名已存在"
            }, status=200)
        info = UserInfo(user=obj, name=obj.username)
        await info.save()
        return response.json({
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, status=201)

    @classmethod
    async def delete(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        await obj.delete()
        return response.json({
            'code': ResponseCode.OK,
            'message': '更新成功',
            'data': obj.to_dict(cls.excludes_fields)
        })