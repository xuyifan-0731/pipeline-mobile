from ..page_executor import SyncVisualPageExecutor, WebarenaPageExecutor
from ..recorder import JSONRecorder

from playwright.sync_api import Playwright, sync_playwright
from ..gpt4v import OpenaiEngine

import os
import re
import getpass
from dotenv import load_dotenv

openai_engine = OpenaiEngine()
config_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(config_path)


def get_code_snippet(content):
    code = re.search(r'```.*?\n([\s\S]+?)\n```', content)
    if code is None:
        raise RuntimeError()
    code = code.group(1)
    return code


def run(playwright: Playwright, instruction=None) -> None:
    # 创建浏览器
    # 浏览器缓存(登录信息)/书签/个人偏好舍设置内容存储位置, 如下图
    __USER_DATE_DIR_PATH__ = f'/Users/{getpass.getuser()}/Library/Application Support/Google/Chrome/Default'
    # 要使用的浏览器位置
    __EXECUTABLE_PATH__ = r'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=__USER_DATE_DIR_PATH__,  # 指定本机用户缓存地址
        executable_path=__EXECUTABLE_PATH__,  # 指定本机google客户端exe的路径
        accept_downloads=True,  # 要想通过这个下载文件这个必然要开  默认是False
        headless=False,
        # no_viewport=True,                                      #  no_viewport=True '--start-maximized'同时存在,窗口最大化
        args=['--start-maximized', '--disable-blink-features=AutomationControlled'],  # 跳过检测
    )

    page = context.new_page()
    page_executor = WebarenaPageExecutor(context=context, page=page, engine=openai_engine,
                                           screenshot_dir=os.getenv('SCREENSHOT_DIR'))
    instruction = input("What would you like to do? >>> ") if instruction is None else instruction
    record = JSONRecorder(instruction=instruction, page_executor=page_executor)

    while record.turn_number <= 100:
        prompt = page_executor.__get_current_status__() if record.turn_number > 0 else instruction
        content = openai_engine.generate(prompt=prompt, image_path=page_executor.current_screenshot,
                                         turn_number=record.turn_number, ouput__0=record.format_history())
        record.update_response(page, content)
        print(content)

        exe_res = page_executor(get_code_snippet(content))
        record.update_execution(exe_res)
        if exe_res['operation'] == 'exit':
            break

        record.turn_number += 1
        # input("Continue? >>>")
        # page_executor.__update_screenshot__()


def main(instruction=None):
    with sync_playwright() as playwright:
        run(playwright, instruction=instruction)


if __name__ == '__main__':
    # main()
    main('Browse and list 3 latest paper authored by Google tweeted by my friend Aran Komatsuzaki on twitter, and help me \'like\' them. Start from twitter and find his profile.')
