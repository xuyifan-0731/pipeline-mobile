from page_executor import MobilePageExecutor
from recorder import JSONRecorder
import tkinter as tk
import argparse
from gpt4v import OpenaiEngine

from utils_mobile.utils import print_with_color
from utils_mobile.label_utils import TouchEventParser
from utils_mobile.and_controller import AndroidController, list_all_devices

import tkinter as tk
from tkinter import filedialog, messagebox

import os
import re
import sys
import time
import yaml
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

def get_planner(engine, prompt, page_executor, record, config, app):
    content = engine.generate(prompt=prompt, image_path=page_executor.current_screenshot,
                                     turn_number=record.turn_number, ouput__0=record.format_history()
                                     , sys_prompt=config["PROMPT"], app=app)
    return content

def run(controller, config = None, app = None) -> None:
    if config is not None:
        TRACE_DIR = config["TRACE_DIR"]
        SCREENSHOT_DIR = config["SCREENSHOT_DIR"]
        XML_DIR = config["XML_DIR"]
    page_executor = MobilePageExecutor(context=controller, screenshot_dir=SCREENSHOT_DIR)
    instruction = config["TASK_DESCRIPTION"]
    id = str(time.time())
    record = JSONRecorder(id = id, instruction=instruction, page_executor=page_executor, trace_dir=TRACE_DIR, xml_dir=XML_DIR)

    root = tk.Tk()
    parser = TouchEventParser(root, page_executor, controller, config, record)
    parser.create_gui()
    parser.run()
    root.mainloop()

    print_with_color(f"Autonomous exploration completed successfully.", "yellow")


def process_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f.read(), Loader=yaml.FullLoader)

    LOG_DIR = config["LOG_DIR"]
    config["TASK_DESCRIPTION"] = config["TASK_DESCRIPTION"].replace(' ', '_').replace('/', '_')
    id = config["TASK_DESCRIPTION"][:32] + '_' + str(time.time())
    SAVE_DIR = os.path.join(LOG_DIR, id)
    TRACE_DIR = os.path.join(LOG_DIR, id, 'traces')
    SCREENSHOT_DIR = os.path.join(LOG_DIR, id, 'Screen')
    XML_DIR = os.path.join(LOG_DIR, id, 'xml')
    Video_DIR = os.path.join(LOG_DIR, id, 'video')
    config["SAVE_DIR"] = SAVE_DIR
    config["TRACE_DIR"] = TRACE_DIR
    config["SCREENSHOT_DIR"] = SCREENSHOT_DIR
    config["XML_DIR"] = XML_DIR
    #config["Video_DIR"] = Video_DIR

    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(TRACE_DIR, exist_ok=True)
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(XML_DIR, exist_ok=True)
    return config

def main(config_path = "config_files/label.yaml"):
    config = process_config(config_path)
    controller = get_mobile_device()
    run(controller, config = config)

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("配置文件路径输入")
        self.geometry("400x100")

        self.initUI()

    def initUI(self):
        self.label = tk.Label(self, text="请输入或选择config_path:")
        self.label.pack(padx=5, pady=5)

        self.entry = tk.Entry(self)
        self.entry.pack(padx=5, pady=5, fill=tk.X, expand=True)

        default_config_path = "config_files/label.yaml"
        self.entry.insert(0, default_config_path)

        self.browse_button = tk.Button(self, text="浏览", command=self.browseFile)
        self.browse_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.submit_button = tk.Button(self, text="执行", command=self.executeMain)
        self.submit_button.pack(side=tk.RIGHT, padx=5, pady=5)

    def browseFile(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, file_path)

    def executeMain(self):
        config_path = self.entry.get()
        if config_path:
            main(config_path)
            messagebox.showinfo("成功", "操作完成！")
        else:
            messagebox.showerror("错误", "请输入配置文件路径！")

if __name__ == '__main__':

    app = Application()
    app.mainloop()

'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='请给出label.yaml的路径')
    parser.add_argument('--yaml_path', type=str, default='config_files/label.yaml')
    args = parser.parse_args()
    main(config_path = "config_files/label.yaml")'''

