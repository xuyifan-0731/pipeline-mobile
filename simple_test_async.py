import json

from playwright.sync_api import Playwright, sync_playwright
from playwright.async_api import Playwright, async_playwright
from Pipeline.gpt4v import OpenaiEngine
from collections import defaultdict

import requests
import PIL.Image
import re
import time
import cv2
import traceback
import asyncio
import os

openai_engine = OpenaiEngine()


class RepetitionException(Exception):
    pass


class Record:
    def __init__(self, instruction, url=None, _id=None, save_path=None):
        if save_path is None:
            save_path = '/Users/shaw/Desktop/Research/MegaPilot/UI-Detector/traces'
        self.id = int(time.time()) if _id is None else _id
        self.instruction = instruction
        self.url = url
        self.file_path = f'{save_path}/{self.id}.jsonl'
        self.contents = []
        self.hashed_actions = defaultdict(list)

    def check_abnormal_action(self, TURN_NUMBER):
        round_free_response = '\n'.join(self.contents[-1]['response'].split('\n')[1:])
        indexes = self.hashed_actions[round_free_response]
        return len(indexes) > 1 and indexes[-1] - indexes[-2] == TURN_NUMBER - indexes[-1]  # Repeition happens!

    def update_response(self, page, response, TURN_NUMBER, CURRENT_SCREENSHOT, prompt="<|user|>\n** screenshot **"):
        step = {
            "trace_id": self.id, "index": TURN_NUMBER,
            "prompt": prompt if TURN_NUMBER > 0 else f"<|user|>\n{self.instruction}", "image": CURRENT_SCREENSHOT,
            "response": response, "url": page.url, "window": page.viewport_size, "target": self.instruction
        }
        self.contents.append(step)

    def update_execution(self, exe_res, TURN_NUMBER):
        self.contents[-1]['parsed_action'] = exe_res

        # check abnormal action (looping)
        if exe_res is not None and self.check_abnormal_action(TURN_NUMBER):
            raise RepetitionException()

        self.contents[-1]['status'] = 0 if exe_res is not None else 1  # 1 refers to error in execution
        if exe_res is not None:
            self.hashed_actions['\n'.join(self.contents[-1]['response'].split('\n')[1:])].append(TURN_NUMBER)
        with open(self.file_path, 'a') as f:
            f.write(json.dumps(self.contents[-1], ensure_ascii=False) + '\n')


async def is_clickable(page, x, y):
    return await page.evaluate(f'''
    (() => {{
        const elem = document.elementFromPoint({x}, {y});
        if (!elem) return false; // No element at this position
        
        const style = window.getComputedStyle(elem);
        const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
        const isNotDisabled = !elem.disabled;
        // Infer clickability based on tag name, roles, or other attributes
        const isLikelyClickable = elem.tagName === 'A' && elem.hasAttribute('href') || elem.tagName === 'BUTTON' || elem.getAttribute('role') === 'button' || elem.hasAttribute('href');
        
        return isVisible && isNotDisabled && isLikelyClickable;
    }})()
    ''')


def check_screenshot_the_same(screenshot_1, screenshot_2):
    image1 = list(PIL.Image.open(screenshot_1).getdata())
    image2 = list(PIL.Image.open(screenshot_2).getdata())
    return image1 == image2


def plot_bbox(bbox, CURRENT_SCREENSHOT):
    # global CURRENT_SCREENSHOT
    assert CURRENT_SCREENSHOT is not None
    image = cv2.imread(CURRENT_SCREENSHOT)
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 2)
    cv2.imwrite(CURRENT_SCREENSHOT.replace('.png', '-bbox.png'), image)


async def operate_relative_bbox_center(page, code, action, CURRENT_SCREENSHOT, is_right=False):
    # global CURRENT_SCREENSHOT
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
    is_clickable_val = True  # await is_clickable(page, center_x, center_y)
    plot_bbox([int(center_x - width_x / 2), int(center_y - height_y / 2), int(width_x), int(height_y)],
              CURRENT_SCREENSHOT)

    if action in {'Click', 'Right Click', 'Type'}:
        await page.mouse.click(center_x, center_y, button='right' if is_right else 'left')
    elif action == 'Hover':
        await page.mouse.move(center_x, center_y)
        await page.wait_for_timeout(500)
    else:
        raise NotImplementedError()

    return dino_prompt, relative_bbox, is_clickable_val


