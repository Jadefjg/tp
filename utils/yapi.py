from aiohttp import ClientSession
from urllib.parse import urljoin
from enum import Enum
from functools import wraps

token = 'c4575a2373f0d7624451efaf59cabdeafa2567408a12f69c8ff88b7fc2145e59'
url = 'http://119.91.67.180/'

class YAPIPath(str, Enum):
    GET_PROJECT = '/api/project/get'
    GET_CAT_MENU = '/api/interface/getCatMenu'
    GET_INTERFACE = '/api/interface/get'
    LIST_CAT_INTERFACE = '/api/interface/list_cat'
    LIST_INTERFACE = '/api/interface/list'
    LIST_MENU_INTERFACE = '/api/interface/list_menu'

def get_api(func):
    @wraps(func)
    async def wrapper(self, *args, **kw):
        url, params = await func(self, *args, **kw)
        if not url.startswith('http'):
            url = urljoin(self.url, url)
        async with ClientSession(headers={'Content-Type': 'application/json'}) as sess:
            async with sess.get(url, params=params) as resp:
                rslt = await resp.json()
                assert rslt.get('errcode') == 0, '接口请求失败'
                return rslt.get('data')
    return wrapper

class YAPIClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token

    @get_api
    async def get_project(self):
        return YAPIPath.GET_PROJECT, {
                'token': self.token
            }

    @get_api
    async def get_cat_menu(self, project_id):
        return YAPIPath.GET_CAT_MENU, {
                'token': self.token,
                'project_id': project_id
            }

    @get_api
    async def get_interface(self, id):
        return YAPIPath.GET_INTERFACE, {
                'token': self.token,
                'id': id
            }

    @get_api
    async def list_cat_interface(self, catid, page=1, limit=20):
        return YAPIPath.LIST_CAT_INTERFACE, {
                'token': self.token,
                'catid': catid,
                'page': page,
                'limit': limit
            }

    @get_api
    async def list_interface(self, project_id, page=1, limit=20):
        return YAPIPath.LIST_INTERFACE, {
                'token': self.token,
                'project_id': project_id,
                'page': page,
                'limit': limit
            }

    @get_api
    async def list_menu_interface(self, project_id):
        return YAPIPath.LIST_MENU_INTERFACE, {
                'token': self.token,
                'project_id': project_id
            }

if __name__ == '__main__':
    client = YAPIClient(url, token)
    import asyncio, json
    def run(coro):
        rslt = asyncio.run(coro)
        print(json.dumps(rslt, indent=2))
        return rslt

    project_id = 275
    cat_id = 5853
    run(client.list_cat_interface(cat_id))
    
    # cat_menu = run(client.get_cat_menu(project_id=project_id))

    