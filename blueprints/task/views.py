import logging

import json
from testrunner import trigger_scheduler
from config import Config
from functools import reduce
from tortoise.query_utils import Q
from blueprints.case.models import TestCase
from framework.api import BaseApi, WriteMixin, ReadMixin, DeleteMixin
from sanic import Request
from blueprints.project.models import Environment, Project
from .models import Task, TaskCase, TaskRun, TaskRunCase, TaskRunCaseDetail, TaskRunLock, TaskRunLog, TaskScheduler
from const import CommonResponse, ResponseCode
from framework.models import StatusEnum


class TaskView(BaseApi, WriteMixin, ReadMixin, DeleteMixin):
    model = Task
    search_fields = ('taskname', )
    
    @classmethod
    async def get_queryset(cls, request: Request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        ids = await Project.filter_by_user(user).values('id')
        ids = [item['id'] for item in ids]
        project_id = request.args.get('project_id')
        if project_id and int(project_id) in ids:
            qs = qs.filter(project_id=project_id)
        else:
            qs = qs.filter(project_id__in=ids)
        if not user.isAdmin:
            qs = qs.filter(status=StatusEnum.NORMAL)
        return qs

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        qs = qs.prefetch_related('createBy', 'project')
        total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        fields = cls.model._db_fields()
        items = await qs.values(*fields, createBy_name='createBy__username', project_name="project__name")
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': {
                'total': total,
                'items':[
                    cls.model.dic_to_json(item) for item in items
                ]
            }
        }, 200
    
    @classmethod
    async def get(cls, request, pk):
        qs = await cls.get_queryset(request, qs=None)
        _fields = cls.model._db_fields()
        obj = await qs.filter(pk=pk).values(
            *_fields,
            project_name="project__name",
            createBy_name='createBy__username'
        )
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': cls.model.dic_to_json(obj[0])
        }

    @classmethod
    async def post(cls, request): # create
        params = request.form or request.json
        params['createBy'] = request.ctx.user
        obj = await cls.model.create(**params)
        return {
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def delete(cls, request, pk=None):  # TODO 处理定时任务
        obj = await cls.get_object(request, pk)
        obj.status = StatusEnum.DELETED
        await obj.save(update_fields=('status',))
        return {
            'code': ResponseCode.OK,
            'message': '删除成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def get_testcase_for_select(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        project_id = obj.project_id
        qs = TestCase.filter(project_id=project_id, status=StatusEnum.NORMAL)
        if title := request.args.get('title'):
            qs = qs.filter(title__contains=title)
        _and = request.args.get('and', False)
        if tags := request.args.get('tags'):
            if isinstance(tags, str):
                tags = tags.split('|')
            q = [Q(tag__contains='"%s"'%tag) for tag in tags]
            filters = reduce(lambda x, y:  x|y if not _and else x&y, q )
            qs = qs.filter(filters)

        if min_priority := request.args.get('min_priority'):
            qs = qs.filter(priority__gte=min_priority)

        if max_priority := request.args.get('max_priority'):
            qs = qs.filter(priority__lte=max_priority)

        cases = await qs.order_by('title').all()
        return {
            "code": ResponseCode.OK,
            "data": [
                case.to_dict()
                for case in cases
            ]
        }
    
    @classmethod
    async def get_testcases(cls, request, pk=None):
        task = await cls.get_object(request, pk)
        taskcases = await task.taskcases.filter(status=TaskCase.Status.NORMAL).order_by('testcase__title').all()
        return {
            "code": ResponseCode.OK,
            "data": [
                taskcase.casecontent
                for taskcase in taskcases
            ]
        }

    @classmethod
    async def add_testcase(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        case_ids = request.json.get('case_ids')
        testcases = await TestCase.filter(id__in=case_ids).all()
        await obj.add_testcase(testcases)
        return {
            "code": ResponseCode.OK,
            "message": "用例更新成功"
        }

    @classmethod
    async def updatecases(cls, request, pk):
        task = await cls.get_object(request, pk)
        case_ids = await task.taskcases.filter(status=TaskCase.Status.NORMAL).values('testcase_id')
        case_ids = [item['testcase_id'] for item in case_ids]
        testcases = await TestCase.filter(id__in=case_ids, status=StatusEnum.NORMAL).all()
        await task.add_testcase(testcases)
        return {
            "code": ResponseCode.OK,
            "message": "用例更新成功"
        }

    @classmethod
    async def deletecase(cls, request, pk):
        params = request.json
        obj = await cls.get_object(request, pk)
        id = params.get('id')
        await obj.taskcases.filter(testcase_id=id).update(status=TaskCase.Status.OLD)
        return {
            "code": ResponseCode.OK,
            "message": "用例删除成功"
        }

    @classmethod
    async def add_scheduler(cls, request, pk):
        await cls.get_object(request, pk)
        params = request.form or request.json
        params['createBy'] = request.ctx.user
        params['task_id'] = pk
        obj = TaskScheduler(**params)
        await obj.save()
        app_ctx = request.app.ctx
        kw = obj.get_scheduler_kwargs()
        await app_ctx.add_job(
            func=trigger_scheduler,
            kwargs={'task_scheduler_id': obj.id},
            id=str(obj.id),
            max_instances=1,
            replace_existing=True,
            **kw
        )
        return {
            'code': ResponseCode.OK,
            'message': '创建成功',
            'data': obj.to_dict(cls.excludes_fields)
        }
    
    @classmethod
    async def execute(cls, request, pk=None):
        task = await cls.get_object(request, pk)
        env_id = request.json.get('env_id')
        try:
            await TaskRunLock.get(
                task_id=task.id,
                env_id=env_id
            )
        except:
            pass
        else:
            return {
                'code': ResponseCode.INVALID_STATE,
                'message': '该任务已经在该环境运行，请稍后重试。'
            }
        env = await Environment.get(pk=env_id)
        task_run = await TaskRun.create_task_run_from_task_and_env(pk, env, create_by=request.ctx.user)
        redis = request.app.ctx.redis
        await redis.rpush(Config.ALL_TASK_RUN_QUEUE_NAME, str(task_run.id))
        return {
                'code': ResponseCode.OK,
                'message': '提交成功'
            }

class TaskSchedulerView(BaseApi, ReadMixin, WriteMixin, DeleteMixin):
    model = TaskScheduler
    
    @classmethod
    async def get_queryset(cls, request: Request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        ids = await Project.filter_by_user(user).values('id')
        ids = [item['id'] for item in ids]
        project_id = request.args.get('project_id')
        if project_id and int(project_id) in ids:
            qs = qs.filter(task__project_id=project_id)
        else:
            qs = qs.filter(task__project_id__in=ids)
        return qs

    @classmethod
    async def getlist(cls, request):
        qs = await cls.get_queryset(request, qs=None)
        if task_id := request.args.get('task_id'):
            qs = qs.filter(task_id=task_id)
        else:
            raise ValueError("参数错误")
        total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        fields = cls.model._db_fields()
        items = await qs.values(*fields, createBy_name='createBy__username', env_name="env__name")
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': {
                'total': total,
                'items':[
                    cls.model.dic_to_json(item) for item in items
                ]
            }
        }, 200
    
    @classmethod
    async def delete(cls, request, pk):
        obj = await cls.get_object(request, pk)
        app_ctx = request.app.ctx
        await app_ctx.remove_job(job_id=str(pk))
        await obj.delete()
        return {
            'code': ResponseCode.OK,
            'message': '删除成功',
            'data': obj.to_dict(cls.excludes_fields)
        }, 200

    @classmethod
    async def post(cls, request):
        raise NotImplementedError
        # params = request.form or request.json
        # task_id = params.get('task_id')
        # await Task.get(pk=task_id)
        # params['createBy'] = request.ctx.user
        # obj = cls.model(**params)
        # await obj.save()
        # # TODO add job
        # return {
        #     'code': ResponseCode.OK,
        #     'message': '创建成功',
        #     'data': obj.to_dict(cls.excludes_fields)
        # }
    
    @classmethod
    async def patch(cls, request, pk):
        resp = await super().patch(request, pk=pk)
        obj = await cls.get_object(request, pk)
        app_ctx = request.app.ctx
        kw = obj.get_scheduler_kwargs()
        await app_ctx.reschedule_job(
            job_id=str(pk),
            **kw
        )
        return resp

    @classmethod
    async def pause(cls, request, pk):
        obj = await cls.get_object(request, pk)
        obj.status = TaskScheduler.Status.PAUSED
        await obj.save()
        app_ctx = request.app.ctx
        await app_ctx.pause_job(job_id=str(pk))
        return CommonResponse.OK

    @classmethod
    async def resume(cls, request, pk):
        obj = await cls.get_object(request, pk)
        obj.status = TaskScheduler.Status.NORMAL
        await obj.save()
        app_ctx = request.app.ctx
        await app_ctx.resume_job(job_id=str(pk))
        return CommonResponse.OK

    @classmethod
    async def trigger(cls, request, pk):
        from testrunner import trigger_scheduler
        user = request.ctx.user
        await cls.get_object(request, pk)
        rslt = await trigger_scheduler(pk, create_by=user)
        if rslt:
            return {
                'code': ResponseCode.OK,
                'message': '提交成功'
            }
        return {
            'code': ResponseCode.DUPLICATE_KEY,
            'message': '任务已经在该环境下执行'
        }

    @classmethod
    async def log(cls, request, pk):
        obj = await cls.get_object(request, pk)
        tsl = await obj.logs.all().order_by('-createAt')
        return {
            "code": ResponseCode.OK,
            "data": [
                item.to_dict()
                for item in tsl
            ]
        }

class TaskRunView(BaseApi, ReadMixin):
    model = TaskRun
    order_by = ('-createAt', )
    filter_fields = ('env_id', 'status')

    @classmethod
    async def get_queryset(cls, request: Request, qs=None):
        qs = await super().get_queryset(request, qs=qs)
        user = request.ctx.user
        ids = await Project.filter_by_user(user).values('id')
        ids = [item['id'] for item in ids]
        project_id = request.args.get('project_id')
        if project_id and int(project_id) in ids:
            qs = qs.filter(task__project_id=project_id)
        else:
            qs = qs.filter(task__project_id__in=ids)
        return qs

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        if taskname:= request.args.get('taskname'):
            qs = qs.filter(task__taskname__contains=taskname)
        if project_id := request.args.get('project_id'):
            qs = qs.filter(task__project_id=project_id)
        if env_id := request.args.get('env_id'):
            qs = qs.filter(env_id=env_id)
        total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        _fields = cls.model._db_fields()
        items = await qs.values(
            *_fields,
            project_name="task__project__name",
            taskname='task__taskname',
            env_name='env__name',
            createBy_name='createBy__username'
        )
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': {
                'total': total,
                'items': [
                    cls.model.dic_to_json(item) for item in items
                ]
            }
        }
    
    @classmethod
    async def get(cls, request, pk):
        qs = await cls.get_queryset(request, qs=None)
        _fields = cls.model._db_fields()
        obj = await qs.filter(pk=pk).values(
            *_fields,
            project_name="task__project__name",
            taskname='task__taskname',
            env_name='env__name',
            createBy_name='createBy__username'
        )
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': cls.model.dic_to_json(obj[0])
        }

    @classmethod
    async def pause(cls, request, pk):
        obj: TaskRun = await cls.get_object(request, pk)
        if obj.status != TaskRun.TaskStatus.RUNNING:
            return {
                'code': ResponseCode.INVALID_STATE,
                'message': '任务执行在当前状态下不能暂停。'
            }
        key = Config.TASK_RUN_CONTROL_CHANNEL.format(taskrunid=pk)
        await request.app.ctx.testrunner.publish(key, {
            'cmd': 'pause',
            'username': request.ctx.user.username
        }, serializer=json)
        await obj.update(status=TaskRun.TaskStatus.PAUSED)
        return {
            'code': ResponseCode.OK,
            'message': '操作成功'
        }
        
    @classmethod
    async def resume(cls, request, pk):
        obj = await cls.get_object(request, pk)
        if obj.status != TaskRun.TaskStatus.PAUSED:
            return {
                'code': ResponseCode.INVALID_STATE,
                'message': '任务执行在当前状态下不能继续。'
            }
        key = Config.TASK_RUN_CONTROL_CHANNEL.format(taskrunid=pk)
        await request.app.ctx.testrunner.publish(key, {
            'cmd': 'resume',
            'username': request.ctx.user.username
        }, serializer=json)
        await obj.update(status=TaskRun.TaskStatus.RUNNING)
        return {
            'code': ResponseCode.OK,
            'message': '操作成功'
        }

    @classmethod
    async def stop(cls, request, pk=None):
        obj = await cls.get_object(request, pk)
        force = request.json.get('force')
        if obj.status != TaskRun.TaskStatus.RUNNING:
            return {
                'code': ResponseCode.INVALID_STATE,
                'message': '任务执行在当前状态下不能停止。'
            }
        key = Config.TASK_RUN_CONTROL_CHANNEL.format(taskrunid=pk)
        await request.app.ctx.testrunner.publish(key, {
            'cmd': 'stop',
            'force': force,
            'username': request.ctx.user.username
        }, serializer=json)
        await obj.update(status=TaskRun.TaskStatus.STOPPED)
        return {
            'code': ResponseCode.OK,
            'message': '操作成功'
        }

    @classmethod
    async def rerun(cls, request, pk):
        obj = await cls.get_object(request, pk)
        # 这里只是简单校验
        try:
            await TaskRunLock.get(
                task_id = obj.task_id,
                env_id = obj.env_id
            )
        except:
            pass
        else:
            return {
                'code': ResponseCode.DUPLICATE_KEY,
                'message': '该任务已经在该环境中运行， 请等待任务完成后重试。'
            }
        task_run = await TaskRun.recreate_task_run(obj, create_by=request.ctx.user)
        redis = request.app.ctx.redis
        await redis.rpush(Config.ALL_TASK_RUN_QUEUE_NAME, str(task_run.id))
        return {
            'code': ResponseCode.OK,
            'message': '任务提交成功',
            'data': {
                'taskrun_id':task_run.id
            }
        }
    
    @classmethod
    async def delete(cls, request, pk=None):
        user = request.ctx.user
        if not user.isAdmin:
            return {
            'code': ResponseCode.FORBIDDEN,
            'message': '无权限操作'
        }
        task_run: TaskRun = await cls.get_object(request, pk)
        runcases = await task_run.cases
        runcase_ids = [runcase.id for runcase in runcases]
        await TaskRunCaseDetail.filter(task_run_case_id__in=runcase_ids).delete()
        await TaskRunCase.filter(id__in=runcase_ids).delete()
        await TaskRunLog.filter(taskrun_id=pk).delete()
        await task_run.delete()
        return {
            'code': ResponseCode.OK,
            'message': '删除成功'
        }

