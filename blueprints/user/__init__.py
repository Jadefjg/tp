from sanic import Blueprint
from .views import Login, UploadView, GetUserInfo, Logout, UserView
from config import Config

user_bp = Blueprint('user', url_prefix=Config.ROOT_URL)

user_bp.add_route(Login.as_view(), '/login', name='login')
user_bp.add_route(GetUserInfo.as_view(), '/user/info', name='userinfo')
user_bp.add_route(Logout.as_view(), '/user/logout', name='logout')
user_bp.add_route(UploadView.as_view(), '/upload', name='upload')
UserView.register(user_bp, 'user')