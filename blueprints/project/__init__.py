from sanic import Blueprint
from .views import ProjectView, EnvironmentView
from config import Config

project_bp = Blueprint('project', url_prefix=Config.ROOT_URL)

ProjectView.register(project_bp, 'project')
EnvironmentView.register(project_bp, 'environment')