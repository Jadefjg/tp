from sanic import Blueprint
from config import Config
from .views import ElementView, widget_list, widget_source

element_bp = Blueprint('element', url_prefix=Config.ROOT_URL)
ElementView.register(element_bp, 'element')

element_bp.add_route(widget_list, '/api/widget/widget_list')
element_bp.add_route(widget_source, '/api/widget/getSource')