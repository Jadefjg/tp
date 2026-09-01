import asyncio
import io
import json
import operator
import re
import traceback as tb
from collections import defaultdict
from enum import IntEnum
from functools import partial
from mimetypes import guess_type
from os import path
from urllib.parse import urlencode, urljoin

from aiohttp import ClientResponse, ClientSession, FormData
from aiohttp.helpers import content_disposition_header
from blueprints.case.models import File
from config import Config
from const import CONTENT_TYPE_MAP
from utils import (copy_file, ensure_json, extract_jsonpath, iter_file,
                   json_serialize, run_code, to_str)

from .context import VAR_RE, Context
from .hooks import (after_case_detail, after_case_run, after_task_run,
                    before_case_detail, before_case_run, before_task_run)


class PipeWriter:
    def __init__(self, writer):
        self._writer = writer

    async def write(self, chunk):
        self._writer.write(chunk)

class Result(IntEnum):
        NOT_RUN = 0
        PASS = 1
        FAILED = 2
        ERROR = 3
        SKIPPED = 4
        STOPPED = 5

class RunResult:
    __slots__ = ['meta']
    def __init__(self):
        self.meta = {}
        self.classify = None
        self.result = Result.NOT_RUN

    def __setattr__(self, name: str, value) -> None:
        if name in self.__slots__:
            return super().__setattr__(name, value)
        self.meta[name] = value

    def __getattr__(self, name: str):
        return self.meta.get(name)

    def to_json(self):
        return json_serialize(self.meta)

class BaseRunner:
    def __init__(self, ctx: Context):
        self._ctx = ctx
        self._rslt = RunResult()

    def _wraps(self, str):
        return self._ctx.wrap_string(str)

    def run(self):
        raise NotImplementedError

