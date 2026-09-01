import asyncio
import hashlib
import json
import time
from datetime import date, datetime
from functools import partial, wraps
from random import choice
from string import ascii_letters, digits
from functools import partial
from aiohttp import ClientSession
import aiofiles
import base64
from Crypto.Cipher import AES


def to_str(str_or_bytes, encoding='utf-8'):
    if isinstance(str_or_bytes, bytes):
        return str_or_bytes.decode(encoding)
    return str(str_or_bytes)

def to_bytes(str_or_bytes, encoding='utf-8'):
    if isinstance(str_or_bytes, str):
        return str_or_bytes.encode(encoding)
    return str_or_bytes

def to_hash(str_or_bytes, method=hashlib.md5):
    if isinstance(method, str):
        method = getattr(hashlib, method)
    s = to_bytes(str_or_bytes)
    return method(s).hexdigest()

def to_md5(str_or_bytes):
    return to_hash(str_or_bytes)

def ensure_json(content):
    if isinstance(content, (list, dict)):
        return content
    if not isinstance(content, str):
        content = to_str(content)
    return json.loads(content)

def generate_token(length=64, choices=digits + ascii_letters):
    return ''.join(choice(choices) for _ in range(length))

def AsyncWrap(func):
    @wraps(func)
    async def f(*args, **kw):
        def inner(*args, **kw):
            from extentions.redis import release_redis
            nonlocal func
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                ret = func(*args, **kw)
                for task in asyncio.all_tasks(loop=new_loop):
                    new_loop.run_until_complete(task)
                new_loop.stop()
                new_loop.run_forever()
            finally:
                release_redis()
                new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                new_loop.close()
            return ret
        return await run_in_executor(inner, *args, **kw)
    return f

async def run_in_executor(func, *args, **kw):
    func = partial(func, **kw)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, func, *args)

async def copy_file(src, dst, chunk_size=8192):
    async with aiofiles.open(src, 'rb') as src_fd:
        async with aiofiles.open(dst, 'wb+') as dst_fd:
            chunk = await src_fd.read(chunk_size)
            while chunk:
                await dst_fd.write(chunk)
                chunk = await src_fd.read(chunk_size)

async def iter_file(filename=None, chunk_size=8192):
    async with aiofiles.open(filename, 'rb') as fd:
        chunk = await fd.read(chunk_size)
        while chunk:
            yield chunk
            chunk = await fd.read(chunk_size)

def default(o):
    date_format = '%Y-%m-%d'
    datetime_format = "%Y-%m-%d %H:%M:%S"
    if isinstance(o, datetime):
        return o.strftime(datetime_format)
    if isinstance(o, date):
        return o.strftime(date_format)
    if hasattr(o, 'to_json'):
        return o.to_json()
    if hasattr(o, 'to_dict'):
        return o.to_dict()
    return str(o)

json_serialize = partial(json.dumps, default=default)

def extract_jsonpath(json_obj, jpath):
    paths = jpath.split('.')
    for path in paths:
        if isinstance(json_obj, list):
            json_obj = json_obj[int(path)]
        else:
            json_obj = json_obj[path]
    return json_obj


async def run_code(code, is_corotine=False, **kwargs):
    # print('start to run code')
    if not code.strip():
        return
    kwargs.update(globals())
    code = '\n'.join(' '*4 + line for line in code.splitlines())
    code = 'def _to_run():\n' + code
    if is_corotine:
        code = 'async ' + code
    else:
        code = '@AsyncWrap\n' + code
    try:
        exec(code, kwargs)
        _to_run = kwargs['_to_run']
        return await _to_run()
    except Exception:
        raise

def time2datetime(t):
    t = int(t)
    return datetime.fromtimestamp(t)

def datetime2time(d):
    if isinstance(d, str):
        d = datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
    return d.timestamp()

def padding(s, to=16):
    to_pad = to - len(s) % to
    if to_pad == to:
        return s
    return s + '\x00'*to_pad

def aes(s, key):
    _aes = AES.new(key, AES.MODE_ECB)
    encrypted = _aes.encrypt(padding(s))
    return encrypted

def aes2base64(s, key):
    encrypted = aes(s, key)
    return base64.b64encode(encrypted).decode()

if __name__ == '__main__':
    # asyncio.run(run_code('print(ctx)', is_corotine=True, ctx=123))
    print(extract_jsonpath({
        "a": 123,
        "b": [{
            "c":1
        }]
    }, "b.0"))