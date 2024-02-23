import os
import time
import re
import sys
sys.path.append('./')

import cv2
import json
import getpass
import requests

from dotenv import load_dotenv
from gpt4v import OpenaiEngine
from playwright.sync_api import Playwright, sync_playwright


config_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(config_path)


openai_engine = OpenaiEngine()

CURRENT_SCREENSHOT = None
TURN_NUMBER = 0

TRACE_DIR = os.getenv('TRACE_DIR')
SCREENSHOT_DIR = os.getenv('SCREENSHOT_DIR')

class Record:
    def __init__(self, instruction):
        self.id = int(time.time())
        self.instruction = instruction

        os.makedirs(f'{TRACE_DIR}/{self.id}', exist_ok=True)
        self.file_path = f'{TRACE_DIR}/{self.id}/{self.id}.jsonl'
        
        self.contents = []

    def update_response(self, page, response, prompt="<|user|>\n** screenshot **"):
        step = {
            "trace_id": self.id, "index": TURN_NUMBER,
            "prompt": prompt if TURN_NUMBER > 0 else f"<|user|>\n{self.instruction}", "image": CURRENT_SCREENSHOT,
            "response": response, "url": page.url, "window": page.viewport_size, "target": self.instruction
        }
        self.contents.append(step)

    def update_execution(self, exe_res):
        self.contents[-1]['parsed_action'] = exe_res
        
        with open(self.file_path, 'a') as f:
            f.write(json.dumps(self.contents[-1], ensure_ascii=False) + '\n')

    def format_history(self):
        history = []
        for turn in self.contents:
            history.append({"role": "user", "content": [{"type": "text", "text": turn['prompt']}]})
            history.append({"role": "assistant", "content": [{"type": "text", "text": turn['response']}]})
        return history
    
    def load_history(self, path):
        with open(path, 'r') as f:
            contents = [json.loads(line) for line in f]
        self.contents = contents
        self.file_path = path
        self.id = int(path.split("/")[-1].split(".jsonl")[0])
        self.instruction = contents[0]['prompt']

def plot_bbox(bbox):
    global CURRENT_SCREENSHOT
    assert CURRENT_SCREENSHOT is not None
    image = cv2.imread(CURRENT_SCREENSHOT)
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 2)
    cv2.imwrite(CURRENT_SCREENSHOT.replace('.png', '-bbox.png'), image)


def operate_relative_bbox_center(page, code, action, is_right=False):
    global CURRENT_SCREENSHOT
    # 获取相对 bbox
    dino_prompt = re.search('find_element_by_instruction\(instruction="(.*?)"\)', code).group(1)
    relative_bbox = call_dino(dino_prompt, CURRENT_SCREENSHOT)

    # 获取页面的视口大小
    viewport_size = page.viewport_size
    # print(viewport_size)
    viewport_width = viewport_size['width']
    viewport_height = viewport_size['height']

    center_x = (relative_bbox[0] + relative_bbox[2]) / 2 * viewport_width / 100
    center_y = (relative_bbox[1] + relative_bbox[3]) / 2 * viewport_height / 100
    width_x = (relative_bbox[2] - relative_bbox[0]) * viewport_width / 100
    height_y = (relative_bbox[3] - relative_bbox[1]) * viewport_height / 100

    # 点击计算出的中心点坐标
    # print(center_x, center_y)
    plot_bbox([int(center_x - width_x / 2), int(center_y - height_y / 2), int(width_x), int(height_y)])

    if action in {'Click', 'Right Click', 'Type', 'Search'}:
        page.mouse.click(center_x, center_y, button='right' if is_right else 'left')
    elif action == 'Hover':
        page.mouse.move(center_x, center_y)
        page.wait_for_timeout(500)
    else:
        raise NotImplementedError()

    return dino_prompt, relative_bbox


def call_dino(instruction, screenshot_path):
    files = {'image': open(screenshot_path, 'rb')}
    response = requests.post("http://172.19.64.21:24026/v1/executor", files=files,
                             data={"text_prompt": f"{instruction}"})
    return [int(s) for s in response.json()['response'].split(',')]
        
