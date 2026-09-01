from enum import Enum
from framework import models
from tortoise import fields

class HttpMethod(str, Enum):
    GET='GET'
    POST='POST'
    PUT='PUT'
    PATCH='PATCH'
    DELETE='DELETE'
    COPY='COPY'
    HEAD='HEAD'
    OPTIONS='OPTIONS'
    LINK='LINK'
    UNLINK='UNLINK'
    PURGE='PURGE'
    LOCK='LOCK'
    UNLOCK='UNLOCK'
    PROPFIND='PROPFIND'
    VIEW='VIEW'

class SyncSource(str, Enum):
    INLINE = 'inline'
    YAPI = 'yapi'

class RemoteProject(models.Model):
    project = fields.ForeignKeyField("models.Project", db_constraint=False)
    url = fields.CharField(512)
    remote_project_id = fields.IntField(null=True)
    remote_project_name = fields.CharField(100, null=True)
    source=fields.CharEnumField(SyncSource, default=SyncSource.YAPI)
    token = fields.CharField(128)
    status=fields.IntEnumField(models.StatusEnum, default=models.StatusEnum.NORMAL)
    create_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        unique_together=('project_id', 'remote_project_id', 'url')

class ApiCat(models.Model):
    project = fields.ForeignKeyField("models.Project", db_constraint=False)
    remote_project = fields.ForeignKeyField("models.RemoteProject", db_constraint=False, null=True)
    remote_cat_id = fields.IntField(null=True)
    name = fields.CharField(1000)
    source=fields.CharEnumField(SyncSource, default=SyncSource.INLINE, null=True)
    update_at = fields.DatetimeField(auto_now_add=True)
    create_at = fields.DatetimeField(auto_now_add=True)

class Api(models.Model):
    project = fields.ForeignKeyField("models.Project", db_constraint=False)
    api_cat = fields.ForeignKeyField("models.ApiCat", db_constraint=False)
    remote_api_id = fields.IntField(null=True)
    title = fields.CharField(100)
    method = fields.CharEnumField(HttpMethod)
    path = fields.CharField(300)
    tag = fields.JSONField(default=[])
    req_params = fields.JSONField(default=[])
    req_form = fields.JSONField(default=[])
    req_body_json_schema = fields.BooleanField(default=False)
    req_body_raw = fields.TextField(null=True)
    req_body_type = fields.CharField(20)
    req_headers = fields.JSONField(default=[])
    # req_cookies = fields.JSONField(default=[])

    res_body = fields.TextField()
    res_body_json_schema = fields.BooleanField(default=False)
    res_body_type = fields.CharField(20)

    desc = fields.TextField()
    markdown = fields.TextField()
    source=fields.CharEnumField(SyncSource, default=SyncSource.INLINE, null=True)
    status=fields.IntEnumField(models.StatusEnum, default=models.StatusEnum.NORMAL)
        
    update_at = fields.DatetimeField(auto_now_add=True)
    create_at = fields.DatetimeField(auto_now_add=True)