def call_dino(instruction, screenshot_path):
    files = {'image': open(screenshot_path, 'rb')}
    response = requests.post("http://172.19.64.21:24026/v1/executor", files=files,
                             data={"text_prompt": f"{instruction}"})
    return [int(s) for s in response.json()['response'].split(',')]


async def execution(content, page, CURRENT_SCREENSHOT):
    # global CURRENT_SCREENSHOT
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
            instruction, bbox, is_clickable_val = await operate_relative_bbox_center(page, code, action,
                                                                                     CURRENT_SCREENSHOT)
            return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": bbox,
                    "is_not_clickable": not is_clickable_val}
        elif action == 'Right Click':
            instruction, bbox, is_clickable_val = await operate_relative_bbox_center(page, code, action,
                                                                                     CURRENT_SCREENSHOT, is_right=True)
            return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": bbox,
                    "is_not_clickable": not is_clickable_val}
        elif action == 'Type':
            instruction, bbox, is_clickable_val = await operate_relative_bbox_center(page, code, action,
                                                                                     CURRENT_SCREENSHOT)
            argument = re.search(r'argument="(.*?)"', code).group(1)
            print("Argument: " + argument)
            await page.keyboard.press('Meta+A')
            await page.keyboard.press('Backspace')
            await page.keyboard.type(argument)
            return {"operation": "do", "action": action, "kwargs": {"argument": argument, "instruction": instruction},
                    "bbox": bbox, "is_not_clickable": not is_clickable_val}
        elif action == 'Hover':
            instruction, bbox, is_clickable_val = await operate_relative_bbox_center(page, code, action,
                                                                                     CURRENT_SCREENSHOT)
            return {"operation": "do", "action": action, "kwargs": {"instruction": instruction}, "bbox": bbox,
                    "is_not_clickable": not is_clickable_val}
        elif action == 'Scroll Down':
            await page.mouse.wheel(0, page.viewport_size['height'] / 3 * 2)
            return {"operation": "do", "action": action}
        elif action == 'Go Backward':
            await page.go_back()
            return {"operation": "do", "action": action}
        elif action == 'Scroll Up':
            await page.mouse.wheel(0, -page.viewport_size['height'] / 3 * 2)
            return {"operation": "do", "action": action}
        elif action == 'Press Key':
            argument = re.search(r'argument="(.*?)"', code).group(1)
            await page.keyboard.press(argument)
            return {"operation": "do", "action": action, "kwargs": {"argument": argument}}
        else:
            raise NotImplementedError()
    elif code.startswith('quote'):
        content = re.search(r'content="(.*?)"', code).group(1)
        return {"operation": "quote", "kwargs": {"content": content}}
    elif code.startswith('open_url'):
        url = re.search(r'url="(.*?)"', code).group(1)
        await page.goto(url)
        return {"operation": "open_url", "kwargs": {"url": url}}
    elif code.startswith('exit'):
        return {"operation": "exit",
                "kwargs": {"message": re.search(r'message="(.*?)"', code).group(1) if 'exit()' not in code else ""}}