def execution(content, page, auto_executor = True):
    global CURRENT_SCREENSHOT
    code = re.search(r'```.*?\n(.*?)\n.*?```', content)
    if code is None:
        raise RuntimeError()
    code = code.group(1)
    if len(code.split('\n')) > 1:
        for line in code.split('\n'):
            if line.startswith('#'):
                continue
            code = line
            break
    if code.startswith('do'):
        action = re.search(r'action="(.*?)"', code).group(1)
        if not auto_executor:
            if action in ['Click','Right Click','Type','Search','Hover']:
                instruction = re.search('find_element_by_instruction\(instruction="(.*?)"\)', code).group(1)
                return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": None}
            elif action == "Press Key":
                argument = re.search(r'argument="(.*?)"', code).group(1)
                return {"operation": "do", "action": action, "kwargs": {"argument": argument}}
            else:
                return {"operation": "do", "action": action}
        
        if action == 'Click':
            instruction, bbox = operate_relative_bbox_center(page, code, action)
            return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": bbox}
        elif action == 'Right Click':
            instruction, bbox = operate_relative_bbox_center(page, code, action, is_right=True)
            return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": bbox}
        elif action in {'Type', 'Search'}:
            instruction, bbox = operate_relative_bbox_center(page, code, action)
            argument = re.search(r'argument="(.*?)"', code).group(1)
            print("Argument: " + argument)
            page.keyboard.press('Meta+A')
            page.keyboard.press('Backspace')
            page.keyboard.type(argument)
            if action == 'Search':
                page.keyboard.press('Enter')
            return {"operation": "do", "action": action, "kwargs": {"argument": argument, "instruction": instruction},
                    "bbox": bbox}
        elif action == 'Hover':
            instruction, bbox = operate_relative_bbox_center(page, code, action)
            return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": bbox}
        elif action == 'Scroll Down':
            page.mouse.wheel(0, page.viewport_size['height'] / 3 * 2)
            return {"operation": "do", "action": action}
        elif action == 'Scroll Up':
            page.mouse.wheel(0, -page.viewport_size['height'] / 3 * 2)
            return {"operation": "do", "action": action}
        elif action == 'Press Key':
            argument = re.search(r'argument="(.*?)"', code).group(1)
            page.keyboard.press(argument)
            return {"operation": "do", "action": action, "kwargs": {"argument": argument}}
        else:
            raise NotImplementedError()
    elif code.startswith('quote'):
        content = re.search(r'content="(.*?)"', code).group(1)
        return {"operation": "quote", "kwargs": {"content": content}}
    elif code.startswith('open_url'):
        url = re.search(r'url="(.*?)"', code).group(1)
        page.goto(url)
        return {"operation": "open_url", "kwargs": {"url": url}}
    elif code.startswith('exit'):
        return {"operation": "exit",
                "kwargs": {"message": re.search(r'message="(.*?)"', code).group(1) if 'exit()' not in code else ""}}


# 创建浏览器
def run(playwright: Playwright, instruction=None, auto_executor = True, history_path = None) -> None:
    global CURRENT_SCREENSHOT, TURN_NUMBER
    # 创建浏览器
    __USER_DATE_DIR_PATH__ = f'/Users/{getpass.getuser()}/Library/Application Support/Google/Chrome/Default'  # 浏览器缓存(登录信息)/书签/个人偏好舍设置内容存储位置, 如下图
    __EXECUTABLE_PATH__ = r'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'  # 要使用的浏览器位置

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=__USER_DATE_DIR_PATH__,  # 指定本机用户缓存地址
        executable_path=__EXECUTABLE_PATH__,  # 指定本机google客户端exe的路径
        accept_downloads=True,  # 要想通过这个下载文件这个必然要开  默认是False
        headless=False,
        # no_viewport=True,                                      #  no_viewport=True '--start-maximized'同时存在,窗口最大化
        args=['--start-maximized', '--disable-blink-features=AutomationControlled'],  # 跳过检测
    )

    # 使用 selenium 如果要打开多个网页，需要创建多个浏览器，但是 playwright 中只需要创建多个上下文即可
    # 例如：content1 = browser.new_context()、content2 = browser.new_context() 分别去访问网页做处理
    # content = browser.new_context()

    # 每个 content 就是一个会话窗口，可以创建自己的页面，也就是浏览器上的 tab 栏，在每个会话窗口中，可以创建多个页面，也就是多个 tab 栏
    # 例如：page1 = content.new_page()、page2 = content.new_page() 封面去访问页面
    page = context.new_page()
    instruction = input("What would you like to do? >>> ") if instruction is None else instruction
    record = Record(instruction=instruction)

    if history_path:
        record.load_history(history_path)

    while TURN_NUMBER <= 100:
        if not history_path:
            content = openai_engine.generate(prompt=instruction, image_path=CURRENT_SCREENSHOT, turn_number=TURN_NUMBER,
                                         ouput__0=record.format_history())
            record.update_response(page, content)
        else:
            content = record.contents[-1]['response']
            history_path = None
        print(content)

        new_page_captured = False

        # Prepare to capture the new page/tab
        def capture_new_page(event):
            nonlocal page, new_page_captured
            new_page_captured = True
            event.wait_for_load_state()
            page = event
            new_page_captured = False

        context.on("page", capture_new_page)

        exe_res = execution(content, page, auto_executor)
        record.update_execution(exe_res)
        if exe_res['operation'] == 'exit':
            break

        TURN_NUMBER += 1
        if not auto_executor:
            input("Finish the action and start to screenshot. >>> ")
        else:
            time.sleep(3)
        # 保存截图
        
        CURRENT_SCREENSHOT = f"{TRACE_DIR}/{record.id}/screenshot/{TURN_NUMBER-1}.png"
        _ = page.viewport_size
        page.screenshot(path="/dev/null")
        while new_page_captured:
            time.sleep(0.1)
        page.screenshot(path=CURRENT_SCREENSHOT)


def main(instruction=None, auto_executor = True, history_path = None):
    with sync_playwright() as playwright:
        run(playwright,instruction, auto_executor, history_path)


if __name__ == '__main__':
    
    instruction = '''open the url http://172.16.64.65:9999/forums and comment to the first post in the r/books with my comment "can't stop it".'''
    auto_executor = False
    
    # 恢复加载
    reload_history = True
    history_path = None

    if reload_history:
        TURN_NUMBER = 3
        history_path = "./traces/1708670656/1708670656.jsonl"

    main(instruction, auto_executor, history_path)
