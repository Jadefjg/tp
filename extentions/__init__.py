from . import db, redis, scheduler, testrunner, logger

def init_app(app):
    db.init_db(app)
    redis.init_redis(app)
    scheduler.init_app(app)
    logger.init_app(app)
    testrunner.init_app(app)
    