# 创建浏览器
async def run(playwright: Playwright, instruction=None, _id=None, url=None, screenshot_temp='temp',
              record_temp=None) -> None:
    # global HISTORY, CURRENT_SCREENSHOT, TURN_NUMBER
    # 创建浏览器
    # user_data_dir = '/Users/shaw/Library/Application Support/Google/Chrome/Default'
    # executable_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    # context = playwright.chromium.launch_persistent_context(user_data_dir, executable_path=executable_path,
    #                                                         headless=False)

    # context = playwright.chromium.connect_over_cdp("ws://localhost:9222")

    __USER_DATE_DIR_PATH__ = r'/Users/shaw/Library/Application Support/Google/Chrome/Default'  # 浏览器缓存(登录信息)/书签/个人偏好舍设置内容存储位置, 如下图
    __EXECUTABLE_PATH__ = r'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'  # 要使用的浏览器位置

    # playwright.chromium.set_default_navigation_timeout(60000)
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=__USER_DATE_DIR_PATH__,  # 指定本机用户缓存地址
        executable_path=__EXECUTABLE_PATH__,  # 指定本机google客户端exe的路径
        accept_downloads=True,  # 要想通过这个下载文件这个必然要开  默认是False
        headless=True,
        # no_viewport=True,                                      #  no_viewport=True '--start-maximized'同时存在,窗口最大化
        args=['--start-maximized', '--disable-blink-features=AutomationControlled'],  # 跳过检测
    )

    # 使用 selenium 如果要打开多个网页，需要创建多个浏览器，但是 playwright 中只需要创建多个上下文即可
    # 例如：content1 = browser.new_context()、content2 = browser.new_context() 分别去访问网页做处理
    # content = browser.new_context()

    # 每个 content 就是一个会话窗口，可以创建自己的页面，也就是浏览器上的 tab 栏，在每个会话窗口中，可以创建多个页面，也就是多个 tab 栏
    # 例如：page1 = content.new_page()、page2 = content.new_page() 封面去访问页面
    HISTORY = ""
    CURRENT_SCREENSHOT = None
    TURN_NUMBER = 0

    page = await context.new_page()
    instruction = input("What would you like to do? >>> ") if instruction is None else instruction
    record = Record(instruction=instruction, url=url, _id=_id, save_path=record_temp)
    final_status = {}

    try:
        while TURN_NUMBER <= 100:
            page.set_default_timeout(60000)
            content = openai_engine.generate(prompt=instruction, image_path=CURRENT_SCREENSHOT, turn_number=TURN_NUMBER,
                                             ouput__0=HISTORY)
            record.update_response(page, content, CURRENT_SCREENSHOT=CURRENT_SCREENSHOT, TURN_NUMBER=TURN_NUMBER)
            HISTORY += content
            print(content)

            new_page_captured = False

            # Prepare to capture the new page/tab
            async def capture_new_page(event):
                nonlocal page, new_page_captured
                new_page_captured = True
                await event.wait_for_load_state()
                page = event
                new_page_captured = False

            context.on("page", capture_new_page)

            # Do execution
            exe_res = await execution(content, page, CURRENT_SCREENSHOT)
            if exe_res['operation'] == 'exit':
                break

            # Get new screeshot
            await page.screenshot(path="/dev/null")
            time.sleep(3)
            LAST_SCREENSHOT = CURRENT_SCREENSHOT
            CURRENT_SCREENSHOT = f"{screenshot_temp}/screenshot-{time.time()}.png"
            while new_page_captured:
                time.sleep(0.1)
            await page.screenshot(path=CURRENT_SCREENSHOT)

            # If operating on unclickable element
            if exe_res.get('action') in {'Click', 'Right Click', 'Type', 'Hover'}:
                if check_screenshot_the_same(CURRENT_SCREENSHOT, LAST_SCREENSHOT):
                    HISTORY += '\n* Operation feedback: the element is plain text or not clickable.'
                    print("* Operation feedback: the page does not change.")
                else:
                    # print("* Operation feedback: the element is clickable.")
                    pass
            record.update_execution(exe_res, TURN_NUMBER)
            TURN_NUMBER += 1

    except RepetitionException as e:
        final_status = {"status": 2, "reason": "Repetition captured.", "turns": TURN_NUMBER}
        record.update_execution(None, TURN_NUMBER)
    except NotImplementedError as e:
        final_status = {"status": 1, "reason": "Not implemented action.", "traceback": traceback.format_exc(),
                        "turns": TURN_NUMBER}
        record.update_execution(None, TURN_NUMBER)
    except:
        final_status = {"status": 1, "reason": "Undefined failure during operation.",
                        "traceback": traceback.format_exc(),
                        "turns": TURN_NUMBER}
        record.update_execution(None, TURN_NUMBER)

    if len(final_status) == 0:
        if TURN_NUMBER > 100:
            final_status = {"status": 1, "reason": "Operating turns exceeded 100.", "turns": TURN_NUMBER}
        else:
            final_status = {"status": 0, "reason": "Normal end.", "turns": TURN_NUMBER}

    with open(f'{record_temp}/status.json', 'w') as f:
        json.dump(final_status, f, ensure_ascii=False, indent=4)
    print(final_status)


async def main(instruction=None, _id=None, url=None, screenshot_temp=None, record_temp=None):
    async with async_playwright() as playwright:
        await run(playwright, instruction=instruction, _id=_id, url=url, screenshot_temp=screenshot_temp,
                  record_temp=record_temp)


if __name__ == '__main__':
    # with sync_playwright() as playwright:
    #     run(playwright)
    asyncio.run(main())
