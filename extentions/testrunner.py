from utils import to_str
from config import Config
from framework.worker import RedisListWorker
from sanic.log import logger

async def to_run_task_run(msg, key):
    from testrunner import run_task_run
    logger.debug('got a task to run %s', msg)
    msg = to_str(msg)
    try:
        await run_task_run(msg)
    except:
        logger.exception()

def init_app(app):
    @app.listener('before_server_start')
    async def runner_at_start(app, loop):
        worker = RedisListWorker(Config.RUNNER_PER_WORKER, app.ctx.redis)
        worker.register(Config.ALL_TASK_RUN_QUEUE_NAME, to_run_task_run)
        app.add_task(worker.run())
        app.ctx.testrunner = worker

    @app.listener('after_server_stop')
    async def runner_at_stop(app, loop):
        await app.ctx.testrunner.stop()