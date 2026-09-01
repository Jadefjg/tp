import asyncio
from blueprints.task.models import (TaskRun, TaskRunLock, TaskScheduler,
                                    TaskSchedulerLog)
from config import Config
from extentions.redis import get_redis
from framework.worker import RedisListWorker, BaseJsonHandler

from .context import Context
from .runner import TaskRunner


async def trigger_scheduler(task_scheduler_id, create_by=None):
    way = '手工' if create_by else '定时器'
    creator = create_by.username if create_by else '定时器[%s]' % task_scheduler_id
    await TaskSchedulerLog.create(task_scheduler_id=task_scheduler_id, message="开始调度，方式【%s】,创建人【%s】" % (way, creator))
    task_scheduler = await TaskScheduler.get(pk=task_scheduler_id)
    try:
        await TaskRunLock.get(
            task_id = task_scheduler.task_id,
            env_id = task_scheduler.env_id
        )
    except:
        pass
    else:
        await TaskSchedulerLog.create(task_scheduler_id=task_scheduler_id, message="调度失败，该任务已经在该环境下运行。")
        return False
    await TaskSchedulerLog.create(task_scheduler_id=task_scheduler_id, message="初始化任务。")
    task_run = await TaskRun.create_task_run(task_scheduler, create_by)
    await TaskSchedulerLog.create(task_scheduler_id=task_scheduler_id, message="初始化任务完成，任务执行编号为[%s]" % task_run.id)
    redis = await get_redis()
    await redis.rpush(Config.ALL_TASK_RUN_QUEUE_NAME, str(task_run.id))
    await TaskSchedulerLog.create(task_scheduler_id=task_scheduler_id, message="任务调度成功")
    return True

async def run_task_run(task_run_id):
    task_run = await TaskRun.get(pk=task_run_id)
    assert task_run.status == 1, '该任务已经开始执行或者还没有初始化完成'
    ctx = await Context.from_task_run(task_run)
    logger = ctx.get_logger()
    try:
        await TaskRunLock.create(
            task_id = task_run.task_id,
            env_id = task_run.env_id
        )
    except:
        logger.error('该任务已经在该环境下运行，请稍后重新启动该任务执行')
        return
    task = asyncio.ensure_future(TaskRunner(ctx).run())
    redis = await get_redis()
    worker = TaskRunControlWorker(1, redis)
    
    def cb(fut: asyncio.Future):
        asyncio.ensure_future(worker.stop())
        if (ex := fut.exception()):
            raise ex

    task.add_done_callback(lambda x: cb)
    key = Config.TASK_RUN_CONTROL_CHANNEL.format(taskrunid=task_run_id)
    worker.register(key, TaskRunControlHandler(ctx, task))
    await worker.run()

class TaskRunControlHandler(BaseJsonHandler):
    def __init__(self, ctx: Context, task: asyncio.Task):
        self._ctx = ctx
        self._task = task
        self.logger = self._ctx.get_logger()

    async def pause(self, msg):
        self._ctx.pause_run()
        self.logger.info('任务执行【%s】被【%s】暂停', self._ctx.task_run.id, msg.get('username', '未知'))

    async def stop(self, msg):
        force = msg.get('force')
        if not force:
            self._ctx.stop_run()
            await self._task
        else:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info('任务执行【%s】被【%s】停止', self._ctx.task_run.id, msg.get('username', '未知'))

    async def resume(self, msg):
        self._ctx.start_run()
        self.logger.info('【%s】继续了任务执行【%s】', msg.get('username', '未知'), self._ctx.task_run.id)

class TaskRunControlWorker(RedisListWorker):
    pass
