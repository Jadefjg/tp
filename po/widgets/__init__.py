from .base import BaseWidget
import os

widget_dir = os.path.dirname(__file__)

for filename in os.listdir(widget_dir):
    if filename in ('__init__.py', '.', '..'):
        continue
    if not filename.endswith('.py'):
        continue
    modulename = 'po.widgets.%s' % filename[:-3]
    __import__(modulename)