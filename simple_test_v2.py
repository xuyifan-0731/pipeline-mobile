from playwright.sync_api import Playwright, sync_playwright
# from .gpt4v import OpenaiEngine

import requests
import re
import time
import cv2

# openai_engine = OpenaiEngine()

HISTORY = ""
CURRENT_SCREENSHOT = None
TURN_NUMBER = 0


def plot_bbox(bbox):
    global CURRENT_SCREENSHOT
    assert CURRENT_SCREENSHOT is not None
    image = cv2.imread(CURRENT_SCREENSHOT)
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 2)
    cv2.imwrite(CURRENT_SCREENSHOT.replace('.png', '-bbox.png'), image)


def click_relative_bbox_center(page, code):
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
    page.mouse.click(center_x, center_y)


def call_dino(instruction, screenshot_path):
    files = {'image': open(screenshot_path, 'rb')}
    response = requests.post("http://172.19.64.21:24026/v1/executor", files=files,
                             data={"text_prompt": f"{instruction}"})
    return [int(s) for s in response.json()['response'].split(',')]


def call_planner(prompt, screenshot_path):
    files = {'image': open(screenshot_path, 'rb')}
    response = requests.post("http://172.19.64.21:24025/v1/planner", files=files, data={"text_prompt": prompt})
    return response.json()["response"]


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
            click_relative_bbox_center(page, code)
        elif action == 'Type':
            click_relative_bbox_center(page, code)
            argument = re.search(r'argument="(.*?)"', code).group(1)
            print("Argument: " + argument)
            page.keyboard.type(argument)
        elif action == 'Scroll Down':
            page.mouse.wheel(0, 400)
        elif action == 'Scroll Up':
            page.mouse.wheel(0, -400)
        elif action == 'Press Key':
            argument = re.search(r'argument="(.*?)"', code).group(1)
            page.keyboard.press(argument)
        elif action == 'Go Backward':
            page.go_backward()
        elif action == 'Go Forward':
            page.go_forward()
        else:
            raise NotImplementedError()
    elif code.startswith('open_url'):
        url = re.search(r'url="(.*?)"', code).group(1)
        page.goto(url)
    elif code.startswith('exit'):
        return 0


def take_screenshot(page):
    global CURRENT_SCREENSHOT
    CURRENT_SCREENSHOT = f"temp/screenshot-{time.time()}.png"
    page.screenshot(path=CURRENT_SCREENSHOT)


# 创建浏览器
def run(playwright: Playwright) -> None:
    global HISTORY, CURRENT_SCREENSHOT, TURN_NUMBER
    # 创建浏览器
    browser = playwright.chromium.launch(headless=False)

    # 使用 selenium 如果要打开多个网页，需要创建多个浏览器，但是 playwright 中只需要创建多个上下文即可
    # 例如：content1 = browser.new_context()、content2 = browser.new_context() 分别去访问网页做处理
    content = browser.new_context()

    # 每个 content 就是一个会话窗口，可以创建自己的页面，也就是浏览器上的 tab 栏，在每个会话窗口中，可以创建多个页面，也就是多个 tab 栏
    # 例如：page1 = content.new_page()、page2 = content.new_page() 封面去访问页面
    page = content.new_page()
    instruction = input("What would you like to do? >>> ")
    initial_url = str(input("Initial URL (default Google) >>> ").strip() or "https://google.com")
    page.goto(initial_url)
    time.sleep(2)
    take_screenshot(page)

    while True:
        # content = openai_engine.generate(prompt=instruction, image_path=CURRENT_SCREENSHOT, turn_number=TURN_NUMBER,
        #                                  ouput__0=HISTORY)
        prompt = f"<|user|>\n{instruction}" if TURN_NUMBER == 0 else f"<|user|>\n{'** screenshot **'}"
        content = call_planner(HISTORY + '\n\n' + prompt, CURRENT_SCREENSHOT)
        HISTORY += ('\n\n' + prompt + content)
        print(content)

        if execution(content, page) == 0:
            break

        TURN_NUMBER += 1
        # input("Continue? >>>")

        # 保存截图
        time.sleep(2)
        take_screenshot(page)


if __name__ == '__main__':
    with sync_playwright() as playwright:
        run(playwright)
    # call_dino("the search bar", "../temp/screenshot-1706109765.033369.png")
