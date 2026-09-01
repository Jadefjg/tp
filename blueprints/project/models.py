from enum import Enum
from typing import List, Optional, Type
from tortoise import fields
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.signals import post_save
from framework import models
from tortoise.models import Q

class Project(models.Model):
    name = fields.CharField(max_length=32, unique=True)
    description = fields.CharField(max_length=1000)
    members = fields.ManyToManyField("models.User", db_constraint=False, related_name="projects")
    status = fields.SmallIntField(default=1)
    createAt = fields.DatetimeField(auto_now_add=True)
    createBy = fields.ForeignKeyField("models.User", db_constraint=False, related_name='-')

    @classmethod
    def filter_by_user(cls, user):
        if user.isAdmin:
            return cls.all()
        return cls.filter(status=1).filter(Q(members__id=user.id) | Q(createBy=user))

class NotifyClassify(str, Enum):
    DINGDING = 'dingding'

DEFAULT_REPORT_TEMPLATE = '''# 测试结果
本次测试完成。  
任务名称： %(task_name)s  
运行环境： %(env_name)s  
耗时： %(duration)s  
用例总数： %(total_num)d条  
通过： %(pass_num)d条  
失败： %(failed_num)s条  
跳过： %(skip_num)s条  
错误： %(error_num)s条  
通过率： %(pass_rate).2f%%  
详情：[测试报告](%(report_url)s)
'''

class ProjectNotify(models.Model):
    project = fields.OneToOneField("models.Project", db_constraint=False, related_name="notify")
    classify = fields.CharEnumField(NotifyClassify, default=NotifyClassify.DINGDING)
    access_token = fields.CharField(128, null=True)
    secret = fields.CharField(128, null=True)
    at_all = fields.BooleanField(default=False)
    at_mobile = fields.JSONField(default=[])
    report_template = fields.TextField(default=DEFAULT_REPORT_TEMPLATE)

@post_save(Project)
async def save_tag(
    sender: "Type[Project]",
    instance: Project,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str],
) -> None:
    if created:
        await ProjectNotify.create(project=instance)

class Environment(models.Model):
    name = fields.CharField(max_length=32)
    description = fields.CharField(max_length=1000)
    project = fields.ForeignKeyField("models.Project", db_constraint=False, related_name="envs")
    status = fields.SmallIntField(default=1)
    createAt = fields.DatetimeField(auto_now_add=True)
    createBy = fields.ForeignKeyField("models.User", db_constraint=False)

    class Meta:
        unique_together = ('name', 'project_id')

    async def get_details(self):
        details = await EnvironmentDetail.filter(environment=self).all()
        return {
            detail.key: detail.value
            for detail in details
        }

class EnvironmentDetail(models.Model):
    environment = fields.ForeignKeyField("models.Environment", db_constraint=False, related_name="details")
    key = fields.CharField(max_length=32)
    value = fields.CharField(max_length=1024)
    comment = fields.CharField(max_length=300, null=True, blank=True)

    class Meta:
        unique_together = ('environment_id', 'key')