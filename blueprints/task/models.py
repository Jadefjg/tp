from blueprints.project.models import Environment
from enum import IntEnum, Enum
from framework import models
from tortoise import fields
from framework.models import StatusEnum
from apscheduler.triggers.cron import CronTrigger

class Task(models.Model):
    project = fields.ForeignKeyField('models.Project', db_constraint=False, related_name='tasks')
    taskname = fields.CharField(30)
    comment = fields.CharField(1000)
    status = fields.IntEnumField(StatusEnum, default=StatusEnum.NORMAL)
    createAt = fields.DatetimeField(auto_now_add=True)
    createBy = fields.ForeignKeyField('models.User', db_constraint=False)

    class Meta:
        unique_together = ('project_id', 'taskname')

    async def add_testcase(self, testcases):
        await TaskCase.filter(task=self).update(status=TaskCase.Status.OLD)
        taskcases = []
        for testcase in testcases:
            details = await testcase.get_details()
            details = [detail.to_dict() for detail in details]
            casecontent = testcase.to_dict()
            casecontent['details'] = details
            taskcases.append(TaskCase(
                task=self,
                testcase=testcase,
                casecontent=casecontent
            ))
        await TaskCase.bulk_create(taskcases)

class TaskScheduler(models.Model):
    class Trigger(str, Enum):
        INTERVAL = 'interval'
        CRON = 'cron'
        DATE = 'date'

    class Status(IntEnum):
        PAUSED, NORMAL = range(2)

    task = fields.ForeignKeyField("models.Task", db_constraint=False, related_name='schedulers')
    env = fields.ForeignKeyField("models.Environment", db_constraint=False)
    extra_params = fields.JSONField(default=lambda: {}) # 额外参数，便于扩展
    trigger = fields.CharEnumField(Trigger)
    trigger_params = fields.JSONField() # json of trigger params
    status = fields.IntEnumField(Status, default=Status.NORMAL)
    createAt = fields.DatetimeField(auto_now_add=True)
    createBy = fields.ForeignKeyField('models.User', db_constraint=False)

    def get_scheduler_kwargs(self):
        kwargs = {
            'trigger': self.trigger
        }
        params = self.trigger_params
        if self.trigger == self.Trigger.INTERVAL:
            kwargs[params['unit']]=params['num']
        elif self.trigger == self.Trigger.DATE:
            kwargs['run_date'] = params['run_date']
        elif self.trigger == self.Trigger.CRON:
            if params.get('expert'):
                kwargs.update(trigger=CronTrigger.from_crontab(params['cron_str']))
            else:
                for k, v in params.items():
                    if k == 'expert':
                        continue
                    if k in ['hour', 'minute', 'second'] or v:
                        kwargs.update(k, v)
        if datetime_range := params.get('datetime_range'):
            start_date, end_date = datetime_range
            kwargs.update(start_date=start_date, end_date=end_date)
        return kwargs

class TaskSchedulerLog(models.Model):
    task_scheduler = fields.ForeignKeyField("models.TaskScheduler", db_constraint=False, related_name="logs")
    message = fields.CharField(1000)
    createAt = fields.DatetimeField(auto_now_add=True)

class TaskCase(models.Model): # 任务选择的用例副本
    class Status(IntEnum):
        OLD, NORMAL = range(2)

    task = fields.ForeignKeyField("models.Task", db_constraint=False, related_name='taskcases')
    testcase = fields.ForeignKeyField('models.TestCase', db_constraint=False, related_name='tasks')
    casecontent = fields.JSONField()
    # 每次重新选择的时候才会更新， 这样能保存测试执行的过程中不会影响正在执行的测试任务
    status = fields.IntEnumField(Status, default=Status.NORMAL)
    # 更新的过程是先全部设置成旧的，然后重新添加新的，添加新的时候重新保存测试用例副本
    createAt = fields.DatetimeField(auto_now_add=True)

class TaskRunLock(models.Model):
    task = fields.ForeignKeyField("models.Task", db_constraint=False, related_name='taskrunlock')
    env = fields.ForeignKeyField("models.Environment", db_constraint=False)
    createAt = fields.DatetimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task_id', 'env_id')

