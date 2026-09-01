from config import DEBUG
from sanic import views, response
from sanic.request import Request
import asyncio
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.models import Q, QuerySet
# import jwt
from inspect import isawaitable
from const import ResponseCode, CommonResponse
from functools import reduce
from sanic.log import error_logger as logger

class Pagination:
    page_size = 20
    page_key = 'page'
    page_size_key = 'page_size'

    async def get_data(self, queryset, page, page_size, excludes=frozenset()):
        offset = page * page_size - page_size
        items, total = await queryset.limit(page_size).offset(offset).all(), await queryset.count()
        return {
            'total': total,
            'items': [i.to_dict(excludes) for i in items]
        }
    
    def get_queryset(self, queryset, request):
        params = request.args or request.form or request.json or {}
        page = int(params.get(self.page_key, 1))
        page_size = int(params.get(self.page_size_key, self.page_size))
        offset = page * page_size - page_size
        return queryset.limit(page_size).offset(offset)

    async def get_total_queryset(self, queryset, request):
        total = await queryset.count()
        return total, self.get_queryset(queryset, request)
        

class BaseApi:
    model = None
    pagination_class = Pagination
    excludes_fields = []
    order_by = ()
    search_fields = ()
    filter_fields = ()

    @classmethod
    async def get_queryset(cls, request: Request, qs=None):
        qs = qs or cls.model.all()
        search_value = request.args.get('search', None)
        if search_value and cls.search_fields:
            q = [Q(**{"%s__contains" % k: search_value }) for k in cls.search_fields]
            q = reduce(lambda x, y: x|y, q)
            qs = qs.filter(q)
        filter_fields = cls.filter_fields if isinstance(cls.filter_fields, (list, tuple, set)) else [cls.filter_fields]
        if filter_fields:
            q = [Q(**{ k: filter_value }) for k in filter_fields if (filter_value := request.args.get(k)) is not None]
            if q:
                q = reduce(lambda x, y: x&y, q)
                qs = qs.filter(q)
        order_by = request.args.getlist('order_by', cls.order_by)
        if order_by:
            qs = qs.order_by(*order_by)
        return qs.distinct()

    @classmethod
    async def get_object(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        return await qs.get(pk=pk)

    @classmethod
    def register(cls, blueprint, name, prefix='/api'):
        endpoint_list = '%s/%s'%(prefix, name)
        endpoint_list_action = '%s/%slist/<action>'%(prefix, name)
        endpoint_one = '%s/%s/<pk:int>'%(prefix, name)
        endpoint_one_action = '%s/%s/<pk:int>/<action>'%(prefix, name)
        blueprint.route(endpoint_list, methods=['GET', 'POST'])(lambda request:cls.dispatch(request))
        blueprint.route(endpoint_list_action, methods=['GET', 'POST'])(lambda request, action:cls.dispatch(request, action=action))
        blueprint.route(endpoint_one, methods=['GET', 'PUT', 'PATCH', 'DELETE'])(lambda request, pk:cls.dispatch(request, pk))
        blueprint.route(endpoint_one_action, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])(lambda request, pk, action:cls.dispatch(request, pk, action))

    @classmethod
    def verify_request(cls, request):
        user = request.ctx.user
        return user is not None

    @classmethod
    async def authorization(cls, request):
        return True

    @classmethod
    async def dispatch(cls, request:Request, pk=None, action=None):
        try:
            if not cls.verify_request(request):
                return response.json(
                    CommonResponse.WRONG_LOGIN_INFO, status=200)
        except:
            return response.json(CommonResponse.WRONG_LOGIN_INFO,
                                 status=200)
        if not (await cls.authorization(request)):
            return response.json(CommonResponse.FORBIDDEN, status=200)
        method = request.method.lower()
        if pk is None and method == 'get':
            method = 'getlist'
        handler = None
        if action is not None:
            handler = getattr(cls, action, None)
            if handler is None:
                return response.json({
                    'code': ResponseCode.OBJECT_NOT_FOUND,
                    'message': 'Path %s not found' % request.path
                }, status=200)
        if handler is None:
            handler = getattr(cls, method, None)
        if handler is None:
            return response.json(
                CommonResponse.METHOD_NOT_ALLOWED, status=200)
        try:
            try:
                if pk:
                    ret = handler(request, pk)
                else:
                    ret = handler(request)
                if isawaitable(ret):
                    ret = await ret
            except Exception as e:
                logger.exception(e)
                raise
        except DoesNotExist as e:
            return response.json(CommonResponse.OBJECT_NOT_FOUND)
        except IntegrityError as e:
            return response.json(CommonResponse.DUPLICATE_KEY)
        except Exception as e:
            return response.json(CommonResponse.BAD_REQUEST)
        if isinstance(ret, response.BaseHTTPResponse):
            return ret
        if not isinstance(ret, tuple):
            ret = (ret, 200)
        data, status_code = ret
        return response.json(data, status=status_code)

class GetListMixin:
    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        if cls.pagination_class:
            total = await qs.count()
            data = await cls.pagination_class().get_queryset(qs, request).all()
            data = {
                'total': total,
                'items': [d.to_dict(cls.excludes_fields) for d in data]
            }
        else:
            data = await qs
            data = [d.to_dict(cls.excludes_fields) for d in data]
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': data
        }, 200

class GetMixin:
    @classmethod
    async def get(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        return {
            'code': ResponseCode.OK,
            'message': '对象获取成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

class PostMixin:
    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        obj = cls.model(**params)
        await obj.save()
        return {
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

class PutMixin:
    @classmethod
    async def put(cls, request, pk=None): # update
        params = request.form or request.json
        obj = await cls.get_object(request, pk)
        obj = await obj.replace(**params)
        return {
            'code': ResponseCode.OK,
            'message': '更新成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

class PatchMixin:
    @classmethod
    async def patch(cls, request, pk=None): # partial update
        params = request.form or request.json
        obj = await cls.get_object(request, pk)
        obj = await obj.update(**params)
        return {
            'code': ResponseCode.OK,
            'message': '更新成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

class DeleteMixin:
    @classmethod
    async def delete(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        await obj.delete()
        return {
            'code': ResponseCode.OK,
            'message': '删除成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200


class ReadMixin(GetListMixin, GetMixin):
    pass

class WriteMixin(PostMixin, PatchMixin, PutMixin):
    pass

# def verify_token(token, secret):
#     payload = jwt.decode(token, secret,  algorithms=['HS256'])
#     if payload:
#         return True, payload
#     return False, {}


