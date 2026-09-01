from sanic import response, request
from framework.api import BaseApi, ReadMixin, WriteMixin, DeleteMixin
from . import models
from framework.models import StatusEnum
from tortoise.exceptions import DoesNotExist
from const import CommonResponse, ResponseCode
from po.widgets import BaseWidget
import inspect
from blueprints.project.models import Project
class ElementView(BaseApi, ReadMixin, WriteMixin, DeleteMixin):
    model = models.Element
    pagination_class = None
    search_fields = ('name',)

    @classmethod
    async def get_queryset(cls, request: request.Request, qs=None):
        if 'filter' in request.args:
            filter_value = request.args.pop('filter')
        ids = await Project.filter_by_user(request.ctx.user).values('id')
        ids = [item['id'] for item in ids]
        qs = qs or models.Element.filter(project_id__in=ids)
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        if not user.isAdmin:
            qs = qs.filter(status=StatusEnum.NORMAL)
        return qs

    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        # print(params)
        try:
            if 'project_id' not in params:
                parent = await cls.get_object(request, pk=params.get('parent_id'))
                params['project_id'] = parent.project_id
            obj = cls.model(**params)
            await obj.save()
        except Exception as e:
            return {}, 400
        return {
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def delete(cls, request, pk=None):
        el = await cls.get_object(request, pk=pk)
        el = await cls.get_object(request, pk)
        children_cnt = await el.children.all().filter(status=StatusEnum.NORMAL).count()
        if children_cnt > 0:
            return {
                'code': ResponseCode.DELETE_NOT_ALLOWED,
                'message': '元素下有子元素，不能删除',
                'data': None
            }, 200
        el.update_from_dict({'status': StatusEnum.DELETED})
        await el.save()
        return {
            'code': ResponseCode.OK,
            'message': '删除成功',
            'data': None
        }, 200

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        project_id = request.args.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)
        parent_id = request.args.get('parent_id')
        qs = qs.filter(parent_id=parent_id)
        data = await qs
        data = [d.to_dict(cls.excludes_fields) for d in data]
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': data
        }, 200

async def widget_list(request):
    name = request.args.get('name', '')
    all_widgets = BaseWidget.all_widgets()
    widgets = []
    for widget in all_widgets:
        if name in widget:
            widgets.append({
                'name': widget,
                'description': all_widgets[widget]['description']
            })
    page = request.args.get('page')
    if page is None:
        return response.json({
            'code': ResponseCode.OK,
            'message': '',
            'data': widgets
        })
    else:
        page_size = request.args.get('page_size', 10)
        page, page_size = int(page), int(page_size)
        return response.json({
            'code': ResponseCode.OK,
            'message': '',
            'data': {
                'items': widgets[page*page_size - page_size: page*page_size],
                'total': len(widgets)
            }
        })

async def widget_source(request):
    name = request.args.get('name', '')
    widget = BaseWidget.all_widgets().get(name)
    if widget is None:
        return response.json(CommonResponse.OBJECT_NOT_FOUND)
    src = inspect.getsource(widget['cls'])
    return response.json({
        'code': ResponseCode.OK,
        'data': src,
        'message': None
    })