import os

from config import Config
from const import ResponseCode
from sanic import Blueprint, response
from utils import to_hash
from hashlib import sha256
import aiofiles

from .views import (CaseDetailView, FileView, MacroView, TestCaseView,
                    TestTagView)

case_bp = Blueprint('case', url_prefix=Config.ROOT_URL)

TestTagView.register(case_bp, "testtag")
TestCaseView.register(case_bp, "testcase")
CaseDetailView.register(case_bp, 'testcasedetail')
MacroView.register(case_bp, "macro")
FileView.register(case_bp, "file")

@case_bp.post('/api/common/upload')
async def upload(request):
    file = request.files.get('file')
    _, ext = os.path.splitext(file.name)
    name = to_hash(file.body, sha256)
    path = os.path.join(Config.BASEDIR, Config.UPLOAD_PATH, name+ext)
    if not os.path.exists(path):
        async with aiofiles.open(path, 'wb+') as fd:
            await fd.write(file.body)
    elif os.path.isdir(path):
        return response.json({
            'code': ResponseCode.DUPLICATE_KEY,
            'message': '已存在同名文件夹' 
        })
    return response.json({
        'code': ResponseCode.OK,
        'data': {
            'path': path[len(Config.BASEDIR):]
        }
    })
