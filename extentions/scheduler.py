from framework.models import StatusEnum
from blueprints.task.models import TaskScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from blueprints.system.models import SchedulerLock
from config import Config
from framework.worker import RedisListWorker, BasePickleHandler
from utils import to_str
import json, pickle
from extentions.redis import get_redis
import asyncio
from sanic.log import logger
from blueprints.api.tasks import sync_all_project


# jobstores = {
#     'default': RedisJobStore(jobs_key=Config.TASK_SCHEDULED, run_times_key=Config.TASK_RUN_TIMES)
# }

class SchedulerHandler(BasePickleHandler):
    def __init__(self, scheduler: AsyncIOScheduler):
        self.scheduler = scheduler

    def add_job(self, msg):
        self.scheduler.add_job(**msg)

    def modify_job(self, msg):
        self.scheduler.modify_job(**msg)

    def reschedule_job(self, msg):
        print('rescheduling:', msg)
        self.scheduler.reschedule_job(**msg)

    def pause_job(self, msg):
        self.scheduler.pause_job(**msg)

    def resume_job(self, msg):
        self.scheduler.resume_job(**msg)

    def remove_job(self, msg):
        self.scheduler.remove_job(**msg)

    def remove_all_jobs(self, msg):
        self.scheduler.remove_all_jobs(**msg)

    async def get_job(self, msg):
        job = self.scheduler.get_job(**msg)
        redis = await get_redis()
        await redis.set(Config.JOB_RESULT.format(job_id=job.id), pickle.dumps(job), expire=5)

    async def get_jobs(self, msg):
        jobs = self.scheduler.get_jobs(**msg)
        redis = await get_redis()
        await redis.set(Config.JOBS_RESULT, pickle.dumps(jobs), expire=5)

def create_redis_future(key, interval=0.1, timeout=5):
    fut = asyncio.Future()
    async def handler():
        redis = await get_redis()
        for _ in range(int(timeout//interval)):
            r = await redis.get(key)
            if r:
                fut.set_result(pickle.loads(r))
                return
            await asyncio.sleep(interval)
        fut.set_exception(TimeoutError)
    asyncio.create_task(handler())
    return fut

def init_app(app):
    @app.listener('before_server_start')
    async def scheduler_at_start(app, loop):
        schedlock = await SchedulerLock.get()
        app.ctx.schedlock = schedlock
        worker = RedisListWorker(5, app.ctx.redis)

        async def get_jobs():
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'get_jobs'
            })

            fut = create_redis_future(Config.JOBS_RESULT)
            jobs = await fut
            return jobs
        
        async def get_job(job_id):
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'get_job',
                'job_id': job_id
            })
            fut = create_redis_future(Config.JOB_RESULT.format(job_id=job_id))
            job = await fut
            return job

        async def add_job(**kw):
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'add_job',
                **kw
            })

        async def modify_job(**kw):
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'modify_job',
                **kw
            })
        
        async def pause_job(**kw):
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'pause_job',
                **kw
            })
        
        async def resume_job(**kw):
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'resume_job',
                **kw
            })
        
        async def remove_job(**kw):
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'remove_job',
                **kw
            })

        async def remove_all_jobs(**kw):
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'remove_all_jobs',
                **kw
            })
        
        async def reschedule_job(**kw):
            await worker.publish(Config.SCHEDULE_QUEUE, {
                'cmd': 'reschedule_job',
                **kw
            })
        
        app.ctx.get_jobs = get_jobs
        app.ctx.get_job = get_job
        app.ctx.add_job = add_job
        app.ctx.modify_job = modify_job
        app.ctx.pause_job = pause_job
        app.ctx.resume_job = resume_job
        app.ctx.remove_job = remove_job
        app.ctx.remove_all_jobs = remove_all_jobs
        app.ctx.reschedule_job = reschedule_job
        
        if schedlock:
            sched = AsyncIOScheduler(timezone=Config.TIME_ZONE) # jobstores=jobstores
            sched.start()
            app.ctx.sched = sched
            worker.register(Config.SCHEDULE_QUEUE, SchedulerHandler(sched))
            # asyncio.create_task(worker.run())
            await add_all_jobs(sched)
            app.add_task(worker.run())
        else:
            logger.info('scheduler get lock failed')
        app.ctx.scheduler_worker = worker

    @app.listener('after_server_stop')
    async def scheduler_at_stop(app, loop):
        if app.ctx.schedlock:
            app.ctx.sched.shutdown()
            # await app.ctx.schedlock.delete()
        await SchedulerLock.all().delete()
        await app.ctx.scheduler_worker.stop()

async def add_all_jobs(shed: AsyncIOScheduler):
    from testrunner import trigger_scheduler
    logger.info('start add background jobs.')
    shed.remove_all_jobs()
    schedulers = await TaskScheduler.filter(status=StatusEnum.NORMAL).all()
    for obj in schedulers:
        kw = obj.get_scheduler_kwargs()
        shed.add_job(
            func=trigger_scheduler,
            kwargs={'task_scheduler_id': obj.id},
            id=str(obj.id),
            max_instances=1,
            replace_existing=True,
            **kw
        )
    shed.add_job(
        func=sync_all_project,
        id='sync_all_project',
        max_instances=1,
        replace_existing=True,
        trigger='cron',
        hour=0
    )
    # await sync_all_project()
    logger.info('all background jobs[%d] added.' % len(schedulers))