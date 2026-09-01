from tortoise import models, fields, queryset
from datetime import datetime, timedelta
from enum import IntEnum

from tortoise.fields import relational

class StatusEnum(IntEnum):
    """
    0: 禁用; 1: 正常; 2: 已删除
    """
    DISABLED = 0
    NORMAL = 1
    DELETED = 2

class Model(models.Model):
    class Meta:
        abstract=True

    date_format = '%Y-%m-%d'
    datetime_format = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def _fields(cls):
        return list(cls._meta.fields)

    @classmethod
    def _db_fields(cls):
        return cls._meta.db_fields

    def to_dict(self, excludes=frozenset()):
        cls = self.__class__
        dic = {}
        for key in self._db_fields():
            if key in excludes:
                continue
            # cls_attr = getattr(cls, key)
            cls_attr = cls._meta.fields_map.get(key)
            inst_attr = getattr(self, key)
            if inst_attr is None:
                continue
            elif isinstance(cls_attr, fields.DateField):
                inst_attr = inst_attr.strftime(self.date_format)
            elif isinstance(cls_attr, fields.DatetimeField):
                inst_attr = inst_attr.strftime(self.datetime_format)
            elif isinstance(cls_attr, fields.TimeDeltaField):
                inst_attr = inst_attr.total_seconds
            elif isinstance(inst_attr, (int, str, list, dict, tuple)):
                pass
            elif isinstance(cls_attr, fields.relational.ForeignKeyFieldInstance):
                # key = key + '_id'
                # inst_attr = getattr(self, key)
                inst_attr = getattr(self, key)
                if isinstance(inst_attr, Model):
                    inst_attr = inst_attr.to_dict(excludes)
                else:
                    key = key + '_id'
                    inst_attr = getattr(self, key)
            elif isinstance(inst_attr, (fields.relational.ManyToManyFieldInstance, 
                    fields.relational.ReverseRelation,
                    queryset.QuerySet)):
                continue
            dic[key] = inst_attr
        return dic

    @classmethod
    def from_dict(cls, dic):
        for key in cls._fields():
            # cls_attr = getattr(cls, key)
            cls_attr = cls._meta.fields_map.get(key)
            inst_attr = dic.get(key, cls_attr.default)
            if callable(inst_attr):
                inst_attr = inst_attr()
            if isinstance(cls_attr, fields.DateField):
                if cls_attr.auto_now_add and not inst_attr:
                    inst_attr = datetime.now()
                else:
                    inst_attr = datetime.strptime(inst_attr, cls.date_format)
            elif isinstance(cls_attr, fields.DatetimeField):
                if cls_attr.auto_now_add:
                    inst_attr = datetime.now()
                else:
                    inst_attr = datetime.strptime(inst_attr, cls.datetime_format)
            elif isinstance(cls_attr, fields.TimeDeltaField):
                inst_attr = datetime.timedelta(seconds=inst_attr)
            elif isinstance(inst_attr, (int, str, list, dict, tuple)):
                pass
            elif isinstance(inst_attr, fields.relational.ForeignKeyFieldInstance):
                continue
                # key = key + '_id'
                # inst_attr = dic.get(key)
            elif isinstance(cls_attr, (fields.relational.BackwardOneToOneRelation, 
                fields.relational.ManyToManyFieldInstance,
                # fields.relational.ReverseRelation,
                fields.relational.BackwardFKRelation)):
                continue
            elif isinstance(inst_attr, (fields.relational.ManyToManyFieldInstance, 
                    fields.relational.ReverseRelation,
                    queryset.QuerySet)):
                continue
            # print(key, inst_attr, cls_attr)
            dic[key] = inst_attr
        if dic['id'] is None:
            del dic['id']
        # print(dic)
        return cls(**dic)

    @classmethod
    def dic_to_json(cls, dic):
        for k, v in dic.items():
            if isinstance(v, datetime):
                cls_attr = cls._meta.fields_map.get(k)
                if isinstance(cls_attr, fields.DateField):
                    v = v.strftime(cls.date_format)
                else:
                    v = v.strftime(cls.datetime_format)
            elif isinstance(v, timedelta):
                    v = v.seconds
            dic[k] = v
        return dic

    @classmethod
    def clean_dict(cls, dic):
        fields = cls._fields()
        for key, inst_attr in dic.items():
            if dic not in fields:
                continue
            cls_attr = cls._meta.fields_map.get(key)
            if isinstance(cls_attr, fields.DateField):
                if cls_attr.auto_now_add and not inst_attr:
                    inst_attr = datetime.now()
                else:
                    inst_attr = datetime.strptime(inst_attr, cls.date_format)
            elif isinstance(cls_attr, fields.DatetimeField):
                if cls_attr.auto_now_add:
                    inst_attr = datetime.now()
                else:
                    inst_attr = datetime.strptime(inst_attr, cls.datetime_format)
            elif isinstance(cls_attr, fields.TimeDeltaField):
                inst_attr = datetime.timedelta(seconds=inst_attr)
            dic[key] = inst_attr
        return dic

    async def update(self, **kw):
        # update_fields = list(args)
        # dic = self.to_dict()
        # dic.update(**args)
        # # print('#'*10, dic, update_fields)
        # obj = self.from_dict(dic)
        # obj.id = self.id
        # await obj.save(update_fields=update_fields)
        # return obj
        # await self.__class__.filter(pk=self.pk).update(**args)
        kw = self.clean_dict(kw)
        await self.update_from_dict(kw).save(update_fields=tuple(kw))
        await self.refresh_from_db(fields=tuple(kw))
        return self

    async def replace(self, **args):
        args['id'] = self.id
        obj = self.from_dict(args)
        await obj.save(force_update=True)
        return obj

