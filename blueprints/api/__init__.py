from .views import RemoteProjectView, ApiCatView, ApiView
from sanic import Blueprint
from config import Config

api_bp = Blueprint("api", url_prefix=Config.ROOT_URL)

RemoteProjectView.register(api_bp, 'sync_config')
ApiCatView.register(api_bp, 'api_cat')
ApiView.register(api_bp, 'interface')