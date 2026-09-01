from config import Config
from sanic import Blueprint

from .views import (TaskRunCaseDetailView, TaskRunCaseView, TaskRunLogView,
                    TaskRunView, TaskSchedulerView, TaskView)
# from .ws import echo

task_bp = Blueprint('task', url_prefix=Config.ROOT_URL)
TaskView.register(task_bp, 'task')
TaskRunCaseDetailView.register(task_bp, 'taskruncasedetail')
TaskRunCaseView.register(task_bp, 'taskruncase')
TaskRunLogView.register(task_bp, 'taskrunlog')
TaskRunView.register(task_bp, 'taskrun')
TaskSchedulerView.register(task_bp, 'taskscheduler')


# ws_bp = Blueprint('ws', url_prefix=Config.ROOT_URL)
# ws_bp.websocket('/ws')(echo)