class StepRunner(BaseRunner):
    async def run_ui(self, content):
        raise NotImplementedError

    async def before_steprun(self):
        await before_case_detail(self._ctx)

    async def after_steprun(self):
        await after_case_detail(self._ctx, self._rslt)

    def parse_params(self, params):
        p = defaultdict(list)
        for v in params:
            if v.get('checked'):
                p[self._wraps(v.get('key',''))].append(self._wraps(v.get('value','')))
        return p

    def parse_body(self, body):
        classify = body.get('classify')
        extra_headers = {}
        if classify == 'none' or not classify:
            return {
                'body': {}
            }
        if classify == 'raw':
            raw_type = body.get('rawType')
            content_type = CONTENT_TYPE_MAP.get(raw_type)
            if content_type:
                extra_headers['Content-Type'] = content_type
            body = body.get('rawBody', '')
            return {
                'extra_headers': extra_headers,
                'body': {
                    'data': self._ctx.wrap_string(body)
                }
            }
        if classify == 'binary':
            body = body.get('binaryBody', {})
            return {
                'extra_headers': extra_headers,
                'body': body
            }

        if classify == 'x-www-form-urlencoded':
            form = body.get('urlEncodedBody', {})
            form = self.parse_params(form)
            return {
                'extra_headers': extra_headers,
                'body': {
                    'data': form
                }
            }

        if classify == 'form-data':
            form_data = body.get('formBody', [])
            form = {}
            for item in form_data:
                if item.get('checked'):
                    if item.get('valueType', 'Text') == 'Text':
                        form[item['key']] = self._wraps(item['value'])
                    else:
                        form[item['key']] = item['file']
            return {
                'extra_headers': extra_headers,
                'body': form
            }

    def parse_key_value(self, items):
        items = { item['key']: item['value'] for item in items if item.get('checked')}
        return {
            self._wraps(key): self._wraps(value)
            for key, value in items.items()
        }

    def parse_cookie(self, cookies):
        return self.parse_key_value(cookies)

    def parse_headers(self, headers):
        return self.parse_key_value(headers)

    def parse_url(self, url):
        url = self._wraps(url)
        if re.match(r'https?://', url):
            return url
        base_url = self._ctx.get('http_base_url', '')
        # return urljoin(base_url, url)
        base_url = base_url.rstrip('/')
        url = url.lstrip('/')
        url = '%s/%s' % (base_url, url)
        return url

    async def run_api(self, content):
        """
        for example:
        content = {
            "params": [
                {
                "key": "a",
                "checked": true,
                "value": "b"
                },
                {
                "key": "c",
                "value": "d",
                "checked": true
                }
            ],
            "headers": [
                {
                "key": "Content-Type",
                "checked": true,
                "value": "application/json",
                "comment": "ddd"
                }
            ],
            "body": {
                "classify": "binary",  #  none, form-data, x-www-form-urlencoded, raw, binary
                "formBody": [
                {
                    "key": "fdsf",
                    "checked": true,
                    "value": "fsdf",
                    "valueType": "Text", # Text File
                    "comment": "fdsf"
                }
                ],
                "urlEncodedBody": [
                {
                    "key": "dfsdfds",
                    "checked": true,
                    "value": "fdsfds"
                }
                ],
                "rawBody": "{\n  \"a\": 1\n}"
            },
            "cookie": [
                {
                "key": "Token",
                "checked": true,
                "value": "ccccc"
                }
            ],
            "method": "GET",
            "url": "/this/is/the/path",
            "extract": {
                "regex": [
                {
                    "regex": "\"name\": \\s*\"(?P<name>[^\"]+)\"",
                    "group": "name"
                }
                ],
                "jsonpath": [
                {
                    "jsonpath": "json.data.id",
                    "varname": "pathId",
                    "checked": true
                }
                ]
            },
            "assertion": {
                "environment": [
                {
                    "varname": "pathId",
                    "value": "123"
                }
                ],
                "jsonpath": [
                {
                    "jsonpath": "json.data.id",
                    "value": "123"
                }
                ]
            }
        }
        """
        logger = self._ctx.get_logger()
        request_kwargs = await self.pre_handle(content)
        logger.info('开始执行请求: %s', str(request_kwargs))
        client: ClientSession = self._ctx.get_client()
        response = {}
        async with client.request(**request_kwargs) as resp:
            resp: ClientResponse
            response['headers'] = dict(resp.headers)
            response['cookies'] = dict(resp.cookies)
            body = await resp.read()
            try:
                body = body.decode()
            except:
                pass
            response['status_code'] = resp.status
            response['status_reason'] = resp.reason
            response['body'] = body
            request_info = resp.request_info
            formated_request_info = self.format_request_info(request_info)
            self._rslt.real_request_header = formated_request_info
            try:
                response['json'] = json.loads(body)
            except:
                response['json'] = None
            logger.info('请求返回: %s', str(response))
            self._rslt.response = response
            content_type = request_info.headers.get('Content-Type')
            self._repire_boundary(content_type)
            self._ctx['last_response'] = response
        self.api_run_extract()
        self.api_run_assert()

    def _repire_boundary(self, content_type):
        if not content_type:
            return
        boundary = re.search(r'boundary=(?P<boundary>.*)', content_type)
        if not boundary:
            return
        boundary = boundary.group('boundary')
        self._rslt.raw_body = self._rslt.raw_body.replace('<this is a boundary>', boundary)

    def format_request_info(self, request_info):
        buf = io.StringIO()
        buf.write(request_info.method)
        buf.write(' ')
        buf.write(str(request_info.url))
        buf.write(' http/1.1\r\n')
        for header, header_value in request_info.headers.items():
            buf.write(header.title())
            buf.write(': ')
            buf.write(header_value)
            buf.write('\r\n')
        buf.write('\r\n')
        return buf.getvalue()

    def api_run_extract(self):
        logger = self._ctx.get_logger()
        response = self._rslt.response
        for i, extractor in enumerate(self._rslt.extractors):
            try:
                extractor(response)
            except (KeyError, IndexError, TypeError) as e:
                raise AssertionError(*e.args)
            except Exception as e:
                logger.error('extract[%d] error: %s', i, e)
                raise e

    def api_run_assert(self):
        logger = self._ctx.get_logger()
        response = self._rslt.response
        for i, extractor in enumerate(self._rslt.assertors):
            try:
                extractor(response)
            except (KeyError, IndexError, TypeError) as e:
                raise AssertionError(*e.args)
            except Exception as e:
                logger.warning('extract[%d] error: %s', i, e)
                raise e

    def api_parse_regex_extractor(self, regex):
        def extract(response, item):
            body = response.get('body')
            body = to_str(body)
            reg = item.get('regex')
            match = re.search(reg, body)
            dic = match.groupdict()
            varname = item.get('varname')
            if varname:
                self._ctx[varname] = dic.get(varname)
                self._rslt.extractor_rslt.append({
                    'classify': 'regex',
                    'extractor': reg,
                    'varname': varname,
                    'value': self._ctx[varname]
                })
            else:
                for varname in dic:
                    self._ctx[varname] = dic.get(varname)
                    self._rslt.extractor_rslt.append({
                        'classify': 'regex',
                        'extractor': reg,
                        'varname': varname,
                        'value': self._ctx[varname]
                    })

        extractors = []
        for item in regex:
            if item.get('checked'):
                extractors.append(partial(extract, item=item))
        return extractors

    def api_parse_jsonpath_extractor(self, jsonpath):
        def extract(response, item):
            jpath = item.get('jsonpath')
            varname = item.get('varname')
            varname = varname or jpath.rsplit('.', 1).pop()
            self._ctx[varname] = extract_jsonpath(response, jpath)
            self._rslt.extractor_rslt.append({
                'classify': 'jsonpath',
                'extractor': jpath,
                'varname': varname,
                'value': self._ctx[varname]
            })

        extractors = []
        for item in jsonpath:
            if item.get('checked'):
                extractors.append(partial(extract, item=item))
        return extractors

    def api_parse_extract(self, extract):
        regex = extract.get('regex', [])
        regex_extractors = self.api_parse_regex_extractor(regex)
        jsonpath = extract.get('jsonpath', [])
        jsonpath_extractors = self.api_parse_jsonpath_extractor(jsonpath)
        self._rslt.extractor_rslt = []
        return regex_extractors + jsonpath_extractors

    def api_parse_env_assertion(self, env):
        def assertor(response, item):
            varname = item.get('varname')
            value = item.get('value')
            to = self._ctx.get(varname)
            opt = item.get('opt')
            try:
                value = self._eval(value)      # 避免int， str， float之间因为类型差异导致的不等
            except:
                pass
            rslt, message = self._assert(to, opt, value)
            self._rslt.assertion_rslt.append({
                'classify': 'env',
                'assertor': varname,
                'value': to,
                'opt': opt,
                'expect': value,
                'result': rslt
            })
            assert rslt, message
        assertors = []
        for item in env:
            if item.get('checked'):
                assertors.append(partial(assertor, item=item))
        return assertors

    def _eval(self, s):
        if (m := VAR_RE.search(s)):
            return self._ctx.wrap_string(s)
        return self._ctx.eval(s)

    def _assert(self, value, opt, expect):
        if opt == 'in':
            rslt = operator.contains(expect, value)
        else:
            rslt = getattr(operator, opt)(value, expect)
        opt_map = {
            'ne': '!=',
            'eq': '==',
            'in': 'be in',
            'gt': '>',
            'ge': '>=',
            'lt': '<',
            'le': '<=',
            'contains': 'contains'
        }
        return rslt, '%s is expected to %s %s' % (expect, opt_map.get(opt, opt), value)

    def api_parse_jsonpath_assertion(self, jsonpath):
        def assertor(response, item):
            jpath = item.get('jsonpath')
            value = item.get('value')
            opt = item.get('opt')
            to = extract_jsonpath(response, jpath)
            try:
                value = self._eval(value)      # 避免int， str， float之间因为类型差异导致的不等
            except:
                pass
            rslt, message = self._assert(to, opt, value)
            self._rslt.assertion_rslt.append({
                'classify': 'jsonpath',
                'assertor': jpath,
                'value': to,
                'opt': opt,
                'expect': value,
                'result': rslt
            })
            assert rslt, message
        assertors = []
        for item in jsonpath:
            if item.get('checked'):
                assertors.append(partial(assertor, item=item))
        return assertors

    def api_parse_assertion(self, assertion):
        env = assertion.get('environment', [])
        env_assertors = self.api_parse_env_assertion(env)
        jsonpath = assertion.get('jsonpath', [])
        jsonpath_extractors = self.api_parse_jsonpath_assertion(jsonpath)
        self._rslt.assertion_rslt = []
        return env_assertors + jsonpath_extractors

    async def pre_handle(self, content):
        buffer = io.StringIO()
        method = content.get('method')
        buffer.write(method.upper())
        buffer.write(' ')
        # self._rslt.method = method
        url = content.get('url', '')
        url = self.parse_url(url)
        params = content.get('params', [])
        params = self.parse_params(params)
        # self._rslt.params = params
        buffer.write(url)
        if params:
            buffer.write('?')
            buffer.write(urlencode(params, doseq=True))
        buffer.write(' http/1.1\r\n')
        # self._rslt.url = url
        headers = content.get('headers', [])
        headers = self.parse_headers(headers)
        for header, header_value in headers.items():
            buffer.write('%s: %s\r\n' % (header.title(), header_value or ''))
        # self._rslt.headers = headers
        cookies = content.get('cookie', [])
        cookies = self.parse_cookie(cookies)
        # self._rslt.cookies = cookies
        if cookies:
            buffer.write('Cookie: ')
            for cookie, cookie_value in cookies.items():
                buffer.write('%s=%s' % (cookie, cookie_value))
            buffer.write('\r\n')
        buffer.write('\r\n')
        self._rslt.raw_header = buffer.getvalue()

        body = content.get('body')
        body_classify = body.get('classify')
        body = self.parse_body(body)
        extra_headers = body.get('extra_headers', {})
        headers.update(extra_headers)
        body = body.get('body')
        self._rslt.body = body
        body_kwargs = {}
        if body_classify == 'binary':
            taskfilepath, taskfilerealpath = await self.get_taskfile(body)
            body_kwargs['data'] = iter_file(taskfilerealpath)
            self._rslt.raw_body = ('<a href="%s" download="%s" class="el-tag el-tag--success el-tag--mini el-tag--light">click to download</a>\r\n\r\n' %
                (taskfilepath, body.get('name', '')))
        elif body_classify == 'form-data':
            formdata = FormData()
            for name, value in body.items():
                if isinstance(value, dict): # file
                    taskfilepath, taskfilerealpath = await self.get_taskfile(value)
                    content_type, _ = guess_type(taskfilepath)
                    formdata.add_field(name, open(taskfilerealpath, 'rb'),
                        content_type=content_type,
                        filename=value.get('name'))
                else:
                    formdata.add_field(name, value)
            self._rslt.raw_body = await self.get_formdata_data(formdata)
            body_kwargs['data'] = formdata
        else:
            if body_classify == 'raw':
                self._rslt.raw_body = body.get('data')
            body_kwargs.update(body)
        self._rslt.body_kwargs = body_kwargs
        extract = content.get('extract', {})
        self._rslt.extract = [
            {'classify': k, **item}
            for k, v in extract.items() for item in v if item.get('checked')
        ]
        self._rslt.extractors = self.api_parse_extract(extract)
        assertion = content.get('assertion', {})
        self._rslt.assertion = [
            {'classify': k, **item}
            for k, v in assertion.items() for item in v if item.get('checked')
        ]
        self._rslt.assertors = self.api_parse_assertion(assertion)
        request_kwargs = {
            'method': method,
            'url': url,
            'params': params,
            'headers': headers,
            'cookies': cookies
        }
        request_kwargs.update(body_kwargs)
        # print(request_kwargs)
        return request_kwargs

    async def get_formdata_data(self, formdata):
        if not formdata.is_multipart:
            buf = io.BytesIO()
            writer = PipeWriter(buf)
            payload = formdata()
            await payload.write(writer)
        else:
            buf = io.StringIO()
            boundary = '--<this is a boundary>'
            for dispparams, headers, value in formdata._fields:
                buf.write(boundary + '\r\n')
                if content_type := headers.get('Content-Type'):
                    buf.write('Content-Type: ')
                    buf.write(content_type)
                    buf.write('\r\n')
                buf.write('Content-Disposition: ')
                buf.write(content_disposition_header('form-data', quote_fields=True, **dispparams))
                buf.write('\r\n')
                if isinstance(value, io.IOBase):
                    buf.write('Content-Length: &lt;not calculate&gt;\r\n\r\n')
                    filename = value.name[len(Config.BASEDIR):]
                    buf.write('<a href="%s" download="%s" class="el-tag el-tag--success el-tag--mini el-tag--light">click to download</a>\r\n\r\n' %
                        (filename, dispparams.get('filename', '')))
                else:
                    buf.write('Content-Length: %d\r\n\r\n'%len(value))
                    buf.write(value)
                    buf.write('\r\n\r\n')
            buf.write('--%s--\r\n\r\n' % boundary)
        return to_str(buf.getvalue())

    async def get_taskfile(self, file):
        file_id = file.get('id')
        file = await File.get(id=file_id)
        filepath = file.path
        taskfilepath = filepath.replace('casefile', 'taskfile', 1)
        taskfilerealpath = path.join(Config.BASEDIR, taskfilepath.lstrip('/'))
        if path.exists(taskfilerealpath):
            return taskfilepath, taskfilerealpath
        filepath = path.join(Config.BASEDIR, filepath.lstrip('/'))
        await copy_file(filepath, taskfilerealpath)
        return taskfilepath, taskfilerealpath

    async def run_macro(self, content):
        """
        for example
        content = {\"macro\":{\"name\":\"登录\",\"comment\":\"登录系统\",\"code\":\"print(234)\",\"isCorotine\":false,\"id\":1,\"project_id\":1,\"status\":1,\"verifiedAt\":\"2021-07-09 16:25:43\",\"createAt\":\"2021-07-09 15:52:16\",\"verifiedBy_id\":1,\"createBy_id\":1,\"createBy_name\":\"ryan\",\"verifiedBy_name\":\"ryan\",\"project_name\":\"新零售\"}}
        """
        macro = content.get('macro')
        self._rslt.macro = macro
        await self.run_raw(macro)

    async def run_raw(self, content):
        """
        for example:
        content = {\"isCorotine\":true,\"code\":\"dfsfs\"}
        """
        code = content.get('code')
        self._rslt.code = code
        is_corotine = content.get('isCorotine')
        rslt = await run_code(code, is_corotine=is_corotine, ctx=self._ctx)
        self._rslt.run_return = rslt

    async def run(self):
        try:
            await self.before_steprun()
            content = self._ctx.task_run_case_detail.case_detail_content
            classify = content.get('classify')
            self._rslt.classify = classify
            content = content.get('content')
            content = ensure_json(content)
            runner = getattr(self, 'run_' + classify)
            await runner(content)
        except AssertionError as e:
            self._rslt.result = Result.FAILED
            self._rslt.message = str(e)
            raise
        except asyncio.CancelledError:
            self._rslt.result = Result.STOPPED
            self._rslt.message = '任务被强行终止了'
            raise
        except Exception as e:
            self._rslt.result = Result.ERROR
            self._rslt.message = tb.format_exc()
            raise
        else:
            self._rslt.result = Result.PASS
        finally:
            await self.after_steprun()

    async def skip(self, message):
        try:
            await self.before_steprun()
            self._rslt.result = Result.SKIPPED
            self._rslt.message = message
        except Exception as e:
            logger = self._ctx.get_logger()
            logger.exception(e)
        finally:
            await self.after_steprun()


