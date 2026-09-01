from enum import Enum, unique
from tortoise import fields, BaseDBAsyncClient
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction
from framework import models
from tortoise.signals import post_save, pre_save
from typing import List, Optional, Type

import json

class Macro(models.Model):
    project = fields.ForeignKeyField("models.Project", db_constraint=False)
    name = fields.CharField(max_length=32)
    comment = fields.TextField()
    isCorotine = fields.BooleanField(default=False)
    code = fields.TextField()
    status = fields.IntEnumField(models.StatusEnum, default=models.StatusEnum.DISABLED)
    verifiedBy = fields.ForeignKeyField('models.User', db_constraint=False, null=True, related_name=False)
    verifiedAt = fields.DatetimeField(null=True)
    createBy = fields.ForeignKeyField('models.User', db_constraint=False, related_name="macros")
    createAt = fields.DatetimeField(auto_now_add=True)

    class Meta:
        unique_together=('project_id', 'name')

class TestCase(models.Model):
    title = fields.CharField(max_length=32)
    priority = fields.SmallIntField(default=3)
    tag = fields.CharField(max_length=200, null=True)
    description = fields.CharField(max_length=1000)
    status = fields.IntEnumField(models.StatusEnum, default=models.StatusEnum.NORMAL)
    data = fields.JSONField(default=[])
    project = fields.ForeignKeyField("models.Project", db_constraint=False, related_name='testcases')
    createBy = fields.ForeignKeyField('models.User', db_constraint=False, related_name='testcase')
    createAt = fields.DatetimeField(auto_now_add=True)

    details: fields.ReverseRelation['TestCaseDetail']

    class Meta:
        unique_together=('project_id', 'title')

    async def get_entry(self):
        return await self.details.filter(previous__id=None).get_or_none()
    
    async def get_details(self):
        details = await self.details.all()
        details = {detail.id: detail for detail in details}
        item = await self.get_entry()
        if not item:
            return []
        rslt = [item]
        while next_id := item.next_id:
            item = details.get(next_id)
            if item is None:
                break
            rslt.append(item)
        return rslt

    async def save_details(self, details):
        if not details:
            return
        detail_objects = []
        for detail in details:
            if 'id' in detail:
                del detail['id']
            if 'next_id' in detail:
                del detail['next_id']
            detail['testcase_id'] = self.id
            detail_objects.append(TestCaseDetail(**detail))
        await TestCaseDetail.bulk_create(detail_objects)
        details = await self.details.all()
        if len(details) == 1:
            return
        sig, details = details[0], details[1:]
        for detail in details:
            sig.next_id = detail.id
            await sig.save(update_fields=('next_id',))
            sig = detail

class TestTag(models.Model):
    project = fields.ForeignKeyField('models.Project', db_constraint=False)
    title = fields.CharField(max_length=30)

    class Meta:
        unique_together=('project_id', 'title')

@post_save(TestCase)
async def save_tag(
    sender: "Type[TestCase]",
    instance: TestCase,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str],
) -> None:
    if created or 'tag' in update_fields:
        tag = instance.tag
        if tag:
            tags = json.loads(tag)
            for tag in tags:
                try:
                    await TestTag.create(title=tag, project_id=instance.project_id)
                except:
                    pass

class TestCaseDetail(models.Model):
    class Classify(str, Enum):
        UI = 'ui'
        API = 'api'
        RAW = 'raw'
        MACRO = 'macro'

    testcase = fields.ForeignKeyField('models.TestCase', db_constraint=False, related_name='details')
    title = fields.CharField(max_length=50)
    classify = fields.CharEnumField(Classify, default=Classify.UI)
    comment = fields.CharField(max_length=1000, null=True)
    content = fields.TextField(null=True)
    next = fields.ForeignKeyField('models.TestCaseDetail', db_constraint=False, related_name="previous", null=True)
    previous: fields.ReverseRelation['TestCaseDetail']

    async def move_to(self, target_id):
        if target_id == self.id:
            return
        cls = self.__class__
        async with in_transaction():
            await cls.filter(testcase_id=self.testcase_id, next_id=self.id).update(next_id=self.next_id)
            await cls.filter(testcase_id=self.testcase_id, next_id=target_id).update(next_id=self.id)
            await self.update(next_id=target_id)

    async def delete(self):
        cls = self.__class__
        async with in_transaction():
            await cls.filter(testcase_id=self.testcase_id, next_id=self.id).update(next_id=self.next_id)
            return await super().delete()

class File(models.Model):
    class Classify(str, Enum):
        DIR = 'dir'
        FILE = 'file'

    project = fields.ForeignKeyField("models.Project", db_constraint=False, related_name='files')
    name = fields.CharField(max_length=50)
    full_name = fields.CharField(max_length=100)
    classify = fields.CharEnumField(Classify, default=Classify.DIR)
    path = fields.CharField(max_length=200, null=True)
    size = fields.IntField(default=0)
    parent = fields.ForeignKeyField("models.File", db_constraint=False, related_name='children', null=True)
    createBy = fields.ForeignKeyField('models.User', db_constraint=False, related_name='files')
    createAt = fields.DatetimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project_id', 'full_name')

@pre_save(File)
async def signal_pre_save(
    sender: "Type[File]", instance: File, using_db, update_fields
) -> None:
    if instance.parent_id is None:
        instance.full_name = instance.name
    else:
        parent = await File.get(pk=instance.parent_id)
        instance.full_name = parent.full_name.rstrip('/') + '/' + instance.name.rstrip('/')
        instance.projet_id = parent.project_id