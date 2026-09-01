from blueprints.user.models import User
from config import Config
from tortoise import Tortoise
from extentions.db import models
from getpass import getpass

import sys

async def main():
    await Tortoise.init(
        config={
            'connections': Config.DB_CONNECTION,
            'apps': {
                'models': {'models': models, "default_connection": "default"}
            }
        },
        timezone=Config.TIME_ZONE
    )
    username = sys.argv[1]
    user = await User.get_or_none(username=username)
    if user is None:
        print('用户不存在')
        return
    password = getpass('请输入新密码：')
    user.password = password
    await user.save()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())