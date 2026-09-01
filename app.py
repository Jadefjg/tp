from sanic import Sanic
import config
from blueprints import init_app as blueprint_init_app
from extentions import init_app as extension_init_app
from middlewares import init_app as middlerware_init_app

import os
os.makedirs('media/casedata', exist_ok=True)
os.makedirs('media/casefile', exist_ok=True)
os.makedirs('media/taskfile/videos', exist_ok=True)

app = Sanic(__name__, load_env=False)
app.update_config(config.Config)

extension_init_app(app)
middlerware_init_app(app)
blueprint_init_app(app)

app.static('/media', './media')

# below is just for test
# end test

if __name__ == '__main__':
    app.run(
        debug=config.DEBUG,
        host='0.0.0.0',
        port=config.Config.PORT, 
        workers=config.Config.WORKERS
    )
    