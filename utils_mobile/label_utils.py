import tkinter as tk
from tkinter import simpledialog, messagebox
from utils_mobile.utils import print_with_color
import threading
import subprocess
import re
import sys

def get_screen_max_values():
    # 执行ADB命令获取设备的事件信息
    command_output = subprocess.run(['adb', 'shell', 'getevent', '-p'], stdout=subprocess.PIPE, text=True).stdout

    # 使用正则表达式匹配宽（0035）和高（0036）的max值
    max_values_pattern = re.compile(r'003[56].*max (\d+)')

    # 使用字典存储宽和高的max值
    max_values = {'width': 0, 'height': 0}

    # 搜索匹配项并存储结果
    for line in command_output.split('\n'):
        match = max_values_pattern.search(line)
        if match:
            if '0035' in line:
                max_values['width'] = int(match.group(1))
            elif '0036' in line:
                max_values['height'] = int(match.group(1))

    # 检查是否成功获取到值
    if max_values['width'] == 0 or max_values['height'] == 0:
        print("无法获取屏幕的max宽度和高度值。请确保设备已连接且adb命令运行正常。")
    else:
        print_with_color(f"屏幕宽度的max值为：{max_values['width']}, 屏幕高度的max值为：{max_values['height']}",'yellow')

    return max_values

def parse_event(output, max_values):

    coord_pattern = re.compile(r'ABS_MT_POSITION_(X|Y)\s+([a-fA-F0-9]+)')
    touch_position = {'X': None, 'Y': None}
    match = coord_pattern.search(output)
    #print(output,match)
    if match:
        axis, value = match.groups()
        value = int(value, 16)  # 将16进制值转换为十进制
        touch_position[axis] = value
        #print(touch_position)
        # 当两个坐标都更新后，打印和保存
        X,Y = None,None
        if touch_position['X'] is not None:
            X = touch_position['X']/max_values["width"]
            touch_position['X'] = X
        if touch_position['Y'] is not None:
            Y = touch_position['Y']/max_values["height"]
            touch_position['Y'] = Y
        return X, Y