class TaskRunCaseView(BaseApi, ReadMixin):
    model = TaskRunCase
    filter_fields = ('task_run_id', 'result')
    order_by = ('task_case__testcase__title', )

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        total, qs = await cls.pagination_class().get_total_queryset(qs, request)
        _fields = cls.model._db_fields()
        items = await qs.prefetch_related('case_details', 'task_case').all()
        data = []
        for item in items:
            dic = item.to_dict()
            dic['casecontent'] = item.task_case.casecontent
            dic['details'] = [i.to_dict() for i in item.case_details]
            data.append(dic)
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': {
                'total': total,
                'items': data
            }
        }

class TaskRunCaseDetailView(BaseApi, ReadMixin):
    model = TaskRunCaseDetail
    filter_fields = ('task_run_case_id', )

class TaskRunLogView(BaseApi, ReadMixin):
    model = TaskRunLog
    filter_fields = ('taskrun_id', 'taskruncase_id', 'taskruncasedetail_id')
    order_by = ('createAt',)
    search_fields = ('message', )

    @classmethod
    async def getlist(cls, request, pk=None):
        qs = await cls.get_queryset(request, qs=None)
        if cls.pagination_class:
            total = await qs.count()
            data = await cls.pagination_class().get_queryset(qs, request).all()
            data = {
                'total': total,
                'items': [d.to_dict(cls.excludes_fields) for d in data]
            }
        else:
            data = await qs
            data = [d.to_dict(cls.excludes_fields) for d in data]
        return {
            'code': ResponseCode.OK,
            'message': '列表加载成功',
            'data': data
        }, 200
