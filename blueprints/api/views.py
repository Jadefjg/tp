from const import ResponseCode
from blueprints.api.models import ApiCat, RemoteProject, Api
from blueprints.project.models import Project
from framework.api import BaseApi, ReadMixin, WriteMixin
from sanic import Request
from urllib.parse import urlsplit

class RemoteProjectView(BaseApi, ReadMixin, WriteMixin):
    model = RemoteProject
    filter_fields = ('project_id', 'source')
    search_fields = ('remote_project_name', )

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
        total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        qs = qs.prefetch_related('project')
        fields = cls.model._db_fields()
        items = await qs.values(*fields, project_name="project__name")
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

class ApiCatView(BaseApi, ReadMixin, WriteMixin):
    model = ApiCat
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


class ApiView(BaseApi, ReadMixin, WriteMixin):
    model = Api
    search_fields = ('title', )
    filter_fields = ('api_cat_id', 'source')

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
        total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        qs = qs.prefetch_related('project', 'api_cat')
        fields = cls.model._db_fields()
        items = await qs.values(*fields, api_cat_name='api_cat__name', project_name="project__name")
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
    async def search(cls, request):
        qs = await cls.get_queryset(request, qs=None)
        query: str = request.args.get('query', '')
        if query.startswith('http://') or query.startswith('https://'):
            url = urlsplit(query)
            qs = qs.filter(path__startswith=url.path)
            prefix = '%s://%s' % (url.scheme, url.netloc)
        elif '/' not in query:
            qs = qs.filter(title__contains=query)
            prefix = ''
        else:
            prefix, path = query.split('/', 1)
            path = '/' + path
            qs = qs.filter(path__startswith=path)
        qs = qs.limit(10)
        items = await qs.all()
        items = [item.to_dict() for item in items]
        for item in items:
            item['value'] = prefix + item['path']
        return {
            'code': ResponseCode.OK,
            'data': items
        }