from framework.models import StatusEnum
from aiohttp.client import request
from utils import datetime2time, time2datetime
from .models import RemoteProject, ApiCat, Api, SyncSource
from utils.yapi import YAPIClient
from blueprints.project.models import Project
from sanic.log import logger


class Sync:
    def __init__(self, project) -> None:
        self.project = project
    
    async def get_remote_projects(self):
        remote_projects = await RemoteProject.filter(project_id=self.project.id, status=StatusEnum.NORMAL)
        return remote_projects
        
    async def sync_cat(self, client, remote_project):
        cat = await client.get_cat_menu(project_id=remote_project.remote_project_id)
        for item in cat:
            cat_id = item['_id']
            api_cat = await ApiCat.filter(remote_cat_id=cat_id, remote_project=remote_project).get_or_none()
            # if api_cat is not None and datetime2time(api_cat.update_at) == item['uptime']:
            #     continue
            data = dict(
                project=self.project,
                remote_project=remote_project,
                remote_cat_id=item['_id'],
                name=item['name'],
                source=SyncSource.YAPI,
                update_at=time2datetime(item['up_time']),
                create_at=time2datetime(item['add_time'])
            )
            if api_cat is None:
                api_cat = await ApiCat.create(**data)
            else:
                await api_cat.update_from_dict(data)
            await self.sync_api(client, api_cat)

    async def sync_api(self, client: YAPIClient, api_cat):
        apis = await client.list_cat_interface(api_cat.remote_cat_id, limit=200)
        for api in apis['list']:
            await self._sync_api(client, api_cat, api)
        total = apis['total']
        for page in range(total-1):
            page = page + 2
            apis = await client.list_cat_interface(api_cat.remote_cat_id, limit=200)
            for api in apis['list']:
                await self._sync_api(client, api_cat, api)

    async def _sync_api(self, client: YAPIClient, api_cat, api):
        api_id = api['_id']
        api = await Api.filter(remote_api_id=api_id, api_cat=api_cat).get_or_none()
        remote_api = await client.get_interface(api_id)
        if api is not None and datetime2time(api.update_at) == remote_api['up_time']:
            return
        data = dict(
            project=self.project,
            api_cat=api_cat,
            remote_api_id=api_id,
            title=remote_api['title'],
            method=remote_api['method'],
            path=remote_api['path'],
            tag=remote_api.get('tag', []),
            req_params=remote_api.get('req_params', []),
            req_form=remote_api.get('req_body_form', []),
            req_body_json_schema=remote_api.get('req_body_is_json_schema', True),
            req_body_raw=remote_api.get('req_body_other', ''),
            req_body_type=remote_api.get('req_body_type', ''),
            req_headers=remote_api.get('req_headers', []),
            res_body=remote_api.get('res_body', ''),
            res_body_json_schema=remote_api.get('res_body_is_json_schema', True),
            res_body_type=remote_api.get('res_body_type', 'json'),
            desc=remote_api.get('desc'),
            markdown=remote_api.get('markdown'),
            source=SyncSource.YAPI,
            update_at=time2datetime(remote_api['up_time']),
            create_at=time2datetime(remote_api['add_time'])
        )
        if api is None:
            await Api.create(**data)
        else:
            await api.update_from_dict(data)

    async def sync_all(self):
        remote_projects = await self.get_remote_projects()
        for remote_project in remote_projects:
            if remote_project.source == SyncSource.YAPI:
                client = YAPIClient(remote_project.url, remote_project.token)
                await self.sync_cat(client, remote_project)


async def sync_all_project():
    logger.info('start sync api from remote.')
    projects = await Project.all()
    for project in projects:
        sync = Sync(project)
        await sync.sync_all()
    logger.info('end sync api from remote.')