class TaskRun(models.Model):
    class TaskStatus(IntEnum):
        CREATED = 0
        INITED = 1
        RUNNING = 2
        PAUSED = 3
        ERROR = 4
        COMPLETED = 5
        STOPPED = 6
    
    class Result(IntEnum):
        PASS = 1
        FAILED = 2
        ERROR = 3

    task = fields.ForeignKeyField("models.Task", db_constraint=False, related_name='taskrun')
    env = fields.ForeignKeyField("models.Environment", db_constraint=False)
    env_content = fields.JSONField()
    extra_params = fields.JSONField(default=lambda: {}) # 额外参数，便于扩展
    scheduler = fields.ForeignKeyField("models.TaskScheduler", db_constraint=False, related_name="taskruns", null=True)
    status = fields.IntEnumField(TaskStatus, default=TaskStatus.CREATED)
    total_num = fields.IntField(default=0)
    pass_num = fields.IntField(default=0)
    failed_num = fields.IntField(default=0)
    error_num = fields.IntField(default=0)
    skip_num = fields.IntField(default=0)
    startAt = fields.DatetimeField(null=True)
    endAt = fields.DatetimeField(null=True)
    createAt = fields.DatetimeField(auto_now_add=True)
    createBy = fields.ForeignKeyField('models.User', db_constraint=False, null=True)

    @classmethod
    async def create_task_run_from_task_and_env(cls, task_id, env, scheduler=None, create_by=None):
        task_cases = await TaskCase.filter(task_id=task_id).filter(status=TaskCase.Status.NORMAL).prefetch_related('testcase').all()
        task_run = await cls.create(
            task_id=task_id,
            env_id=env.id,
            env_content=await env.get_details(),
            extra_params=scheduler.extra_params if scheduler else {},
            scheduler=None if create_by else scheduler,
            createBy=create_by
        )
        task_run_case_details = []
        for task_case in task_cases:
            data = task_case.casecontent['data']
            if not data:
                data = [{}]
            for i, d in enumerate(data):
                task_run.total_num += 1
                casecontent = task_case.casecontent
                task_run_case = TaskRunCase(
                    task_run=task_run,
                    task_case=task_case,
                    data=d,
                    iter_num=i
                )
                await task_run_case.save()
                for case_detail in casecontent['details']:
                    task_run_case_detail = TaskRunCaseDetail(
                        task_run_case=task_run_case,
                        case_detail_content=case_detail,
                    )
                    task_run_case_details.append(task_run_case_detail)
        await TaskRunCaseDetail.bulk_create(task_run_case_details)
        task_run.status = cls.TaskStatus.INITED
        await task_run.save(update_fields=('status', 'total_num'))
        return task_run

    @classmethod
    async def recreate_task_run(cls, task_run, create_by):
        task_id = task_run.task_id
        env = await Environment.get(id=task_run.env_id)
        return await cls.create_task_run_from_task_and_env(task_id, env, None, create_by=create_by)

    @classmethod
    async def create_task_run(cls, task_scheduler, create_by=None):
        task_id = task_scheduler.task_id
        env = await Environment.get(id=task_scheduler.env_id)
        return await cls.create_task_run_from_task_and_env(task_id, env, task_scheduler, create_by=create_by)


class TaskRunCase(models.Model):
    class Status(IntEnum):
        CREATED = 0
        RUNNING = 1
        COMPLETED = 2
        ERROR = 3
        STOPPED = 4

    class Result(IntEnum):
        NOT_RUN = 0
        PASS = 1
        FAILED = 2
        ERROR = 3
        SKIPPED = 4
        STOPPED = 5

    task_run = fields.ForeignKeyField('models.TaskRun', db_constraint=False, related_name="cases")
    task_case = fields.ForeignKeyField('models.TaskCase', db_constraint=False)
    data = fields.JSONField(default={})
    iter_num = fields.IntField(default=0) # data在数据中的序号
    status = fields.IntEnumField(Status, default=Status.CREATED)
    result = fields.IntEnumField(Result, default=Result.NOT_RUN)
    message = fields.TextField(null=True)
    startAt = fields.DatetimeField(null=True)
    endAt = fields.DatetimeField(null=True)

class TaskRunCaseDetail(models.Model):
    class Status(IntEnum):
        CREATED = 0
        RUNNING = 1
        COMPLETED = 2
        ERROR = 3
        STOPPED = 4

    class Result(IntEnum):
        NOT_RUN = 0
        PASS = 1
        FAILED = 2
        ERROR = 3
        SKIPPED = 4
        STOPPED = 5

    task_run_case = fields.ForeignKeyField('models.TaskRunCase', db_constraint=False, related_name="case_details")
    case_detail_content = fields.JSONField()
    status = fields.IntEnumField(Status, default=Status.CREATED)
    result = fields.IntEnumField(Result, default=Result.NOT_RUN)
    result_detail = fields.JSONField(default={})
    startAt = fields.DatetimeField(null=True)
    endAt = fields.DatetimeField(null=True)

class TaskRunLog(models.Model):
    taskrun = fields.ForeignKeyField('models.TaskRun', db_constraint=False, related_name="logs")
    taskruncase = fields.ForeignKeyField('models.TaskRunCase', db_constraint=False, null=True)
    taskruncasedetail = fields.ForeignKeyField('models.TaskRunCaseDetail', db_constraint=False, null=True)
    levelname = fields.CharField(10)
    pathname = fields.CharField(1024)
    filename = fields.CharField(64)
    lineno = fields.IntField()
    module = fields.CharField(32)
    exc_text = fields.TextField(null=True)
    created = fields.FloatField()
    createAt = fields.DatetimeField()
    message = fields.TextField()
