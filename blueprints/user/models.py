from werkzeug.security import generate_password_hash, check_password_hash
from tortoise import fields
from framework import models
from utils import to_md5, generate_token
import time
from config import Config

class User(models.Model):
    username = fields.CharField(max_length=32, unique=True)
    _password = fields.CharField(max_length=256)
    status = fields.SmallIntField(default=1)
    isAdmin = fields.BooleanField(default=False)
    createAt = fields.DatetimeField(auto_now_add=True)

    def __init__(self, username, password=None, **kw):
        if '_password' in kw:
            kw.pop('_password')
        super().__init__(**kw)
        self.username = username
        if password:
            self.password = password
    
    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        value = to_md5(value)
        self._password = generate_password_hash(value)

    def check_password(self, value):
        return check_password_hash(self.password, value)


class UserInfo(models.Model):
    user = fields.OneToOneField("models.User", related_name="info", db_constraint=False)
    name = fields.CharField(max_length=32, blank=True, null=True)
    avatar = fields.CharField(max_length=128, default='https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif')

class LoginRecord(models.Model):
    user = fields.ForeignKeyField("models.User", related_name="lr", db_constraint=False)
    token = fields.CharField(max_length=256)
    expire = fields.FloatField(default=lambda: time.time() + Config.TOKEN_EXPIRE)
    status = fields.SmallIntField(defauld=1)

    @classmethod
    async def login(cls, user):
        if not Config.ALLOW_MULTI_LOGIN:
            await cls.filter(user=user).update(status=0)
        token = generate_token(length=Config.TOKEN_LENGTH)
        lr = cls(user=user, token=token, status=1)
        await lr.save()
        return token

    @classmethod
    async def token2user(cls, token):
        lr = await cls.filter(token=token, status=1, expire__gt=time.time()).order_by('-id').limit(1).get_or_none()
        if lr is None:
            return None
        return await lr.user.get_or_none(status=1)

    @classmethod
    async def logout(cls, user, token):
        await LoginRecord.filter(user=user, token=token).update(status=1)
        
