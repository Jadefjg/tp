import aioredis
import config
from threading import local

_local = local()

async def get_redis():
    global _local
    if not hasattr(_local, '_redis') or not _local._redis:
        _local._redis = await aioredis.from_url(config.Config.REDIS_URL,
            # minsize=config.Config.REDIS_POOL_MINSIZE,
            # maxsize=config.Config.REDIS_POOL_MAXSIZE,
            max_connections=config.Config.REDIS_POOL_MAXSIZE
        )
    return _local._redis

def release_redis():
    _local._redis = None

def init_redis(app):
    @app.listener('before_server_start')
    async def redis_at_start(app, loop):
        app.ctx.redis = await get_redis()

    @app.listener('after_server_stop')
    async def redis_at_stop(app, loop):
        await app.ctx.redis.close()
        release_redis()
