import os

from .utils import get_relative_bbox_center
from .api_utils import screenshot_satisfies

import time
import inspect
import json
import signal
import shutil
from functools import partial

from ..webarena_tools import (
    map_keys,
    map_url_to_real,
    map_url_to_local,
    create_none_action,
    create_stop_action,
    create_click_action,
    create_hover_action,
    create_type_action,
    create_key_press_action,
    create_goto_url_action,
    create_scroll_action
)

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException

signal.signal(signal.SIGALRM, timeout_handler)


class WebarenaPageExecutor:
    def __init__(self, context, page, engine, screenshot_dir, options={}):
        self.context = context
        self.page = page
        self.engine = engine
        self.screenshot_dir = screenshot_dir
        self.task_id = int(options.get("task_id", time.time()))
        
        output_dir = os.path.join(self.screenshot_dir, f"{self.task_id}")
        os.makedirs(output_dir, exist_ok=True)
        shutil.rmtree(output_dir)

        self.new_page_captured = False
        self.current_screenshot = None
        self.current_return = None
        self.action_return = create_none_action()
        self.mac_platform = False if "Mac" not in self.page.evaluate("navigator.platform") else True

    def __get_current_status__(self):
        status = {
            "Current URL": map_url_to_real(self.page.url),
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
        
        signal.alarm(30)
        try:
            exec(code_snippet, {}, local_context)
            signal.alarm(0)
        except:
            error_msg = f"The following code generates an unexpected error, you should NEVER try this again:\n```\n{code_snippet}\n```"
            self.current_return = {"operation": "quote", "kwargs": {"content": error_msg}}
            action = create_none_action()
            action["text"] = error_msg
            self.action_return = action
        
            
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
        current_screenshot = os.path.join(self.screenshot_dir, f"{self.task_id}", f"screenshot-{time.time()}.png")
        _ = self.page.viewport_size
        self.page.screenshot(path="/dev/null")
        while self.new_page_captured:
            time.sleep(0.1)
        self.page.screenshot(path=current_screenshot)
        
        self.current_screenshot = current_screenshot
        print(f"Screenshot saved at {self.current_screenshot}.")

    def reach_page_bottom(self):
        scroll_position = self.page.evaluate("window.pageYOffset")  # Current scroll position from the top
        total_height = self.page.evaluate("document.body.scrollHeight")  # Total scrollable height
        inner_height = self.page.evaluate("window.innerHeight")  # Height of the viewport

        # Determine if scrolled to bottom
        val = scroll_position + inner_height >= total_height
        print(f"Call reach_page_bottom():\n{val}")
        return val

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

    def open_url(self, url):
        local_url = map_url_to_local(url)
        self.page.goto(local_url)
        self.current_return = {"operation": "open_url", "kwargs": {"url": url}}
        self.action_return = create_goto_url_action(local_url)
        self.__update_screenshot__()
        
    def quote(self, content):
        self.current_return = {"operation": "quote", "kwargs": {"content": content}}
        self.action_return = create_none_action()
        self.__update_screenshot__()

    def exit(self, message=None):
        self.current_return = {"operation": "exit", "kwargs": {"message": message}}
        self.action_return = create_stop_action(message)
        self.__update_screenshot__()

    # Implement sub-actions of do
    def click(self, element):
        instruction, (center_x, center_y), bbox = element
        self.page.mouse.click(center_x, center_y)
        self.action_return = create_click_action(center_x, center_y)
        self.current_return = {"operation": "do", "action": 'Click', "kwargs": {"instruction": instruction},
                               "bbox": bbox}

    def right_click(self, element):
        instruction, (center_x, center_y), bbox = element
        self.page.mouse.click(center_x, center_y, button="right")
        self.action_return = create_click_action(center_x, center_y, True)
        self.current_return = {"operation": "do", "action": 'Click', "kwargs": {"instruction": instruction},
                               "bbox": bbox}

    def type(self, argument, element):
        instruction, (center_x, center_y), bbox = element
        self.page.mouse.click(center_x, center_y, button='left')
        self.page.keyboard.press(self.match_key('Meta+A'))
        self.page.keyboard.press('Backspace')
        self.page.keyboard.type(self.match_key(argument))
        self.action_return = create_type_action(argument, center_x, center_y)
        self.current_return = {"operation": "do", "action": 'Type',
                               "kwargs": {"argument": argument, "instruction": instruction},
                               "bbox": bbox}

    def search(self, argument, element):
        instruction, (center_x, center_y), bbox = element
        self.page.mouse.click(center_x, center_y, button='left')
        self.page.keyboard.press(self.match_key('Meta+A'))
        self.page.keyboard.press('Backspace')
        self.page.keyboard.type(self.match_key(argument))
        self.page.keyboard.press('Enter')
        self.action_return = create_type_action(argument + '\n', center_x, center_y, True)
        self.current_return = {"operation": "do", "action": 'Search',
                               "kwargs": {"argument": argument, "instruction": instruction},
                               "bbox": bbox}

    def hover(self, element):
        instruction, (center_x, center_y), bbox = element
        self.page.mouse.move(center_x, center_y)
        self.page.wait_for_timeout(500)
        self.action_return = create_hover_action(center_x, center_y)
        self.current_return = {"operation": "do", "action": 'Hover', "kwargs": {"instruction": instruction},
                               "bbox": bbox}

    def scroll_up(self):
        self.page.mouse.wheel(0, -self.page.viewport_size['height'] * 2.0 / 3)
        self.action_return = create_scroll_action('up')
        self.current_return = {"operation": "do", "action": 'Scroll Up'}

    def scroll_down(self):
        self.page.mouse.wheel(0, self.page.viewport_size['height'] * 2.0 / 3)
        self.action_return = create_scroll_action('down')
        self.current_return = {"operation": "do", "action": 'Scroll Down'}

    def press_key(self, argument):
        self.page.keyboard.press(self.match_key(argument))
        self.action_return = create_key_press_action(argument)
        self.current_return = {"operation": "do", "action": 'Press Key', "kwargs": {"argument": argument}}

    def wait(self):
        self.page.wait_for_timeout(5000)
        self.action_return = create_none_action()
        self.current_return = {"operation": "do", "action": 'Wait'}
        
    def match_key(self, key_comb: str):
        key = map_keys(key_comb)
        if "Meta" in key and not self.mac_platform:
            key = key.replace("Meta", "Control")        
        return key
