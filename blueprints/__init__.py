from .user import user_bp
from .project import project_bp
from .element import element_bp
from .case import case_bp
from .task import task_bp #, ws_bp
from .api import api_bp

def init_app(app):
    app.blueprint(user_bp)
    app.blueprint(project_bp)
    app.blueprint(element_bp)
    app.blueprint(case_bp)
    app.blueprint(task_bp)
    app.blueprint(api_bp)
    
    # app.blueprint(ws_bp)