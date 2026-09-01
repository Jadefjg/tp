from blueprints.case.models import File
import os

from config import Config, DEBUG
from tortoise import Tortoise
from sanic.log import logger

path = os.path.dirname(os.path.dirname(__file__))
bp_path = os.path.join(path, 'blueprints')
models = ['blueprints.%s.models'%x for x in os.listdir(bp_path) if not x.startswith('__') and not x.endswith('.py')]

TORTOISE_ORM = {
    "connections": Config.DB_CONNECTION,
    "apps": {
        "models": {"models": models + ['aerich.models'], "default_connection": "default"},
    },
}

def init_db(app):
    @app.listener('before_server_start')
    async def db_at_start(app, loop):
        await Tortoise.init(
            config={
                'connections': Config.DB_CONNECTION,
                'apps': {
                    'models': {'models': models, "default_connection": "default"}
                }
            },
            timezone=Config.TIME_ZONE
        )
        if DEBUG:
            await Tortoise.generate_schemas(safe=True)
            try:
                await init_data()
            except:
                logger.exception('调试数据初始化错误。')

    @app.listener('after_server_stop')
    async def db_at_stop(app, loop):
        await Tortoise.close_connections()

async def init_data():
    from blueprints.task.models import Task, TaskScheduler
    from blueprints.user.models import LoginRecord
    from blueprints.case.models import Macro
    from blueprints.user.models import User, UserInfo
    from blueprints.project.models import Project, Environment, EnvironmentDetail, ProjectNotify
    from blueprints.case.models import TestTag, TestCase, TestCaseDetail
    from blueprints.api.models import RemoteProject
    try:
        await RemoteProject.create(
            project_id=1,
            url='http://119.91.67.180/',
            remote_project_id=349,
            remote_project_name='服务商售后',
            token='e37f3f1d7f2a76eb5ee66c3e5ea1a625b6dcb88aba22a55063f662b9699775cd'
        )
    except:
        pass
    user = User(**{
        'username': 'ryan',
        'password': 'ryan',
        'isAdmin': True
    })
    await user.save()
    token = 'uJr61nVE3AtqhSD3oXk5hYw474RvjNZnGg62O0qmOBWJe02gGP32itRzBncTSh5k6RvnEneGh89s16wIufegLw648yUvV4bDJl4rdTuaEk7Ti9fM9JPjCfRR9HLLGgT4C6yygAdZqpu1povHva9BP3CmaId1qcroLSKt84J0tVjrNpwxA9SwoxRZ6y8RSkXPSdQoMr0q'
    await LoginRecord.create(user=user, token=token, status=1)
    token = '5XBW8qETFlkAInwzi5j44jiSrGaLUEc445UjLEPdkRHy2ah5aa3eiLYNRWFXwUzdj6ExWhal6MttDcNsPWCMmveYF1cJlrxgSMFYmZD32gyQMBBPIpxbttnxaYtpJTetb1K7mOEjd2HDy60T8IdlbvBwYceLMWMVAcYFFkrRehojuhwqPlm3J7vQVkU7ndwNeF4a6Kz4'
    await LoginRecord.create(user=user, token=token, status=1)
    user_info = UserInfo(**{
        'user': user,
        "name": 'ryan'
    })
    await user_info.save()
    project = await Project.create(name="新零售", description="新零售项目", createBy=user)
    await ProjectNotify.filter(project=project).update(
        access_token='70adfe245673c4cded50548602355f535deca8df47bff11e0465ca4d19fb8781',
        secret='SECbff1186bdc8d08b42017a3e9bfb48f174f694bcb3d017eb10f30ee3b9af40d0a')
    env = await Environment.create(name="新零售-测试环境", description="新零售测试环境", project=project, createBy=user)
    await EnvironmentDetail.create(environment=env, key="url", value='https://saas-test.aqara.com')
    await EnvironmentDetail.create(environment=env, key="username", value='wangrui@top365.ml')

    await TestTag.create(title="项目", project=project)
    await TestTag.create(title="CRM", project=project)
    await TestTag.create(title="工单", project=project)
    await TestTag.create(title="上传图片", project=project)
    project1 = await Project.create(name="ODOO", description="ERP", createBy=user)
    await TestTag.create(title="CRM", project=project1)
    await TestTag.create(title="订单", project=project1)
    await TestTag.create(title="库存", project=project1)
    await File.create(classify='file', createBy=user, full_name='abc-123.jpg', name='abc-123.jpg', project=project,
        size=384509,
        path="/media/casefile/09942401d92b87de5ef1eceea640084db04e48958a6a65ca0848f4e4103ec088.jpg")
    case = await TestCase.create(title="零售挂单", project=project, tag='["服务商", "零售订单"]', priority=5, description="零售挂单", createBy=user)
    case1 = await TestCase.create(title="零售开单", project=project, tag='["服务商", "零售订单"]', priority=5, description="零售开单", createBy=user)
    case2 = await TestCase.create(title="零售开单1", project=project, tag='["零售订单"]', priority=1, description="零售开单", createBy=user)
    case3 = await TestCase.create(title="零售开单2", project=project, tag='["服务商", "零售订单"]', priority=3, description="零售开单", createBy=user)
    case4 = await TestCase.create(title="零售开单3", project=project, tag='["服务商"]', priority=4, description="零售开单", createBy=user)
    case5 = await TestCase.create(title="零售开单4", project=project, tag='["服务商", "零售订单"]', priority=5, description="零售开单", createBy=user)
    case6 = await TestCase.create(title="零售开单5", project=project, tag='["服务商", "零售订单"]', priority=7, description="零售开单", createBy=user)
    detail = await TestCaseDetail.create(testcase=case, title="打开主页", comment="打开saas-test.aqara.cn", classify='raw', content="{\"code\":\"print('123')\"}")
    detail1 = await TestCaseDetail.create(testcase=case, title="点击登录按钮", comment="点击登录按钮", classify='raw', content="{\"code\":\"print('123')\"}")
    await detail.update(next_id=detail1.id)
    detail2 = await TestCaseDetail.create(testcase=case, title="输入用户名", comment="输入用户名", classify='raw', content="{\"code\":\"print('123')\"}")
    await detail1.update(next_id=detail2.id)
    detail3 = await TestCaseDetail.create(testcase=case, title="输入密码", comment="输入密码", classify='raw', content="{\"code\":\"print('123')\"}")
    await detail2.update(next_id=detail3.id)

    detail = await TestCaseDetail.create(testcase=case1, title="打开主页", comment="打开saas-test.aqara.cn", classify='raw', content="{\"code\":\"print('123')\"}")
    detail1 = await TestCaseDetail.create(testcase=case1, title="点击登录按钮", comment="点击登录按钮", classify='raw', content="{\"isCorotine\":true, \"code\":\"await asyncio.sleep(10)\\nprint(123)\"}")
    await detail.update(next_id=detail1.id)
    detail2 = await TestCaseDetail.create(testcase=case1, title="输入用户名", comment="输入用户名", classify='raw', content="{\"code\":\"print('123')\\nimport time\\ntime.sleep(3)\"}")
    await detail1.update(next_id=detail2.id)
    detail3 = await TestCaseDetail.create(testcase=case1, title="输入密码", comment="输入密码", classify='raw', content="{\"code\":\"import time\\nprint('123')\\nlogger = ctx.get_logger()\\nlogger.info('this is a info')\\ntime.sleep(1)\\nlogger.info('this is also a info')\\n\"}")
    await detail2.update(next_id=detail3.id)

    content = "{\"params\":[{\"key\":\"a\",\"checked\":true,\"value\":\"123\"}],\"headers\":[{\"key\":\"token\",\"checked\":true,\"value\":\"thisisatoken\"}],\"body\":{},\"cookie\":[{\"key\":\"c\",\"checked\":true,\"value\":\"123\"}],\"method\":\"GET\",\"url\":\"http://httpbin.org/get\",\"extract\":{\"regex\":[],\"jsonpath\":[{\"jsonpath\":\"json.origin\"}]}}"
    d = await TestCaseDetail.create(testcase=case4, title="输入密码", comment="输入密码", classify='api', content=content)
    # content = "{\"params\":[{\"key\":\"abc\",\"checked\":true,\"value\":\"3\"}],\"headers\":[{\"key\":\"token\",\"checked\":true,\"value\":\"nicetoken\"}],\"body\":{\"classify\":\"form-data\",\"formBody\":[{\"key\":\"anc\",\"checked\":true,\"value\":\"3\"},{\"key\":\"fsdf\",\"checked\":true,\"valueType\":\"File\",\"file\":{\"id\":1,\"name\":\"abc-123.jpg\"}}]},\"cookie\":[{\"key\":\"cccc\",\"checked\":true,\"value\":\"1\"}],\"method\":\"POST\",\"url\":\"http://httpbin.org/post\"}"
    # d1 = await TestCaseDetail.create(testcase=case4, title="post", comment="输入密码", classify='api', content=content)
    # await d.update(next_id=d1.id)
    
    await TestCaseDetail.create(testcase=case2, title="测试失败", comment="失败", classify='raw', content="{\"code\":\"print('123')\\nassert 1==0, '失败了吧'\"}")
    await TestCaseDetail.create(testcase=case3, title="测试错误", comment="直接抛异常", classify='raw', content="{\"code\":\"raise ValueError('什么玩意啊')\"}")
    await Macro.create(project=project, name="登录", comment="登录系统", code="", createBy=user)

    task = await Task.create(project=project, taskname="测试新零售", comment='for debug', createBy=user)
    await task.add_testcase([case5, case1, case4])
    scheduler = await TaskScheduler.create(task=task, env=env, trigger='date', trigger_params={'run_date': '2021-12-20 00:00:00'}, createBy=user)
    
    logger.debug('调试数据初始化完成。')