from functools import reduce
from blueprints.project.models import Project
from const import CommonResponse, ResponseCode
from framework.api import (BaseApi, DeleteMixin, GetListMixin, GetMixin, Pagination, PatchMixin, PostMixin,
                           ReadMixin, WriteMixin)
from framework.models import StatusEnum
from sanic import response
from sanic.request import Request
from tortoise.models import Q
from tortoise.exceptions import DoesNotExist, IntegrityError

from .models import File, Macro, TestCase, TestCaseDetail, TestTag
import json
from datetime import datetime
from sanic.log import logger

class TestTagView(BaseApi, GetListMixin, PostMixin):
    model = TestTag
    search_fields = ('title',)

    @classmethod
    async def get_queryset(cls, request: Request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        ids = await Project.filter_by_user(user).values('id')
        ids = [item['id'] for item in ids]
        qs = qs.filter(project_id__in=ids)
        return qs

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        if project_id := request.args.get('project_id'):
            qs = qs.filter(project_id=project_id)
        page = request.args.get('page')
        if page:
            params = request.args
            page = params.get('page', 1)
            page_size = params.get('page_size', cls.pagination_class.page_size)
            page, page_size = int(page), int(page_size)
            data = await Pagination().get_data(qs, page, page_size, cls.excludes_fields)
        else:
            data = await qs.limit(5).distinct().values('title')
            data = [item['title'] for item in data]
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': data
        }, 200

