from page_executor import MobilePageExecutor
from recorder import JSONRecorder
from tkinter import ttk


from utils_mobile.utils import print_with_color
from utils_mobile.label_utils import TouchEventParser
from utils_mobile.and_controller import AndroidController, list_all_devices

import tkinter as tk
from tkinter import messagebox

import os
import sys
import time

def is_utf8_chars(input_str):
    """
    Check if the input string consists solely of UTF-8 encoded characters.

    Args:
    input_str (str): The input string to check.

    Returns:
    bool: True if the input string is valid UTF-8, False otherwise.
    """
    try:
        # 先将字符串编码为UTF-8字节序列，然后尝试解码
        input_str.encode('utf-8').decode('utf-8')
        return True
    except UnicodeDecodeError:
        # 如果在解码过程中出现UnicodeDecodeError异常，则不是有效的UTF-8
        return False


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


def process_config(task, task_id, storage, platform):
    config = {}
    config["TASK_DESCRIPTION"] = task
    config["LOG_DIR"] = storage
    config["DEVICE"] = platform
    LOG_DIR = config["LOG_DIR"]
    config["TASK_DESCRIPTION"] = config["TASK_DESCRIPTION"].replace(' ', '_').replace('/', '_')

    assert task_id.isdigit(), "task_id must be an integer"

    id = str(task_id) + '_' + str(time.time())

    assert is_utf8_chars(id), "id must be valid UTF-8, delete Chinese words in the task description or path"

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

def main(task, taskid, storage, platform):
    config = process_config(task, taskid, storage, platform)
    controller = get_mobile_device()
    run(controller, config = config)

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("配置文件路径")
        self.geometry("800x800")

        self.initUI()


    def initUI(self):
        # 任务名称输入框
        self.task_label = tk.Label(self, text="当前任务:")
        self.task_label.pack(padx=5, pady=5)

        self.task_entry = tk.Entry(self)
        self.task_entry.pack(padx=5, pady=5, fill=tk.X, expand=True)

        self.task_idlabel = tk.Label(self, text="当前任务id:")
        self.task_idlabel.pack(padx=5, pady=5)

        self.task_identry = tk.Entry(self)
        self.task_identry.pack(padx=5, pady=5, fill=tk.X, expand=True)

        # 结果存储位置输入框
        self.storage_label = tk.Label(self, text="结果存储位置:")
        self.storage_label.pack(padx=5, pady=5)

        self.storage_entry = tk.Entry(self)
        self.storage_entry.pack(padx=5, pady=5, fill=tk.X, expand=True)

        # 平台选择下拉框
        self.platform_label = tk.Label(self, text="选择平台:")
        self.platform_label.pack(padx=5, pady=5)

        self.platform_combo = ttk.Combobox(self, values=["android", "huawei", "else"])
        self.platform_combo.pack(padx=5, pady=5, fill=tk.X, expand=True)

        # 执行按钮
        self.submit_button = tk.Button(self, text="执行", command=self.executeMain)
        self.submit_button.pack(side=tk.RIGHT, padx=5, pady=5)


    def executeMain(self):
        print(self.task_entry.get(), self.task_identry.get(), self.storage_entry.get(), self.platform_combo.get())

        if self.task_entry.get():
            main(self.task_entry.get(), self.task_identry.get(), self.storage_entry.get(), self.platform_combo.get())
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

