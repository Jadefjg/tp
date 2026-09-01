from blueprints.project.models import Environment
from blueprints.task.models import Task
import time
import hmac
import hashlib
import base64
import urllib.parse
from aiohttp import ClientSession
from datetime import timedelta


def human_duration(duration: timedelta) -> str:
    seconds = duration.seconds
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}.{duration.microseconds:06d}'


class Dingding:
    def __init__(self, project_notify):
        assert project_notify.classify == 'dingding'
        self.project_notify = project_notify

    def get_url(self):
        access_token = self.project_notify.access_token
        secret = self.project_notify.secret
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return f'https://oapi.dingtalk.com/robot/send?access_token={access_token}&timestamp={timestamp}&sign={sign}'

    async def get_content(self, taskrun):
        from config import Config
        template = self.project_notify.report_template
        duration = taskrun.endAt - taskrun.startAt
        duration = human_duration(duration)
        taskrun = taskrun.to_dict()
        taskrun['duration'] = duration
        taskrun['pass_rate'] = round(10000*taskrun['pass_num']/taskrun['total_num'])/100
        report_url = 'http://%s/#/task/taskrun-detail?taskrun_id=%d' % (Config.HOST, taskrun['id'])
        taskrun['report_url'] = report_url
        task = await Task.get(pk=taskrun['task_id'])
        taskrun['task_name'] = task.taskname
        env = await Environment.get(pk=taskrun['env_id'])
        taskrun['env_name'] = env.name
        return template % taskrun

    async def send_dingding_notify(self, taskrun):
        url = self.get_url()
        pn = self.project_notify
        content = await self.get_content(taskrun)
        if not pn.at_all:
            for mobile in pn.at_mobile:
                content += '@%s' % mobile['number']
        
        data = {
            'at': {
                'atMobiles': pn.at_mobile,
                'isAtAll': pn.at_all
            },
            'markdown': {
                'title': '测试结果',
                'text': content
            },
            'msgtype': 'markdown'
        }
        async with ClientSession() as sess:
            async with sess.post(url, json=data) as resp:
                await resp.json()