import os
import logging


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_int(name, default):
    value = os.getenv(name)
    if value is None or value == '':
        return default
    return int(value)


DEBUG = _env_bool('TP_DEBUG', True)


class CommonConfig:
    TOKEN_LENGTH = 200
    TOKEN_EXPIRE = 86400 * 7
    ALLOW_MULTI_LOGIN = True
    BASEDIR = os.path.dirname(__file__)
    UPLOAD_PATH = 'media/casefile'

    REDIS_POOL_MAXSIZE = 100

    TIME_ZONE = 'Asia/Shanghai'

    WHITE_LIST = [
        "/",
        "/home",
        "/dashboard",
        "/login",
        "/register",
        "/media",
        "/static"
    ]

    PORT = _env_int('TP_PORT', 8081)
    WORKERS = _env_int('TP_WORKERS', 1)
    RUNNER_PER_WORKER = _env_int('TP_RUNNER_PER_WORKER', 4)

    GENERATE_SCHEMAS = _env_bool('TP_GENERATE_SCHEMAS', DEBUG)
    INIT_DEBUG_DATA = _env_bool('TP_INIT_DEBUG_DATA', DEBUG)
    ADMIN_USER = os.getenv('TP_ADMIN_USER', 'admin')
    ADMIN_PASSWORD = os.getenv('TP_ADMIN_PASSWORD', 'admin123')

    # redis queue
    ALL_TASK_RUN_QUEUE_NAME = 'tp:task:startrun:all'
    TASK_RUN_CONTROL_CHANNEL = 'tp:task:control:${taskrunid}'

    SCHEDULE_QUEUE = 'tp:task:to_schedule'
    TASK_SCHEDULED = 'tp:task:scheduled'
    TASK_RUN_TIMES = 'tp:task:run_times'

    REDIS_LOGGER_QUEUE = 'tp:task:log:queue'

    # redis key
    JOB_RESULT = 'tp:job:${job_id}'
    JOBS_RESULT = 'tp:jobs'

    # config of log
    TASKRUNNER_LOGGER_NAME = 'tp.taskrunner'
    LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

    # config of apscheduler job
    APSCHEDULER_MISFIRE_GRACE_TIME = 5
    APSCHEDULER_COALESCE = False

    @staticmethod
    def build_db_connection(defaults):
        credentials = defaults.copy()
        credentials.update({
            'host': os.getenv('MYSQL_HOST', credentials['host']),
            'port': _env_int('MYSQL_PORT', credentials['port']),
            'user': os.getenv('MYSQL_USER', credentials['user']),
            'password': os.getenv('MYSQL_PASSWORD', credentials['password']),
            'database': os.getenv('MYSQL_DATABASE', credentials['database']),
            'charset': os.getenv('MYSQL_CHARSET', credentials.get('charset', 'utf8mb4')),
            'minsize': _env_int('MYSQL_POOL_MIN', credentials.get('minsize', 1)),
            'maxsize': _env_int('MYSQL_POOL_MAX', credentials.get('maxsize', 10)),
            'pool_recycle': _env_int('MYSQL_POOL_RECYCLE', credentials.get('pool_recycle', 3600)),
        })
        return {
            'default': {
                'engine': 'tortoise.backends.mysql',
                'credentials': credentials
            }
        }


class DEV(CommonConfig):
    DB_URL = "sqlite://db.sqlite3"
    DB_CONNECTION = CommonConfig.build_db_connection({
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'test',
        'password': 'test',
        'database': 'test',
        'charset': 'utf8mb4',
        'minsize': 1,
        'maxsize': 10,
        'pool_recycle': 3600
    })
    ROOT_URL = '/'
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
    HOST = os.getenv('TP_HOST', 'localhost:9528')


class PROD(CommonConfig):
    DB_CONNECTION = CommonConfig.build_db_connection({
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'testplatform',
        'password': 'testplatform',
        'database': 'testplatform',
        'charset': 'utf8mb4',
        'pool_recycle': 28750
    })
    ROOT_URL = '/'
    REDIS_URL = os.getenv('REDIS_URL', 'redis://172.18.0.99:6379/0')
    HOST = os.getenv('TP_HOST', '10.20.12.90:4096')


if DEBUG:
    Config = DEV
else:
    Config = PROD
