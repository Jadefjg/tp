from .auth import auth
from .cors import cors_middle_req, cors_middle_res

def init_app(app):
    app.middleware(cors_middle_req)
    app.middleware(auth)
    app.middleware("response")(cors_middle_res)