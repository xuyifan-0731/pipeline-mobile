import os

from .utils import get_relative_bbox_center, call_dino, plot_bbox
from .api_utils import screenshot_satisfies

import base64
import time
import inspect
import json
from functools import partial


class MobilePageExecutor:
    def __init__(self, context, engine, screenshot_dir):
        self.context = context
        self.device = context.device
        #self.page = page
        self.engine = engine
        self.screenshot_dir = screenshot_dir
        self.task_id = int(time.time())
        os.makedirs(f'{self.screenshot_dir}/{self.task_id}')

        self.new_page_captured = False
        self.current_screenshot = None
        self.current_return = None

        self.last_turn_element = None
        self.last_turn_element_tagname = None
        self.is_finish = False
        self.device_pixel_ratio = None

        # self.device_pixel_ratio = self.page.evaluate("window.devicePixelRatio")

    def __get_current_status__(self):
        page_position = None
        scroll_height = None
        status = {
            "Current URL": self.context.get_current_activity(),
        }
        return json.dumps(status, ensure_ascii=False)

    def __capture_new_page__(self, event):
        # delete
        self.new_page_captured = True
        event.wait_for_load_state(timeout=30000)
        self.page = event
        self.new_page_captured = False

    def __call__(self, code_snippet):
        '''
        self.new_page_captured = False
        self.context.on("page", self.__capture_new_page__)
        self.current_return = None'''

        local_context = self.__get_class_methods__()
        local_context.update(**{'self': self})
        print(code_snippet)
        exec(code_snippet, {}, local_context)
        '''
        if self.current_return['operation'] != 'do' or self.current_return['action'] not in {'Click', 'Right Click',
                                                                                             'Select Dropdown Option'}:
            self.last_turn_element, self.last_turn_element_tagname = None, None'''

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
        self.context.save_screenshot(self.current_screenshot)

    def __get_element_by_coordinates__(self, coordinates):
        x, y = coordinates
        return self.page.evaluate_handle(f"""() => document.elementFromPoint({x}, {y})""")

    def __get_select_element_options__(self, element):
        return [{"value": option.get_attribute('value'), "text": option.text_content().strip(' \n')} for option in
                element.query_selector_all("option")]

    def do(self, action=None, argument=None, element=None, **kwargs):
        assert action in ["Tap","Type","Swipe","Press Enter","Press Home","Press Back","Long Press"],"Unsupported Action"
        if action == "Tap":
            self.tap(element)
        elif action == "Type":
            self.type(argument, element)
        elif action == "Swipe":
            if "dist" in kwargs:
                self.swipe(argument, element, kwargs["dist"])
            else:
                self.swipe(argument, element)
        elif action == "Press Enter":
            self.press_enter(argument)
        elif action == "Press Home":
            self.press_home(argument)
        elif action == "Press Back":
            self.press_back(argument)
        elif action == "Long Press":
            self.long_press(element)
        else:
            raise NotImplementedError()
        self.__update_screenshot__()

    def get_relative_bbox_center(self, instruction, screenshot):
        # 获取相对 bbox
        relative_bbox = call_dino(instruction, screenshot)

        viewport_width,viewport_height = self.context.get_device_size()

        center_x = (relative_bbox[0] + relative_bbox[2]) / 2 * viewport_width / 1000
        center_y = (relative_bbox[1] + relative_bbox[3]) / 2 * viewport_height / 1000
        width_x = (relative_bbox[2] - relative_bbox[0]) * viewport_width / 1000
        height_y = (relative_bbox[3] - relative_bbox[1]) * viewport_height / 1000

        # 点击计算出的中心点坐标
        # print(center_x, center_y)
        plot_bbox([int(center_x - width_x / 2), int(center_y - height_y / 2), int(width_x), int(height_y)], screenshot, instruction)

        return (int(center_x), int(center_y)), relative_bbox

    def find_element_by_instruction(self, instruction):
        (center_x, center_y), bbox = self.get_relative_bbox_center(instruction, self.current_screenshot)
        '''
        self.last_turn_element = self.__get_element_by_coordinates__(
            (center_x / self.device_pixel_ratio, center_y / self.device_pixel_ratio)
        )  # save the element
        self.last_turn_element_tagname = self.last_turn_element.evaluate("element => element.tagName")'''
        return instruction, (center_x, center_y), bbox

    def screenshot_satisfies(self, condition):
        return screenshot_satisfies(self.engine, condition, self.current_screenshot)

    def exit(self, message=None):
        self.current_return = {"operation": "exit", "kwargs": {"message": message}}
        self.__update_screenshot__()

    def tap(self, element):
        instruction, (center_x, center_y), bbox = element
        self.context.tap(center_x, center_y)
        self.current_return = {"operation": "do", "action": 'Click', "kwargs": {"instruction": instruction},
                               "bbox": bbox}

    def long_press(self, element):
        instruction, (center_x, center_y), bbox = element
        self.context.long_press(center_x, center_y)
        self.current_return = {"operation": "do", "action": 'Long Press', "kwargs": {"instruction": instruction},
                               "bbox": bbox}

    def swipe(self, argument, element = None, dist = "medium"):
        if element is not None:
            instruction, (center_x, center_y), bbox = element
            self.context.swipe(center_x, center_y, argument, dist)
            self.current_return = {"operation": "do", "action": 'Swipe',
                                   "kwargs": {"argument": argument, "instruction": instruction, "dist": dist},
                                   "bbox": bbox}
        else:
            center_x, center_y = None, None
            self.context.swipe(center_x, center_y, argument, dist)
            self.current_return = {"operation": "do", "action": 'Swipe',
                                   "kwargs": {"argument": argument, "instruction": None, "dist": dist},
                                   "bbox": None}

    def type(self, argument, element = None):
        instruction = None
        bbox = None
        if element is not None:
            instruction, (center_x, center_y), bbox = element
            self.context.tap(center_x, center_y)
        self.context.text(argument)
        self.context.enter()
        self.current_return = {"operation": "do", "action": 'Type',
                               "kwargs": {"argument": argument, "instruction": instruction},
                               "bbox": bbox}

    def press_enter(self, argument):
        self.context.enter()
        self.current_return = {"operation": "do", "action": 'Press Enter', "kwargs": {"argument": argument}}

    def press_back(self, argument):
        self.context.back()
        self.current_return = {"operation": "do", "action": 'Press Back', "kwargs": {"argument": argument}}

    def press_home(self, argument):
        self.context.home()
        self.current_return = {"operation": "do", "action": 'Press Home', "kwargs": {"argument": argument}}

    def finish(self, message = None):
        self.is_finish = True
        self.current_return = {"operation": "do", "action": 'finish', "kwargs": {"message": message}}

    def wait(self):
        time.sleep(5)
        self.current_return = {"operation": "do", "action": 'Wait'}