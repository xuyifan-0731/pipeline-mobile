import os

from .utils import get_relative_bbox_center
from .api_utils import screenshot_satisfies

import time
import inspect
import json
from functools import partial

from ..webarena_tools import (
    create_none_action,
    create_stop_action,
    create_click_action,
    create_hover_action,
    create_type_action,
    create_key_press_action,
    create_goto_url_action,
    create_scroll_action
)

class WebarenaPageExecutor:
    def __init__(self, context, page, engine, screenshot_dir):
        self.context = context
        self.page = page
        self.engine = engine
        self.screenshot_dir = screenshot_dir
        self.task_id = int(time.time())
        os.makedirs(f'{self.screenshot_dir}/{self.task_id}')

        self.new_page_captured = False
        self.current_screenshot = None
        self.current_return = None
        self.action_return = None

    def __get_current_status__(self):
        status = {
            "Current URL": self.page.url,
            "document.body.scrollHeight": self.page.evaluate("document.body.scrollHeight"),
            "window.pageYOffset": self.page.evaluate("window.pageYOffset"),
            "window.innerHeight": self.page.evaluate("window.innerHeight")
        }
        return json.dumps(status, ensure_ascii=False)

    def __capture_new_page__(self, event):
        self.new_page_captured = True
        event.wait_for_load_state(timeout=30000)
        self.page = event
        self.new_page_captured = False

    def __call__(self, code_snippet):
        self.new_page_captured = False
        self.context.on("page", self.__capture_new_page__)
        self.current_return = None

        local_context = self.__get_class_methods__()
        local_context.update(**{'self': self})
        exec(code_snippet, {}, local_context)

        return self.current_return

    def __get_class_methods__(self, include_dunder=False, exclude_inherited=True):
        """
        Returns a dictionary of {method_name: method_object} for all methods in the given class.

        Parameters:
        - cls: The class object to inspect.
        - include_dunder (bool): Whether to include dunder (double underscore) methods.
        - exclude_inherited (bool): Whether to exclude methods inherited from parent classes.
        """
        methods_dict = {}
        cls = self.__class__
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if exclude_inherited and method.__qualname__.split('.')[0] != cls.__name__:
                continue
            if not include_dunder and name.startswith('__'):
                continue
            methods_dict[name] = partial(method, self)
        return methods_dict

    def __update_screenshot__(self):
        time.sleep(5)
        self.current_screenshot = f"{self.screenshot_dir}/{self.task_id}/screenshot-{time.time()}.png"
        _ = self.page.viewport_size
        self.page.screenshot(path="/dev/null")
        while self.new_page_captured:
            time.sleep(0.1)
        self.page.screenshot(path=self.current_screenshot)
        print("Screenshot saved.")

    def reach_page_bottom(self):
        scroll_position = self.page.evaluate("window.pageYOffset")  # Current scroll position from the top
        total_height = self.page.evaluate("document.body.scrollHeight")  # Total scrollable height
        inner_height = self.page.evaluate("window.innerHeight")  # Height of the viewport

        # Determine if scrolled to bottom
        val = scroll_position + inner_height >= total_height
        print(f"Call reach_page_bottom():\n{val}")
        return val

    def open_url(self, url):
        self.page.goto(url)
        self.current_return = {"operation": "open_url", "kwargs": {"url": url}}
        self.__update_screenshot__()

    def do(self, action=None, argument=None, element=None):
        if action == 'Click':
            self.click(element)
        elif action == 'Right Click':
            self.right_click(element)
        elif action == 'Type':
            self.type(argument, element)
        elif action == 'Search':
            self.search(argument, element)
        elif action == 'Hover':
            self.hover(element)
        elif action == 'Scroll Down':
            self.scroll_down()
        elif action == 'Scroll Up':
            self.scroll_up()
        elif action == 'Press Key':
            self.press_key(argument)
        elif action == 'Wait':
            self.wait()
        else:
            raise NotImplementedError()
        self.__update_screenshot__()

    def find_element_by_instruction(self, instruction):
        (center_x, center_y), bbox = get_relative_bbox_center(self.page, instruction, self.current_screenshot)
        return instruction, (center_x, center_y), bbox

    def screenshot_satisfies(self, condition):
        return screenshot_satisfies(self.engine, condition, self.current_screenshot)

    def quote(self, content):
        self.current_return = {"operation": "quote", "kwargs": {"content": content}}
        self.__update_screenshot__()

    def exit(self, message=None):
        self.current_return = {"operation": "exit", "kwargs": {"message": message}}
        self.action_return = create_stop_action(message)
        self.__update_screenshot__()

    # Implement sub-actions of do
    def click(self, element):
        instruction, (center_x, center_y), bbox = element
        self.action_return = create_click_action(center_x, center_y)
        self.current_return = {"operation": "do", "action": 'Click', "kwargs": {"instruction": instruction},
                               "bbox": bbox}

    def right_click(self, element):
        instruction, (center_x, center_y), bbox = element
        self.action_return = create_click_action(center_x, center_y, True)
        self.current_return = {"operation": "do", "action": 'Click', "kwargs": {"instruction": instruction},
                               "bbox": bbox}

    def type(self, argument, element):
        instruction, (center_x, center_y), bbox = element
        self.action_return = create_type_action(argument, center_x, center_y)
        self.current_return = {"operation": "do", "action": 'Type',
                               "kwargs": {"argument": argument, "instruction": instruction},
                               "bbox": bbox}

    def search(self, argument, element):
        instruction, (center_x, center_y), bbox = element
        self.action_return = create_type_action(argument + '\n', center_x, center_y, True)
        self.current_return = {"operation": "do", "action": 'Search',
                               "kwargs": {"argument": argument, "instruction": instruction},
                               "bbox": bbox}

    def hover(self, element):
        instruction, (center_x, center_y), bbox = element
        self.action_return = create_hover_action(center_x, center_y)
        self.current_return = {"operation": "do", "action": 'Hover', "kwargs": {"instruction": instruction},
                               "bbox": bbox}

    def scroll_up(self):
        self.action_return = create_scroll_action('up')
        self.current_return = {"operation": "do", "action": 'Scroll Up'}

    def scroll_down(self):
        self.action_return = create_scroll_action('down')
        self.current_return = {"operation": "do", "action": 'Scroll Down'}

    def press_key(self, argument):
        self.action_return = create_key_press_action(argument)
        self.current_return = {"operation": "do", "action": 'Press Key', "kwargs": {"argument": argument}}

    def wait(self):
        self.page.wait_for_timeout(5000)
        self.current_return = {"operation": "do", "action": 'Wait'}

