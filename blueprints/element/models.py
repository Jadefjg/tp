from tortoise import fields
from framework import models
from enum import Enum
from po.widgets import BaseWidget
from po import By
import asyncio


def get_widget_by_name(name):
    widget =  BaseWidget.all_widgets().get(name)
    if widget is None:
        raise ValueError('not found widget: %s' % name)
    return widget.get('cls')

class Element(models.Model):
    class ElementClassify(str, Enum):
        PAGE_GROUP = 'page group'
        PAGE = 'page'
        ELEMENT = 'element'
        WIDGET = 'widget'

    name = fields.CharField(max_length=30)
    classify = fields.CharEnumField(ElementClassify)
    widget_name = fields.CharField(max_length=30, null=True)
    selector = fields.CharEnumField(By, null=True)
    selector_value = fields.CharField(max_length=100, null=True)
    selector_is_relative = fields.BooleanField(default=False)
    status = fields.IntEnumField(models.StatusEnum, description=models.StatusEnum.__doc__,
                                 default=models.StatusEnum.NORMAL)
    project = fields.ForeignKeyField("models.Project", db_constraint=False, related_name="elements")
    parent: fields.ForeignKeyNullableRelation["Element"] = fields.ForeignKeyField('models.Element',
                                                                                  null=True,
                                                                                  db_constraint=False,
                                                                                  related_name='children')
    children: fields.ReverseRelation['Element']

    async def get_element(self, driver):
        if self.classify in (self.ElementClassify.PAGE_GROUP, self.ElementClassify.PAGE):
            return None
        if self.classify == self.ElementClassify.WIDGET:
            widget_class = get_widget_by_name(self.widget_name)
        ctx = None
        if self.selector_is_relative:
            parent = await self.parent.get()
            if parent:
                ctx = await parent.get_element(driver)
        ctx = ctx or driver
        loop = asyncio.get_event_loop()
        if self.classify == self.ElementClassify.WIDGET:
            selector, selector_value = widget_class.wrap_selector(self.selector, self.selector_value)
        else:
            selector, selector_value = self.selector, self.selector_value
        element = await loop.run_in_executor(None, ctx.find_element, selector, selector_value)
        if self.classify == self.ElementClassify.WIDGET:
            element = widget_class(element)
        return element