class TestCaseView(BaseApi, ReadMixin, WriteMixin, DeleteMixin):
    model = TestCase
    search_fields = ('title', )
    order_by = ('-createAt', )
    
    @classmethod
    async def get_queryset(cls, request: Request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        ids = await Project.filter_by_user(user).values('id')
        ids = [item['id'] for item in ids]
        project_id = request.args.get('project_id')
        if project_id and int(project_id) in ids:
            qs = qs.filter(project_id=project_id)
        else:
            qs = qs.filter(project_id__in=ids)
        if not user.isAdmin:
            qs = qs.filter(status=StatusEnum.NORMAL)
        return qs

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        if tags := request.args.get('tags'):
            if isinstance(tags, str):
                tags = tags.split('|')
            q = [Q(tag__contains=json.dumps(tag)) for tag in tags]
            filters = reduce(lambda x, y:  x|y, q )
            qs = qs.filter(filters)         # TODO 性能问题
        
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
        }

    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        if 'tag' in params and not isinstance(tag := params['tag'], str):
            params['tag'] = json.dumps(tag)
        params['createBy'] = request.ctx.user
        try:
            obj = await cls.model.create(**params)
        except Exception as e:
            return {'message': '参数错误'}, 200
        return {
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def patch(cls, request, pk=None): # partial update
        params = request.form or request.json
        obj = await cls.get_object(request, pk)
        if 'tag' in params and not isinstance(tag := params['tag'], str):
            params['tag'] = json.dumps(tag)
        obj = await obj.update(**params)
        return {
            'code': ResponseCode.OK,
            'message': '更新成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def delete(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        obj.status = StatusEnum.DELETED
        await obj.save(update_fields=('status',))
        return {
            'code': ResponseCode.OK,
            'message': '删除成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def real_delete(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        await obj.delete()
        return {
            'code': ResponseCode.OK,
            'message': '删除成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def details(cls, request, pk=None):
        case = await cls.get_object(request, pk)
        details = await case.get_details()
        details = [detail.to_dict() for detail in details]
        return response.json({
            'code': ResponseCode.OK,
            'data': details
        })

    @classmethod
    async def deleteDetail(cls, request, pk=None):
        case = await cls.get_object(request, pk)
        detail_id = request.json.get('id')
        detail = await case.details.filter(id=detail_id).get_or_none()
        if detail:
            await detail.delete()
        return response.json({
            'code': ResponseCode.OK,
            'message': '删除成功'
        })

    @classmethod
    async def moveDetail(cls, request, pk=None):
        case = await cls.get_object(request, pk)
        req = request.json or request.form
        source, target = req.get('source'), req.get('target')
        if source != target:
            detail = await case.details.all().get(pk=source)
            await detail.move_to(target)
        return response.json({
            'code': ResponseCode.OK,
            'message': '移动成功'
        })

    @classmethod
    async def getDetail(cls, request, pk=None):
        case = await cls.get_object(request, pk)
        detail_id = request.args.get('id')
        detail = await case.details.all().get(pk=detail_id)
        return response.json({
            'code': ResponseCode.OK,
            'data': detail.to_dict()
        })

    @classmethod
    async def insertDetail(cls, request, pk=None):
        req = request.json
        assert int(pk) == req.get('testcase_id')
        detail = await TestCaseDetail.create(**req)
        await TestCaseDetail.filter(testcase_id=pk,next_id=req.get('next_id')).exclude(id=detail.id).update(next_id=detail.id)
        return response.json({
            'code': ResponseCode.OK,
            'message': '保存成功'
        })
    
    @classmethod
    async def export_case(cls, request):
        req = request.json
        ids = req.get('ids')
        qs = None
        if ids:
            qs = TestCase.filter(id__in=ids)
        qs = await cls.get_queryset(request, qs=qs)
        if tags := request.args.get('tags'):
            if isinstance(tags, str):
                tags = tags.split('|')
            q = [Q(tag__contains=json.dumps(tag)) for tag in tags]
            filters = reduce(lambda x, y:  x|y, q )
            qs = qs.filter(filters) 
        cases = await qs.filter(status=StatusEnum.NORMAL).all()
        details = [await case.get_details() for case in cases]
        details = [[step.to_dict() for step in detail] for detail in details]
        cases = [case.to_dict() for case in cases]
        for case, detail in zip(cases, details):
            case['details'] = detail
        return {
            'code': ResponseCode.OK,
            'data': cases
        }

    @classmethod
    async def import_case(cls, request):
        req = request.json
        user = request.ctx.user
        duplicates = []
        errors = []
        for data in req:
            try:
                data.pop('id', None)
                data.pop('createAt', None)
                data['createBy_id'] = user.id
                details = data.pop('details', [])
                case = await TestCase.create(**data)
                await case.save_details(details)
            except IntegrityError:
                duplicates.append(data.get('title'))
                logger.exception('')
            except:
                title = data.get('title')
                errors.append(title)
                logger.exception('导入用例[%s]发生异常', title)
        if not (duplicates + errors):
            return {
                'code': ResponseCode.OK,
                'message': '导入成功'
            }
        message = ['导入失败。']
        if duplicates:
            message.append('标题重复或者字段缺失: ' + ', '.join(duplicates))
        if errors:
            message.append('未知错误: ' + ', '.join(errors))
        message.append('请参照导出格式导入用例。')
        return {
            'code': ResponseCode.BAD_REQUEST_ARGS,
            'message': '\n'.join(message)
        }
    
    @classmethod
    async def copy(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        data = request.json
        data.pop('id', None)
        case = await TestCase.create(**data)
        details = await obj.get_details()
        details = [detail.to_dict() for detail in details]
        await case.save_details(details)
        return {
            'code': ResponseCode.OK,
            'message': '复制成功'
        }
        

class CaseDetailView(BaseApi, PatchMixin):
    model = TestCaseDetail

class MacroView(BaseApi, ReadMixin, WriteMixin, DeleteMixin):
    model = Macro
    pagination_class = Pagination
    search_fields = ('name', )

    @classmethod
    async def get_queryset(cls, request: Request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        ids = await Project.filter_by_user(user).values('id')
        ids = [item['id'] for item in ids]
        project_id = request.args.get('project_id')
        if project_id and int(project_id) in ids:
            qs = qs.filter(project_id=project_id)
        else:
            qs = qs.filter(project_id__in=ids)
        return qs
    
    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        params['createBy'] = request.ctx.user
        obj = cls.model(**params)
        await obj.save()
        return {
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        if request.args.get('verified'):
            qs = qs.filter(status=StatusEnum.NORMAL)
        qs = qs.prefetch_related('createBy', 'verifiedBy', 'project')
        total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        fields = cls.model._db_fields()
        items = await qs.values(*fields, createBy_name='createBy__username', verifiedBy_name='verifiedBy__username', project_name="project__name")
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
    async def verify(cls, request, pk):
        m = await cls.get_object(request, pk)
        m.status = StatusEnum.NORMAL
        m.verifiedBy = request.ctx.user
        m.verifiedAt = datetime.now()
        await m.save()
        return {
            'code': ResponseCode.OK,
            'message': '审核通过'
        }, 200

    @classmethod
    async def patch(cls, request, pk):
        m = await cls.get_object(request, pk)
        data = request.json
        if m.to_dict() != dict(data):
            data['status'] = StatusEnum.DISABLED
            data['verifiedBy_id'] = None
        obj = await m.update(**data)
        return {
            'code': ResponseCode.OK,
            'message': '更新成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200


class FileView(BaseApi, ReadMixin, WriteMixin, DeleteMixin):
    model = File
    search_fields = ('name', )
    order_by = ('classify', 'name')

    @classmethod
    async def get_queryset(cls, request: Request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        ids = await Project.filter_by_user(user).values('id')
        ids = [item['id'] for item in ids]
        project_id = request.args.get('project_id')
        if project_id and int(project_id) in ids:
            qs = qs.filter(project_id=project_id)
        else:
            qs = qs.filter(project_id__in=ids)
        return qs

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        if not request.args.get('name'):
            parent_id = request.args.get('parent_id', None)
            qs = qs.filter(parent_id=parent_id)
        qs = qs.prefetch_related('createBy', 'project')
        # total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        fields = cls.model._db_fields()
        items = await qs.values(*fields, createBy_name='createBy__username', project_name="project__name")
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': {
                # 'total': total,
                'items':[
                    cls.model.dic_to_json(item) for item in items
                ]
            }
        }, 200

    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        user = request.ctx.user
        params.update(createBy=user)
        try:
            obj = await cls.model.create(**params)
        except IntegrityError:
            return {'message': '重复名称'}, 200
        except:
            return {'message': '参数错误'}, 200
        return {
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def delete(cls, request, pk): # delete
        obj = await cls.get_object(request, pk)
        if (await obj.children.all().count()) > 0:
            return CommonResponse.DELETE_NOT_ALLOWED, 200
        await obj.delete()
        return {
            'code': ResponseCode.OK,
            'message': '删除成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200