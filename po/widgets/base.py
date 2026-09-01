from functools import wraps
from selenium.webdriver.remote.webelement import WebElement
import inspect, types
import re

MAGIC_VAR = re.compile(r'__\w+__')

class BaseWidget(WebElement):
    __widgets = {}

    def __init_subclass__(cls, name=None, description=''):
        # cls 子类或者子类的子类.
        super().__init_subclass__()
        name = name or cls.__name__
        if name in BaseWidget.__widgets:
            raise ValueError('duplicate name: %s' % name)
        BaseWidget.__widgets[name] = {
            'cls': cls,
            'description': description
        }
        cls.__el_name = name

    def __init__(self, el):
        self._parent = el.parent
        self._id = el.id
        self._w3c = el._w3c
    
    @classmethod
    def all_widgets(cls):
        return BaseWidget.__widgets
    
    @classmethod
    def get_name(cls):
        return cls.__el_name

    @classmethod
    def wrap_selector(self, selector, selector_value):
        raise NotImplementedError

    def get_actions(self):
        rslt = []
        for attr in dir(self):
            if MAGIC_VAR.match(attr):
                continue
            try:
                attr_value = getattr(self, attr)
            except:
                continue
            if hasattr(attr_value, '__action_title__'):
                rslt.append({
                    'title': getattr(attr_value, '__action_title__'),
                    'sig': get_signature(attr_value)
                })
        return rslt

def get_signature(callable):
    pass


def action(title_or_function):
    if isinstance(title_or_function, types.FunctionType):
        return action(title_or_function.__name__)(title_or_function)
    def wrapper(func):
        func.__action_title__ = title_or_function
        return func
    return wrapper

if __name__ == '__main__':
    import asyncio
    class A(BaseWidget):

        @action
        async def say_one(self):
            print('one')

        @action('鬼')
        async def say_two(self):
            print('two')

    class FakeWebElement:
        id = None
        parent = None
        _w3c = None

    a = A(FakeWebElement)
    print(a.get_actions())