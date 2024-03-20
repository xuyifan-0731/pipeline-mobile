from page_executor import MobilePageExecutor
from recorder import JSONRecorder

from gpt4v import OpenaiEngine

from utils_mobile.utils import print_with_color
from utils_mobile.and_controller import AndroidController, list_all_devices

import os
import re
import sys
import time
import getpass
import datetime
from dotenv import load_dotenv

def get_code_snippet(content):
    code = re.search(r'```.*?\n([\s\S]+?)\n```', content)
    if code is None:
        print(content)
        raise RuntimeError()
    code = code.group(1)
    return code

def get_mobile_device():
    device_list = list_all_devices()
    if not device_list:
        print_with_color("ERROR: No device found!", "red")
        sys.exit()
    print_with_color(f"List of devices attached:\n{str(device_list)}", "yellow")
    if len(device_list) == 1:
        device = device_list[0]
        print_with_color(f"Device selected: {device}", "yellow")
    else:
        print_with_color("Please choose the Android device to start demo by entering its ID:", "blue")
        device = input()

    controller = AndroidController(device)
    width, height = controller.get_device_size()
    if not width and not height:
        print_with_color("ERROR: Invalid device size!", "red")
        sys.exit()
    print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")

    return controller


def run(controller, instruction=None, config = None) -> None:
    openai_engine = OpenaiEngine()
    if config is not None:
        TRACE_DIR = config["TRACE_DIR"]
        SCREENSHOT_DIR = config["SCREENSHOT_DIR"]
        XML_DIR = config["XML_DIR"]
    page_executor = MobilePageExecutor(context=controller, engine=openai_engine,
                                           screenshot_dir=SCREENSHOT_DIR)
    instruction = input("What would you like to do? >>> ") if instruction is None else instruction
    id = str(time.time())
    record = JSONRecorder(id = id, instruction=instruction, page_executor=page_executor, trace_dir=TRACE_DIR, xml_dir=XML_DIR)
    page_executor.update_screenshot(prefix=str(0))
    while record.turn_number <= 100:
        prompt = page_executor.__get_current_status__() if record.turn_number > 0 else instruction
        content = openai_engine.generate(prompt=prompt, image_path=page_executor.current_screenshot,
                                         turn_number=record.turn_number, ouput__0=record.format_history()
                                         ,sys_prompt="android_basic")
        record.update_response(controller, content)

        exe_res = page_executor(get_code_snippet(content))
        record.update_execution(exe_res)

        if exe_res['operation'] == 'exit':
            break

        record.turn_number += 1

        if page_executor.is_finish:
            print_with_color(f"Autonomous exploration completed successfully.", "yellow")
            page_executor.update_screenshot(prefix="end")
            break

def process_config():
    config = {}
    config_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(config_path)

    LOG_DIR = os.environ.get('LOG_DIR')
    config["LOG_DIR"] = LOG_DIR

    if LOG_DIR is None:
        LOG_DIR = '../logs'
    id = str(time.time())
    TRACE_DIR = os.path.join(LOG_DIR, id, 'traces')
    SCREENSHOT_DIR = os.path.join(LOG_DIR, id, 'Screen')
    XML_DIR = os.path.join(LOG_DIR, id, 'xml')
    Video_DIR = os.path.join(LOG_DIR, id, 'video')
    config["TRACE_DIR"] = TRACE_DIR
    config["SCREENSHOT_DIR"] = SCREENSHOT_DIR
    config["XML_DIR"] = XML_DIR
    config["Video_DIR"] = Video_DIR

    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(TRACE_DIR, exist_ok=True)
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(XML_DIR, exist_ok=True)
    return config
def main(instruction=None):
    controller = get_mobile_device()
    config = process_config()
    run(controller, instruction=instruction, config = config)


if __name__ == '__main__':
    # main()
    main('使用Amap，我需要去北京南站，请帮我查查打车和坐地铁大概分别最快需要多久')
    # main('I am in Beijing in Tsinghua University. Give me some choices about hotpot restaurants nearby.')
    # main("Sort products by price. Start on http://localhost:7770/sports-outdoors/hunting-fishing.html")
