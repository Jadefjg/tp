from .base import BaseWidget
from .. import By

class TextWidget(BaseWidget):
    __actions__ = []
    
    @classmethod
    def wrap_selector(self, selector, selector_value):
        if selector != By.USER_DEFINED:
            return selector, selector_value
        return By.XPATH, '//[text()=%s]' % selector_value