class TestRunner(BaseRunner):

    async def before_case(self):
        await before_case_run(self._ctx)

    async def after_case(self):
        await after_case_run(self._ctx, self._rslt)

    async def run(self):
        try:
            await self.before_case()
            await self.run_case_details()
        except AssertionError as e:
            self._rslt.result = Result.FAILED
            self._rslt.message = e.args[0]
            raise
        except asyncio.CancelledError:
            self._rslt.result = Result.STOPPED
            self._rslt.message = '任务被强行终止了'
            raise
        except Exception as e:
            self._rslt.result = Result.ERROR
            self._rslt.message = tb.format_exc()
            raise
        finally:
            if self._rslt.result != Result.SKIPPED:
                # skip 会执行after_case 这里不要重复执行
                await self.after_case()

    async def run_case_details(self):
        case_details = await self._ctx.task_run_case.case_details.all()
        if not case_details:
            return await self.skip('该用例无步骤，跳过')
        message = None
        willskip = False
        error = None
        for detail in case_details:
            with self._ctx as _ctx:
                _ctx.set_run_case_detail(detail)
                try:
                    if not willskip:
                        await StepRunner(_ctx).run()
                        self._rslt.result = Result.PASS
                    else:
                        await StepRunner(_ctx).skip(message)
                except Exception as e:
                    import sys
                    willskip = True
                    message = '前面步骤失败或错误'
                    error = e.with_traceback(sys.exc_info()[2])
        if error:
            raise error

    async def skip(self, message):
        try:
            await self.before_case()
            case_details = await self._ctx.task_run_case.case_details.all()
            for detail in case_details:
                with self._ctx as _ctx:
                    _ctx.set_run_case_detail(detail)
                    await StepRunner(_ctx).skip(message)
        except Exception as e:
            logger = self._ctx.get_logger()
            logger.exception(e)
            self._rslt.result = Result.ERROR
            self._rslt.message = tb.format_exc()
        else:
            self._rslt.result = Result.SKIPPED
            self._rslt.message = message
        finally:
            await self.after_case()