class TouchEventParser:
    def __init__(self, root, page_executor, controller, config, recorder=None):
        self.root = root
        self.reset()
        self.events = []
        self.page_executor = page_executor
        self.max_values = None
        self.begin = False
        self.recorder = recorder
        self.controller = controller
        self.block = False
        self.config = config

    def reset(self):
        # Reset tracking states and coordinates
        self.is_tracking = False
        self.is_click = True
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.key_down = {}

    def save_click_or_swipe(self):
        if self.is_click:
            if self.start_x is not None and self.start_y is not None:
                self.events.append(f"Click at: ({self.start_x}, {self.start_y})")
                event = {"type": "click", "position_start": (self.start_x, self.start_y)}
                self.add_new_event(event)
            else:
                self.reset()
        else:
            dx = abs(self.end_x - self.start_x) if self.start_x is not None and self.end_x is not None else 0
            dy = abs(self.end_y - self.start_y) if self.start_y is not None and self.end_y is not None else 0

            # 检查是否为滑动
            if dx > 0.05 or dy > 0.05:
                # 认为是滑动
                self.events.append(
                    f"Swipe from: ({self.start_x}, {self.start_y}) to ({self.end_x}, {self.end_y})")
                event = {"type": "swipe", "position_start": (self.start_x, self.start_y),
                         "position_end": (self.end_x, self.end_y)}
                self.add_new_event(event)
            else:
                click_x = (self.start_x + self.end_x) / 2 if self.end_x is not None else self.start_x
                click_y = (self.start_y + self.end_y) / 2 if self.end_y is not None else self.start_y
                self.events.append(f"Click at: ({click_x}, {click_y})")
                event = {"type": "click", "position_start": (click_x, click_y)}
                self.add_new_event(event)

    def parse_press(self, line):
        key_pattern = re.compile(r'EV_KEY\s+(KEY_[A-Z0-9_]+)\s+(DOWN|UP)')
        key_match = key_pattern.search(line)
        if key_match:
            key_name, key_action = key_match.groups()
            # 检查按键DOWN-UP完整性
            if key_action == "DOWN":
                if key_name in self.key_down:
                    raise ValueError(f"Error: {key_name} DOWN received twice without UP.")
                self.key_down[key_name] = True  # 标记为按下状态
            elif key_action == "UP":
                if key_name not in self.key_down:
                    raise ValueError(f"Error: {key_name} UP received without a corresponding DOWN.")
                del self.key_down[key_name]  # 移除按下状态
                self.events.append(f"Key event: {key_name} pressed")  # 只有成功的DOWN-UP序列才记录为事件
                event = {"type": "press_key", "key_name": key_name}
                self.add_new_event(event)

    def parse_android(self, line):
        coord_info = parse_event(line, self.max_values)
        if "ABS_MT_TRACKING_ID" in line:
            if not self.begin:
                print("Please click Begin button first.")
                return
            tracking_id = line.split()[-1]
            if tracking_id != "ffffffff":
                # print("开始跟踪触摸事件")
                self.is_tracking = True
            elif tracking_id == "ffffffff":
                self.save_click_or_swipe()
        elif coord_info and self.is_tracking:
            X, Y = coord_info
            if X is not None:
                self.end_x = X
                if self.start_x is None:
                    self.start_x = self.end_x
                else:
                    self.is_click = False  # 出现连续的坐标变化，确认为滑动
            elif Y is not None:
                self.end_y = Y
                if self.start_y is None:
                    self.start_y = self.end_y
                else:
                    self.is_click = False  # 出现连续的坐标变化，确认为滑动
        # 处理按钮点击事件
        elif "EV_KEY" in line and "KEY_" in line:
            self.parse_press(line)


    def parse_huawei(self, line):
        coord_info = parse_event(line, self.max_values)
        if "BTN_TOUCH" in line:
            if not self.begin:
                print("Please click Begin button first.")
                return
            arg_touch = line.split()[-1]
            if arg_touch == "DOWN":
                self.is_tracking = True
            elif arg_touch == "UP":
                self.save_click_or_swipe()
        elif coord_info and self.is_tracking:
            X, Y = coord_info
            if X is not None:
                self.end_x = X
                if self.start_x is None:
                    self.start_x = self.end_x
                else:
                    self.is_click = False  # 出现连续的坐标变化，确认为滑动
            elif Y is not None:
                self.end_y = Y
                if self.start_y is None:
                    self.start_y = self.end_y
                else:
                    self.is_click = False  # 出现连续的坐标变化，确认为滑动
        # 处理按钮点击事件
        elif "EV_KEY" in line and "KEY_" in line:
            self.parse_press(line)


    def parse_line(self, line):
        # 解析坐标信息
        if not self.max_values:
            self.max_values = get_screen_max_values()

        #print(line)
        # 处理触摸跟踪ID开始和结束

        if self.config["DEVICE"] != "huawei":
            self.parse_android(line)
        else:
            self.parse_huawei(line)

    def get_events(self):
        return self.events


    def press_enter(self):
        if not self.begin:
            messagebox.showinfo(title='Hi', message='Please click Begin button first.')
            return
        self.page_executor.press_enter()
        event = {"type": "press_key", "key_name": 'KEY_ENTER'}

        print_with_color("Simulating press Enter...",'blue')
        self.add_new_event(event)


    def press_back(self):
        if not self.begin:
            messagebox.showinfo(title='Hi', message='Please click Begin button first.')
            return
        self.page_executor.press_back()
        event = {"type": "press_key", "key_name": 'KEY_BACK'}

        print_with_color("Simulating press Back...",'blue')
        self.add_new_event(event)


    def press_home(self):
        if not self.begin:
            messagebox.showinfo(title='Hi', message='Please click Begin button first.')
            return
        self.page_executor.press_home()
        event = {"type": "press_key", "key_name": 'KEY_HOME'}

        print_with_color("Simulating press Home...",'blue')
        self.add_new_event(event)


    def type_text(self):
        if not self.begin:
            messagebox.showinfo(title='Hi', message='Please click Begin button first.')
            return
        text = simpledialog.askstring("Input", "What do you want to type?")
        self.page_executor.type(text)
        event = {"type": "type", "input": text}

        if text is not None:
            print_with_color(f"Simulating typing: {text}", 'blue')
        self.add_new_event(event)

    def finish(self):
        text = simpledialog.askstring("Input", "Anything to return for finish?")
        if text is not None:
            print_with_color(f"Finish and Return: {text}", 'blue')
        else:
            print_with_color(f"Finish", 'blue')
        self.page_executor.finish(text)
        self.page_executor.update_screenshot(prefix="end")
        event = {"type": "finish", "input": text}
        self.add_new_event(event)
        print("Save Path: ", self.config["SAVE_DIR"])
        sys.exit()


    def begin_operation(self):
        if self.block:
            messagebox.showinfo(title='Hi', message='Please wait until finish the current operation or current screenshot first.')
            return
        self.block = True
        self.begin = True
        self.recorder.update_response(self.controller, need_screenshot=True, status = "before")
        print_with_color(f"Begin your operation...", 'yellow')
        self.block = False

    def create_gui(self):
        # Create a simple GUI with buttons for specific actions
        root = self.root
        root.title("执行操作：每次操作前都需要点击Begin")

        # Define button actions (assuming press_enter, press_back, press_home, type_text are defined)
        tk.Button(root, text="Begin", command=self.begin_operation).pack(fill=tk.X)
        tk.Button(root, text="Press Enter", command=self.press_enter).pack(fill=tk.X)
        tk.Button(root, text="Press Back", command=self.press_back).pack(fill=tk.X)
        tk.Button(root, text="Press Home", command=self.press_home).pack(fill=tk.X)
        tk.Button(root, text="Type", command=self.type_text).pack(fill=tk.X)
        tk.Button(root, text="Finish", command=self.finish).pack(fill=tk.X)

        # Start the GUI in a separate thread to avoid blocking
        threading.Thread(target=root.mainloop, daemon=True).start()

    def run_adb_command(self):
        """执行 adb shell getevent 命令，并实时处理输出"""
        process = subprocess.Popen(['adb', 'shell', 'getevent', '-l'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    print("No more output")
                    break
                self.parse_line(line)
        except KeyboardInterrupt:
            print("Stopping event monitoring...")
        finally:
            process.terminate()

    def add_new_event(self, event):
        self.block = True
        self.events.append(event)
        print(event)
        if self.recorder:
            self.recorder.update_execution(event, status = "after")
            self.recorder.turn_number += 1
        self.reset()
        self.begin = False
        self.block = False
        print_with_color(f"Operation completed.", 'yellow')


    def run(self):
        # Running both GUI and adb command in separate threads
        adb_thread = threading.Thread(target=self.run_adb_command, daemon=True)
        adb_thread.start()
        if self.recorder:
            self.recorder.update_response(self.controller, None)

# Example usage
if __name__ == "__main__":
    root = tk.Tk()
    parser = TouchEventParser(root)
    parser.create_gui()
    parser.run()
    root.mainloop()
