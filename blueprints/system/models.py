from framework import models
from tortoise import fields

class SchedulerLock(models.Model):  # 保证在多worker的环境下apscheduler的单例
    name = fields.CharField(max_length=5, unique=True)

    @classmethod
    async def get(cls):
        try:
            return await cls.create(name='lock')
        except:
            pass