class TaskRunner(BaseRunner):

    async def before_task_run(self):
        await before_task_run(self._ctx)

    async def after_task_run(self):
        await after_task_run(self._ctx, self._rslt)

    async def run(self):
        await self.before_task_run()
        try:
            self._rslt.result = Result.PASS
            await self.run_case()
        except AssertionError as e:
            self._rslt.result = Result.FAILED
            self._rslt.message = e.args[0]
        except asyncio.CancelledError:
            self._rslt.result = Result.STOPPED
            self._rslt.message = '任务被强行终止了'
        except Exception as e:
            self._rslt.result = Result.ERROR
            self._rslt.message = tb.format_exc()
            logger = self._ctx.get_logger()
            logger.exception(e)
        finally:
            await self.after_task_run()

    async def run_case(self):
        run_cases = await self._ctx.task_run.cases.order_by('task_case__testcase__title').all()
        for run_case in run_cases:
            with self._ctx.enter_run_case(run_case) as _ctx:
                try:
                    if self._ctx.running:
                        await TestRunner(_ctx).run()
                    elif self._ctx.paused:
                        while self._ctx.paused:
                            await asyncio.sleep(1)
                        await TestRunner(_ctx).run()
                    else:
                        await TestRunner(_ctx).skip('任务终止')
                except AssertionError as e:
                    self._rslt.result = Result.FAILED
                    self._rslt.message = e.args[0]
                except asyncio.CancelledError:
                    self._rslt.result = Result.STOPPED
                    self._rslt.message = '任务被强行终止了'
                    raise
                except Exception as e:
                    self._ctx.stop_run()
                    self._rslt.result = Result.ERROR
                    self._rslt.message = tb.format_exc()
                    logger = self._ctx.get_logger()
                    logger.exception(e)

