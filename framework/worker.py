import asyncio
import json, pickle
import logging
# from aioredis.pubsub import Receiver
from aioredis.exceptions import ConnectionError
import aioredis
from utils import to_str
from inspect import isawaitable
from sanic.log import error_logger as logger

class BaseWorker:
    def __init__(self, currency):
        self.currency = currency
        self._running = False
        self._task = None

    @property
    def running(self):
        return self._running

    async def iter_task(self):
        """
        异步迭代器
        """
        raise NotImplementedError

    async def publish(self, key, task):
        raise NotImplementedError
    
    async def stop(self):
        self._running = False
    
    def get_handler(self, task):
        raise NotImplementedError
    
    async def _run(self):
        tasks = set()
        async for task in self.iter_task():
            handler = self.get_handler(task)
            try:
                tasks.add(asyncio.ensure_future(handler(*task)))
            except Exception as ex:
                logger.exception(ex)
            if len(tasks) >= self.currency:
                done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    try:
                        await t
                    except Exception as ex:
                        logger.exception(ex)

    async def run(self):
        self._running = True
        async def daemon():
            while self._running:
                await asyncio.sleep(1)
            print('stop worker')
        self._task = asyncio.create_task(self._run())
        tasks = [asyncio.create_task(daemon()), self._task]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            try:
                await t
            except Exception as ex:
                logger.exception(ex)
        for p in pending:
            p.cancel()
        self._running = False

# class RedisChannelWorker(BaseWorker):
#     def __init__(self, currency, redis, channel_names=None, channel_patterns=None):
#         super().__init__(currency)
#         self.redis = redis
#         self.q = asyncio.Queue()
#         if isinstance(channel_names, str) and channel_names:
#             channel_names = [channel_names]
#         if isinstance(channel_patterns, str) and channel_patterns:
#             channel_patterns = [channel_patterns]
#         self.channel_names = channel_names
#         self.channel_patterns = channel_patterns
#         self.handler_map = {}
    
#     def get_handler(self, task):
#         _, channel_name = task
#         return self.handler_map.get(channel_name)
    
#     def register(self, key, func=None):
#         key = to_str(key)
#         if func is not None:
#             self.handler_map[key] = func
#             return
#         def wrapper(func):
#             self.handler_map[key] = func
#             return func
#         return wrapper

#     async def producer(self):
#         channel_names = self.channel_names or []
#         channel_patterns = self.channel_patterns or []
#         if not channel_names and not channel_patterns:
#             return
#         mpsc = Receiver()
#         if channel_names:
#             channels = [mpsc.channel(c) for c in channel_names]
#             await self.redis.subscribe(*channels)
#         if channel_patterns:
#             tasks = set()
#             for p in channel_patterns:
#                 tasks.add(self.redis.psubscribe(mpsc.pattern(p)))
#             if tasks:
#                 await asyncio.wait(tasks)
#         try:
#             await self.receiver_reader(mpsc)
#         finally:
#             if channel_names:
#                 await self.redis.unsubscribe(*channel_names)
#             if channel_patterns:
#                 tasks = set()
#                 for p in channel_patterns:
#                     tasks.add(self.redis.punsubscribe(p))
#                 await asyncio.wait(tasks)
#             mpsc.stop()

#     async def receiver_reader(self, receiver):
#         async for channel, msg in receiver.iter():
#             await self.q.put((msg, channel))

#     async def iter_task(self):
#         """
#         异步迭代器
#         """
#         while True:
#             yield self.q.get()
    
#     def run(self):
#         asyncio.ensure_future(self.producer())
#         return super().run()

#     async def publish(self, key, task, serializer=pickle):
#         if isinstance(task, (list, tuple, dict)):
#             task = serializer.dumps(task)
#         await self.redis.publish(key, task)

class RedisListWorker(BaseWorker):
    def __init__(self, currency, redis):
        super().__init__(currency)
        self.redis = redis
        self.handler_map = {}

    async def iter_task(self):
        if not self.handler_map:
            return
        while True:
            list_keys = list(self.handler_map)
            try:
                ret = await self.redis.blpop(list_keys, timeout=1)
                if ret is None:
                    await asyncio.sleep(0)
                    continue
                key, msg = ret
            except ConnectionError:
                break
            yield (msg, key)

    async def publish(self, key, task, serializer=pickle):
        if isinstance(task, (list, tuple, dict)):
            task = serializer.dumps(task)
        await self.redis.rpush(key, task)

    def get_handler(self, task):
        _, key = task
        return self.handler_map.get(to_str(key))

    def _register(self, key, func=None):
        key = to_str(key)
        if func is not None:
            self.handler_map[key] = func
            return
        def wrapper(func):
            self.handler_map[key] = func
            return func
        return wrapper
    
    def register(self, key, func=None):
        return self._register(key, func=func)

class BaseHandler:
    async def __call__(self, msg, key):
        pass

class BasePickleHandler(BaseHandler):
    async def __call__(self, msg, key):
        msg = pickle.loads(msg)
        cmd = msg.get('cmd')
        if cmd:
            msg.pop('cmd')
            attr = getattr(self, cmd, lambda *x:x)
            ret = attr(msg)
            if isawaitable(ret):
                await ret

class BaseJsonHandler(BaseHandler):
    async def __call__(self, msg, key):
        msg = json.loads(to_str(msg))
        cmd = msg.get('cmd')
        if cmd:
            msg.pop('cmd')
            attr = getattr(self, cmd, lambda *x:x)
            ret = attr(msg)
            if isawaitable(ret):
                await ret

if __name__ == '__main__':
    pass