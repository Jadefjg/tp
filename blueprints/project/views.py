from framework.models import StatusEnum
from sanic import views, response
from sanic.request import Request
from tortoise.models import Q
from tortoise.exceptions import IntegrityError
from framework.api import BaseApi, DeleteMixin, ReadMixin, WriteMixin
from .models import Project, Environment, EnvironmentDetail
from ..user.models import User
from const import CommonResponse, ResponseCode
from tortoise.transactions import atomic, in_transaction
from tortoise.exceptions import DoesNotExist

class ProjectView(BaseApi, ReadMixin, WriteMixin):
    model = Project
    order_by = ('-createAt',)
    search_fields = ('name',)

    @classmethod
    async def get_queryset(cls, request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        if not user.isAdmin:
            qs = qs.filter(status=1).filter(Q(members__id=user.id) | Q(createBy=user))
        return qs

    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        # print(params)
        params.update(createBy=request.ctx.user)
        try:
            obj = cls.model(**params)
            await obj.save()
        except IntegrityError as e:
            return response.json({
                'message': "该项目已存在"
            }, status=202)
        except Exception:
            return response.json({
                'message': "参数错误"
            }, status=203)
        return response.json({
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, status=201)

    @classmethod
    async def members(cls, request, pk=None):
        project = await cls.get_object(request, pk)
        mems = await project.members.all()
        return response.json({
            'code': ResponseCode.OK,
            'message': '获取成功',
            'data': [{
                'username': mem.username,
                "id": mem.id,
                "enabled": mem.status==1
                } for mem in mems]
        }, status=200)

    @classmethod
    async def assign(cls, request, pk=None):
        user = request.ctx.user
        project = await cls.get_object(request, pk)
        if not user.isAdmin:
            mem = await project.members.all().get_or_none(id=user.id)
            if mem is None and project.createBy_id != user.id:
                return response.json({
                    'code': ResponseCode.FORBIDDEN,
                    'message': '你不是项目成员无权分配。',
                    'data': None
                }, status=200)
        mem_ids = request.json['members']
        await project.members.clear()
        members = await User.filter(id__in=mem_ids).all()
        await project.members.add(*members)
        return response.json({
            'code': ResponseCode.OK,
            'message': '分配成功',
            'data': None
        }, status=200)

    @classmethod
    async def get_notify(cls, request, pk):
        project = await cls.get_object(request, pk)
        notify = await project.notify.get()
        return {
            'code': ResponseCode.OK,
            'data': notify.to_dict()
        }

    @classmethod
    async def save_notify(cls, request, pk):
        project = await cls.get_object(request, pk)
        notify = await project.notify.get()
        await notify.update(**request.json)
        return {
            'code': ResponseCode.OK,
            'message': '更新成功'
        }

class EnvironmentView(BaseApi, ReadMixin, WriteMixin, DeleteMixin):
    model = Environment
    order_by = ('-createAt', )
    search_fields = ('name',)

    @classmethod
    async def get_queryset(cls, request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        project_qs = Project.filter_by_user(request.ctx.user)
        ids = await project_qs.values('id')
        ids = [item['id'] for item in ids]
        project_id = request.args.get('project_id')
        if project_id and int(project_id) in ids:
            qs = qs.filter(project_id=project_id)
        else:
            qs = qs.filter(project_id__in=ids)
        if not request.ctx.user.isAdmin:
            qs = qs.filter(status=StatusEnum.NORMAL)
        return qs

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        qs = qs.prefetch_related('createBy', 'project')
        total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        fields = cls.model._db_fields()
        items = await qs.values(*fields, createBy_name='createBy__username', project_name='project__name')
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': {
                'total': total,
                'items':[
                    cls.model.dic_to_json(item) for item in items
                ]
            }
        }, 200

    @classmethod
    async def delete(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        obj.status=2
        await obj.save()
        return {
            'code': ResponseCode.OK,
            'message': '删除成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200
        

    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        # print(params)
        params.update(createBy=request.ctx.user)
        try:
            obj = cls.model(**params)
            await obj.save()
        except IntegrityError as e:
            return response.json({
                'message': "该环境已存在"
            }, status=202)
        except Exception:
            return response.json({
                'message': "参数错误"
            }, status=203)
        return response.json({
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, status=201)

    @classmethod
    async def details(cls, request, pk=None):
        env = await cls.get_object(request, pk)
        details = await env.details.order_by('key').all()
        return response.json({
            'code': ResponseCode.OK,
            'message': '',
            'data': [d.to_dict() for d in details]
        }, status=200)

    @classmethod
    async def setDetails(cls, request, pk=None):
        env = await cls.get_object(request, pk)
        details = request.json['details']
        keys = [detail['key'] for detail in details]
        if len(set(keys)) != len(details):
            return response.json(CommonResponse.DUPLICATE_KEY,
                                 status=200)
        details_id = [detail['id'] for detail in details if 'id' in detail]
        new = [{**detail, 'environment_id': env.id} for detail in details if 'id' not in detail]
        async with in_transaction() as connection:
            if details_id:
                await env.details.all().exclude(id__in=details_id).using_db(connection).delete()
            else:
                await env.details.all().using_db(connection).delete()
            if new:
                await EnvironmentDetail.bulk_create([EnvironmentDetail(**d) for d in new], using_db=connection)
        return response.json({
            'code': ResponseCode.OK,
            'message': '保存成功',
            'data': None
        }, status=200)

    @classmethod
    async def clone(cls, request, pk=None):
        env = await cls.get_object(request, pk)
        params = request.form or request.json
        params.update(createBy=request.ctx.user)
        async with in_transaction() as connection:
            try:
                id = params.pop('id')
                obj = cls.model(**params)
                await obj.save(using_db=connection)
            except IntegrityError as e:
                return response.json({
                    'message': "该环境名称已存在"
                }, status=202)
            except Exception:
                return response.json({
                    'message': "参数错误"
                }, status=203)
            details = await env.details.all().using_db(connection)
            for detail in details:
                detail.id = None
                # detail.pk = None
                detail._custom_generated_pk = False
                detail.environment_id = obj.id
            await EnvironmentDetail.bulk_create(details, using_db=connection)
        return response.json({
            'code': ResponseCode.OK,
            'message': '复制成功',
            'data': None
        }, status=200)
