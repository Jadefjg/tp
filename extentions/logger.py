from framework.worker import BaseHandler, RedisListWorker
from config import Config
import logging, asyncio, json
from logging import LogRecord
from utils import default, to_str
from datetime import datetime
from .redis import get_redis

class RedisHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET, queue_name=''):
        super().__init__(level)
        self._queue_name = queue_name
        self._tasks = set()

    async def _emit(self, msg):
        redis = await get_redis()
        async with redis as r:
            await r.rpush(self._queue_name, msg)

    def emit(self, record: LogRecord) -> None:
        self.format(record)
        dic = record.__dict__
        message = json.dumps(dic, default=default)
        task = asyncio.ensure_future(self._emit(message))
        # loop = asyncio.get_event_loop()
        # task = loop.create_task(self._emit(message))
        task.add_done_callback(lambda fut: self._tasks.remove(fut))
        self._tasks.add(task)

class TestrunnerLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = self.extra.copy()
        extra.update(kwargs.get('extra', {}))
        kwargs['extra'] = extra
        return msg, kwargs

class LogWorkHandler(BaseHandler):
    async def __call__(self, msg, key):
        from blueprints.task.models import TaskRunLog
        assert to_str(key) == Config.REDIS_LOGGER_QUEUE
        msg = json.loads(msg)
        createAt = datetime.fromtimestamp(msg['created'])
        await TaskRunLog.create(
            taskrun_id=msg.get('task_run_id'),
            taskruncase_id=msg.get('task_runcase_id'),
            taskruncasedetail_id=msg.get('task_runcase_detail_id'),
            levelname=msg['levelname'],
            pathname=msg['pathname'],
            filename=msg['filename'],
            lineno=msg['lineno'],
            module=msg['module'],
            exc_text=msg['exc_text'],
            created=msg['created'],
            createAt=createAt,
            message=msg['message']
        )

def init_app(app):
    @app.listener('before_server_start')
    async def logger_at_start(app, loop):
        logger = logging.getLogger(Config.TASKRUNNER_LOGGER_NAME)
        logger.setLevel(Config.LOG_LEVEL)
        handler = RedisHandler(queue_name=Config.REDIS_LOGGER_QUEUE)
        handler.setLevel(Config.LOG_LEVEL)
        logger.addHandler(handler)
        logger.propagate = False
        logwork = RedisListWorker(1, app.ctx.redis)
        logwork.register(Config.REDIS_LOGGER_QUEUE, LogWorkHandler())
        app.add_task(logwork.run())

if __name__ == '__main__':
    from extentions.redis import get_redis
    import asyncio
    queue_name = 'logger:queue'

    async def main():
        logger = logging.getLogger('tp.testrunner')
        redis = await get_redis()
        logger.setLevel(0)
        handler = RedisHandler(redis=redis, queue_name=queue_name)
        handler.setLevel(0)
        logger.addHandler(handler)
        logger = TestrunnerLoggerAdapter(logger, extra={'task_run': 123})
        logger.error('this is error')
        try:
            raise ValueError('this is a value error')
        except:
            logger.exception('error')
        await asyncio.sleep(1)
    asyncio.run(main())