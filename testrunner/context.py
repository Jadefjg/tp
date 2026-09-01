from utils import ensure_json
from collections import ChainMap
from ast import literal_eval
from random import choice
from string import ascii_letters, ascii_lowercase, ascii_uppercase, digits, whitespace, printable
import json

from aiohttp.client import ClientSession
from extentions.logger import TestrunnerLoggerAdapter
from config import Config
import logging
import re
from datetime import datetime, timedelta
import time

VAR_RE = re.compile(r'\${(?P<var_name>[^}]+)}')

class BultinMock:
    @staticmethod
    def phone():
        return '1' + choice('3456789') + (''.join(choice(digits) for _ in range(9)))

    @staticmethod
    def today():
        return datetime.today().strftime('%Y-%m-%d')
    
    @staticmethod
    def tomorrow():
        return (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')

    @staticmethod
    def now():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def timestamp():
        return str(int(time.time()))

    @staticmethod
    def timestamp1():
        return str(int(time.time() * 1000 ))

class BaseContext(ChainMap):
    """
    包含了运行测试用例的所有的东西
    driver， session， logger
    """
    def push(self, ctx):
        ctx = dict(ctx)
        self.maps.insert(0, ctx)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *ex):
        pass

    def set_global(self, key, value):
        first = self.maps[-1]
        if hasattr(first, 'set_global'):
            first.set_global(key, value)
        else:
            first[key] = value


    def _wrap_string(self, s, var_names=None):
        var_names = [] if var_names is None else var_names
        
        def repl(m):
            complete_str = m.group(0)
            var_name = m.group('var_name')
            if var_name not in var_names:
                var_names.append(var_name)
            elif var_name in self:
                var_names.append(var_name)
                var_chain = ' -> '.join(var_names)
                raise RecursionError('circle reference variables detected: %s' % var_chain)
            replace = self.get(var_name, complete_str)
            if var_name in self:
                replace = self._wrap_string(str(replace), var_names)
            var_names.pop(-1)
            return str(replace)
        return VAR_RE.sub(repl, s)

    def eval(self, s):
        try:
            return json.loads(s)
        except:
            try:
                return literal_eval(s)
            except:
                return s

    def wrap_string(self, s, var_names=None):
        var_names = [] if var_names is None else var_names
        if (m := VAR_RE.fullmatch(s)):
            var_name = m.group('var_name')
            if var_name in self or re.fullmatch(r'__mock_\w+__', var_name):
                if var_name in var_names:
                    var_names.append(var_name)
                    var_chain = ' -> '.join(var_names)
                    raise RecursionError('circle reference variables detected: %s' % var_chain)
                var_names.append(var_name)
                o = object()
                value = self.get(var_name, o)
                if value is o:
                    return s
                if isinstance(value, str):
                    return self.wrap_string(value, var_names)
                return value
            else:
                value = self.eval(var_name)
                if value == var_name:
                    return s
                else:
                    return value
        return self._wrap_string(s, var_names)
    
    def get(self, key, default=None):
        if not re.fullmatch(r'__mock_\w+__', key):
            return super().get(key, default)
        name = key[7:-2]
        mock_function = getattr(BultinMock, name, None)
        if mock_function is None:
            return default
        return mock_function()

class Context(BaseContext):
    task_run = None
    task_run_case = None
    task_run_case_detail = None
    task_params = {}

    RUNNING_KEY = '__running__'
    CLIENT_KEY = '__api_client__'

    def start_run(self):
        # 不要外部调用
        self.set_global(self.RUNNING_KEY, 'running')

    def stop_run(self):
        # 不要外部调用
        self.set_global(self.RUNNING_KEY, 'stop')

    def pause_run(self):
        # 不要外部调用
        self.set_global(self.RUNNING_KEY, 'paused')

    @property
    def paused(self):
        return self.get(self.RUNNING_KEY)=='paused'

    @property
    def running(self):
        return self.get(self.RUNNING_KEY)=='running'

    @classmethod
    async def from_environment(cls, env_id): 
        from blueprints.project.models import EnvironmentDetail
        env_details = await EnvironmentDetail.filter(environment_id=env_id).all()
        env_dict = {}
        for detail in env_details:
            try:
                value = json.loads(detail.value)
            except:
                value = detail.value
            env_dict[detail.key] = value
        return cls(env_dict)

    @classmethod
    async def from_env_content(cls, env_content):
        env_content = ensure_json(env_content)
        return cls(env_content)

    def get_logger(self): # for logging of task
        logger = logging.getLogger(Config.TASKRUNNER_LOGGER_NAME)
        logger_adapter = TestrunnerLoggerAdapter(logger, extra={
            'task_run_id': self.task_run and self.task_run.id or None,
            'task_runcase_id': self.task_run_case and self.task_run_case.id or None,
            'task_runcase_detail_id': self.task_run_case_detail and self.task_run_case_detail.id or None
        })
        return logger_adapter

    def get_http_config(self):
        '''
        help in https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession
        '''
        items = {'cookies', 'headers', 'skip_auto_headers',
            'version', 'read_timeout', 'conn_timeout', 'timeout',
            'auto_decompress', 'trust_env', 'requote_redirect_url',
            'read_bufsize'}
        config = {}
        for k, v in self.items():
            k = k.lower()
            if not k.startswith('http_'):
                continue
            k = k[5:]
            if k not in items:
                continue
            try:
                v = json.loads(v)
            except:
                pass
            config[k] = v
        return config


    def get_client(self): # for api test
        if self.CLIENT_KEY in self:
            return self[self.CLIENT_KEY]
        config = self.get_http_config()
        client = ClientSession(**config)
        self[self.CLIENT_KEY] = client
        return client

    def set_client(self, client):
        self[self.CLIENT_KEY] = client

    async def release(self):  # release api test
        if self.CLIENT_KEY in self:
            await self[self.CLIENT_KEY].close()

    def get_driver(self): # for ui test
        pass
    
    @classmethod
    async def from_task_run(cls, task_run):
        obj = await cls.from_env_content(task_run.env_content)
        obj.task_run = task_run
        obj.task_params = task_run.extra_params
        return obj
    
    def set_task_run(self, task_run):
        self.task_run = task_run

    def set_run_case(self, run_case):
        self.task_run_case = run_case
    
    def iter_num(self):
        return self.task_run_case.iter_num

    def set_run_case_detail(self, run_case_detail):
        self.task_run_case_detail = run_case_detail

    def enter_run_case(self, run_case):
        data = run_case.data
        child = self.__class__(data.copy(), self)
        child.set_task_run(self.task_run)
        child.set_run_case(run_case)
        return child

if __name__ == '__main__':
    ctx = Context({'a': 1})
    print('ctx', ctx)
    with ctx.enter_run_case(1) as newCtx:
        ctx['abc'] = 123
        print(newCtx)
    print('ctx', ctx)
