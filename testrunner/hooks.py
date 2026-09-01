from blueprints.project.models import ProjectNotify
import json
from blueprints.task.models import Task, TaskRun, TaskRunCase, TaskRunCaseDetail, TaskRunLock
from tortoise.expressions import F
from datetime import datetime
from utils.dingding import Dingding

async def before_task_run(ctx):
    ctx.start_run()
    logger = ctx.get_logger()
    task_run = ctx.task_run
    logger.info('开始执行任务[%d]，执行编号[%d]', task_run.task_id, task_run.id)
    ctx.task_run = await task_run.update(status=TaskRun.TaskStatus.RUNNING, startAt=datetime.now())

async def after_task_run(ctx, rslt):
    from .runner import Result
    task_run = ctx.task_run
    status = TaskRun.TaskStatus.COMPLETED if  rslt.result != Result.ERROR else TaskRun.TaskStatus.ERROR
    if rslt.result == Result.STOPPED:
        status = TaskRun.TaskStatus.STOPPED
    ctx.task_run = await task_run.update(status=status, endAt=datetime.now())
    task_id = task_run.task_id
    env_id = task_run.env_id
    await TaskRunLock.filter(task_id=task_id, env_id=env_id).delete()
    logger = ctx.get_logger()
    try:
        task_run = await TaskRun.get(pk=task_run.id)
        task = await Task.get(pk=task_run.task_id)
        project_notify = await ProjectNotify.get(project_id=task.project_id)
        ding = Dingding(project_notify)
        await ding.send_dingding_notify(task_run)
    except:
        logger.exception('钉钉推送失败')
    logger.info('任务执行完成。')

async def before_case_run(ctx):
    task_run_case = ctx.task_run_case
    ctx.task_run_case = await task_run_case.update(status=TaskRunCase.Status.RUNNING, startAt=datetime.now())

async def after_case_run(ctx, rslt):
    from .runner import Result
    task_run_case = ctx.task_run_case
    status = TaskRunCase.Status.COMPLETED if  rslt.result != Result.ERROR else TaskRunCase.Status.ERROR
    if rslt.result == Result.STOPPED:
        status = TaskRunCase.Status.STOPPED
    now = datetime.now()
    await task_run_case.update(status=status, endAt=now, result=rslt.result, message=rslt.message)
    task_run = ctx.task_run
    if rslt.result != Result.STOPPED:
        keys = ['pass', 'failed', 'error', 'skip']
        field = '%s_num' % keys[rslt.result - 1]
        kw = {field: F(field) + 1}
        await TaskRun.filter(pk=task_run.id).update(**kw)
    await ctx.release()  # 回收ctx中的ClientSession

async def before_case_detail(ctx):
    task_run_case_detail = ctx.task_run_case_detail
    ctx.task_run_case_detail = await task_run_case_detail.update(status=TaskRunCaseDetail.Status.RUNNING, startAt=datetime.now())

async def after_case_detail(ctx, rslt):
    from .runner import Result
    task_run_case_detail = ctx.task_run_case_detail
    status = TaskRunCaseDetail.Status.COMPLETED if  rslt.result != Result.ERROR else TaskRunCaseDetail.Status.ERROR
    if rslt.result == Result.STOPPED:
        status = TaskRunCaseDetail.Status.STOPPED
    now = datetime.now()
    ctx.task_run_case_detail = await task_run_case_detail.update(status=status, endAt=now, result=rslt.result, result_detail=json.loads(rslt.to_json()))

