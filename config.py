import os
import logging
import os

DEBUG=True
class CommonConfig:
    TOKEN_LENGTH = 200
    TOKEN_EXPIRE = 86400 * 7
    ALLOW_MULTI_LOGIN = True
    BASEDIR = os.path.dirname(__file__)
    UPLOAD_PATH = 'media/casefile'

    REDIS_POOL_MAXSIZE = 100

    TIME_ZONE = 'Asia/Shanghai'

    WHITE_LIST = [
        "/login",
        "/media"
    ]

    PORT= int(os.getenv('TP_PORT', 8081))
    WORKERS = int(os.getenv('TP_WORKERS', 1))
    RUNNER_PER_WORKER = int(os.getenv('TP_RUNNER_PER_WORKER', 20))

    # redis queue
    ALL_TASK_RUN_QUEUE_NAME = 'tp:task:startrun:all'
    # TASK_RUN_INFO_CHANNEL= 'tp:task:info:${taskrunid}'
    TASK_RUN_CONTROL_CHANNEL = 'tp:task:control:${taskrunid}'

    SCHEDULE_QUEUE = 'tp:task:to_schedule'
    TASK_SCHEDULED = 'tp:task:scheduled'
    TASK_RUN_TIMES = 'tp:task:run_times'

    REDIS_LOGGER_QUEUE = 'tp:task:log:queue'
    # REDIS_LOGGER_BROADCAST = 'tp:task:log:broadcast'
    # end of redis queue

    # redis key
    JOB_RESULT = 'tp:job:${job_id}'
    JOBS_RESULT = 'tp:jobs'
    # end of redis key

    # config of log
    TASKRUNNER_LOGGER_NAME = 'tp.taskrunner'
    LOG_LEVEL = logging.DEBUG
    # end of log

    # config of apscheduler job
    APSCHEDULER_MISFIRE_GRACE_TIME = 5
    APSCHEDULER_COALESCE = False
    # end of apsheduler job

class DEV(CommonConfig):
    # DB_URL = "mysql://test:test@172.18.0.100:3306/test"
    DB_URL = "sqlite://db.sqlite3"
    DB_CONNECTION = {
        'default': {
            'engine': 'tortoise.backends.mysql',
            'credentials': {
                'host': '127.0.0.1',
                'port': 3306,
                'user': 'test',
                'password': 'test',
                'database': 'test',
                'pool_recycle': 10
            }
        }
    }
    ROOT_URL = '/'
    REDIS_URL = 'redis://127.0.0.1'

    HOST = 'localhost:9528'

class PROD(CommonConfig):
    # DB_URL = 'mysql://testplatform:testplatform@172.18.0.100:3306/testplatform'
    DB_CONNECTION = {
        'default': {
            'engine': 'tortoise.backends.mysql',
            'credentials': {
                'host': '127.0.0.1',
                'port': 3306,
                'user': 'testplatform',
                'password': 'testplatform',
                'database': 'testplatform',
                'pool_recycle': 28750
            }
        }
    }
    ROOT_URL = '/'
    REDIS_URL = 'redis://172.18.0.99'
    HOST = '10.20.12.90:4096'

if DEBUG:
    Config = DEV
else:
    Config = PROD


