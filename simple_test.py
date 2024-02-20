import json

from playwright.sync_api import Playwright, sync_playwright
from Pipeline.gpt4v import OpenaiEngine

import requests
import PIL.Image
import re
import time
import cv2
import os

openai_engine = OpenaiEngine()

HISTORY = ""
CURRENT_SCREENSHOT = None
TURN_NUMBER = 0


class Record:
    def __init__(self, instruction):
        self.id = int(time.time())
        self.instruction = instruction
        self.file_path = f'/Users/shaw/Desktop/Research/MegaPilot/UI-Detector/traces/{self.id}.jsonl'
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


def plot_bbox(bbox):
    global CURRENT_SCREENSHOT
    assert CURRENT_SCREENSHOT is not None
    image = cv2.imread(CURRENT_SCREENSHOT)
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 2)
    cv2.imwrite(CURRENT_SCREENSHOT.replace('.png', '-bbox.png'), image)


def check_screenshot_the_same(screenshot_1, screenshot_2):
    image1 = list(PIL.Image.open(screenshot_1).getdata())
    image2 = list(PIL.Image.open(screenshot_2).getdata())
    return image1 == image2


def operate_relative_bbox_center(page, code, action, is_right=False):
    global CURRENT_SCREENSHOT
    # 获取相对 bbox
    dino_prompt = re.search('find_element_by_instruction\(instruction="(.*?)"\)', code).group(1)
    relative_bbox = call_dino(dino_prompt, CURRENT_SCREENSHOT)

    # 获取页面的视口大小
    viewport_size = page.viewport_size
    print(viewport_size)
    viewport_width = viewport_size['width']
    viewport_height = viewport_size['height']

    center_x = (relative_bbox[0] + relative_bbox[2]) / 2 * viewport_width / 100
    center_y = (relative_bbox[1] + relative_bbox[3]) / 2 * viewport_height / 100
    width_x = (relative_bbox[2] - relative_bbox[0]) * viewport_width / 100
    height_y = (relative_bbox[3] - relative_bbox[1]) * viewport_height / 100

    # 点击计算出的中心点坐标
    print(center_x, center_y)
    plot_bbox([int(center_x - width_x / 2), int(center_y - height_y / 2), int(width_x), int(height_y)])

    if action in {'Click', 'Right Click', 'Type'}:
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


def execution(content, page):
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
        if action == 'Click':
            instruction, bbox = operate_relative_bbox_center(page, code, action)
            return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": bbox}
        elif action == 'Right Click':
            instruction, bbox = operate_relative_bbox_center(page, code, action, is_right=True)
            return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": bbox}
        elif action == 'Type':
            instruction, bbox = operate_relative_bbox_center(page, code, action)
            argument = re.search(r'argument="(.*?)"', code).group(1)
            print("Argument: " + argument)
            page.keyboard.press('Meta+A')
            page.keyboard.press('Backspace')
            page.keyboard.type(argument)
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
def run(playwright: Playwright, instruction=None) -> None:
    global HISTORY, CURRENT_SCREENSHOT, TURN_NUMBER
    # 创建浏览器
    # user_data_dir = '/Users/shaw/Library/Application Support/Google/Chrome/Default'
    # executable_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    # context = playwright.chromium.launch_persistent_context(user_data_dir, executable_path=executable_path,
    #                                                         headless=False)

    # context = playwright.chromium.connect_over_cdp("ws://localhost:9222")

    __USER_DATE_DIR_PATH__ = r'/Users/shaw/Library/Application Support/Google/Chrome/Default'  # 浏览器缓存(登录信息)/书签/个人偏好舍设置内容存储位置, 如下图
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

    while TURN_NUMBER <= 100:
        content = openai_engine.generate(prompt=instruction, image_path=CURRENT_SCREENSHOT, turn_number=TURN_NUMBER,
                                         ouput__0=HISTORY)
        record.update_response(page, content)
        HISTORY += content
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

        exe_res = execution(content, page)
        record.update_execution(exe_res)
        if exe_res['operation'] == 'exit':
            break

        # Get new screeshot
        page.screenshot(path="/dev/null")
        time.sleep(3)
        LAST_SCREENSHOT = CURRENT_SCREENSHOT
        CURRENT_SCREENSHOT = f"temp/screenshot-{time.time()}.png"
        while new_page_captured:
            time.sleep(0.1)
        page.screenshot(path=CURRENT_SCREENSHOT)

        # If operating on unclickable element
        if exe_res.get('action') in {'Click', 'Right Click', 'Type', 'Hover'}:
            if check_screenshot_the_same(CURRENT_SCREENSHOT, LAST_SCREENSHOT):
                HISTORY += '\n* Operation feedback: the page does not change.'
                print("* Operation feedback: the page does not change.")
            else:
                # print("* Operation feedback: the element is clickable.")
                pass
        record.update_execution(exe_res)
        TURN_NUMBER += 1


def main(instruction=None):
    with sync_playwright() as playwright:
        run(playwright)


if __name__ == '__main__':
    main()
