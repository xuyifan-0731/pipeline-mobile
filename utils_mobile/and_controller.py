import os
import base64
import getpass
import subprocess
import xml.etree.ElementTree as ET

# from config import load_config
from utils_mobile.utils import print_with_color


# configs = load_config()


class AndroidElement:
    def __init__(self, uid, bbox, attrib):
        self.uid = uid
        self.bbox = bbox
        self.attrib = attrib


def execute_adb(adb_command):
    # print(adb_command)
    env = os.environ.copy()
    env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/platform-tools:" + env["PATH"]
    env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/tools:" + env["PATH"]
    result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            executable='/bin/zsh', env=env)
    if result.returncode == 0:
        return result.stdout.strip()
    print_with_color(f"Command execution failed: {adb_command}", "red")
    print_with_color(result.stderr, "red")
    return "ERROR"

def execute_adb_no_output(adb_command):
    # print(adb_command)
    env = os.environ.copy()
    env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/platform-tools:" + env["PATH"]
    env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/tools:" + env["PATH"]
    result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            executable='/bin/zsh', env=env)
    if result.returncode == 0:
        return result.stdout.strip()
    return "ERROR"

def list_all_devices():
    adb_command = "adb devices"
    device_list = []
    result = execute_adb(adb_command)
    if result != "ERROR":
        devices = result.split("\n")[1:]
        for d in devices:
            device_list.append(d.split()[0])

    return device_list


def get_id_from_element(elem):
    bounds = elem.attrib["bounds"][1:-1].split("][")
    x1, y1 = map(int, bounds[0].split(","))
    x2, y2 = map(int, bounds[1].split(","))
    elem_w, elem_h = x2 - x1, y2 - y1
    if "resource-id" in elem.attrib and elem.attrib["resource-id"]:
        elem_id = elem.attrib["resource-id"].replace(":", ".").replace("/", "_")
    else:
        elem_id = f"{elem.attrib['class']}_{elem_w}_{elem_h}"
    if "content-desc" in elem.attrib and elem.attrib["content-desc"] and len(elem.attrib["content-desc"]) < 20:
        content_desc = elem.attrib['content-desc'].replace("/", "_").replace(" ", "").replace(":", "_")
        elem_id += f"_{content_desc}"
    return elem_id


def traverse_tree(xml_path, elem_list, attrib, add_index=False):
    path = []
    for event, elem in ET.iterparse(xml_path, ['start', 'end']):
        if event == 'start':
            path.append(elem)
            if attrib in elem.attrib and elem.attrib[attrib] == "true":
                parent_prefix = ""
                if len(path) > 1:
                    parent_prefix = get_id_from_element(path[-2])
                bounds = elem.attrib["bounds"][1:-1].split("][")
                x1, y1 = map(int, bounds[0].split(","))
                x2, y2 = map(int, bounds[1].split(","))
                center = (x1 + x2) // 2, (y1 + y2) // 2
                elem_id = get_id_from_element(elem)
                if parent_prefix:
                    elem_id = parent_prefix + "_" + elem_id
                if add_index:
                    elem_id += f"_{elem.attrib['index']}"
                close = False
                for e in elem_list:
                    bbox = e.bbox
                    center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
                    dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
                    if dist <= 30:
                        close = True
                        break
                if not close:
                    elem_list.append(AndroidElement(elem_id, ((x1, y1), (x2, y2)), attrib))

        if event == 'end':
            path.pop()


class AndroidController:
    def __init__(self, device):
        self.device = device
        self.screenshot_dir = "/sdcard"
        self.xml_dir = "/sdcard"
        self.width, self.height = self.get_device_size()
        self.viewport_size = (self.width, self.height)
        self.backslash = "\\"
        self.set_adb_keyboard()

    '''
    def get_device_size(self):
        adb_command = f"adb -s {self.device} shell wm size"
        result = execute_adb(adb_command)
        if result != "ERROR":
            return map(int, result.split(": ")[1].split("x"))
        return 0, 0'''

    def set_adb_keyboard(self):
        command = f"adb -s {self.device} shell ime set com.android.adbkeyboard/.AdbIME"
        result = execute_adb(command)
        return result

    def get_device_size(self):
        command = f"adb -s {self.device} shell wm size"
        output = execute_adb(command)
        resolution = output.split(":")[1].strip()
        width, height = resolution.split("x")
        return int(width), int(height)

    def get_screenshot(self, prefix, save_dir):
        cap_command = f"adb -s {self.device} shell screencap -p " \
                      f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')}"
        pull_command = f"adb -s {self.device} pull " \
                       f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')} " \
                       f"{os.path.join(save_dir, prefix + '.png')}"
        result = execute_adb(cap_command)
        if result != "ERROR":
            result = execute_adb(pull_command)
            if result != "ERROR":
                return os.path.join(save_dir, prefix + ".png")
            return result
        return result

    def save_screenshot(self, save_path):
        prefix = os.path.basename(save_path).replace('.png', '')
        remote_path = f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')}"

        cap_command = f"adb -s {self.device} shell screencap -p {remote_path}"
        pull_command = f"adb -s {self.device} pull {remote_path} {save_path}"
        print(remote_path, save_path)
        result = execute_adb(cap_command)
        if result != "ERROR":
            result = execute_adb(pull_command)
            if result != "ERROR":
                return save_path
            return result
        return result

    def get_current_activity(self):
        adb_command = f"adb -s {self.device} shell dumpsys window | grep mCurrentFocus"
        result = execute_adb(adb_command)
        if result != "ERROR":
            return result
        return 0

    def get_xml(self, prefix, save_dir):
        dump_command = f"adb -s {self.device} shell uiautomator dump " \
                       f"{os.path.join(self.xml_dir, prefix + '.xml').replace(self.backslash, '/')}"
        pull_command = f"adb -s {self.device} pull " \
                       f"{os.path.join(self.xml_dir, prefix + '.xml').replace(self.backslash, '/')} " \
                       f"{os.path.join(save_dir, prefix + '.xml')}"
        result = execute_adb(dump_command)
        if result != "ERROR":
            result = execute_adb(pull_command)
            if result != "ERROR":
                return os.path.join(save_dir, prefix + ".xml")
            return result
        return result

    def back(self):
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_BACK"
        ret = execute_adb(adb_command)
        return ret

    def enter(self):
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_ENTER"
        ret = execute_adb(adb_command)
        return ret

    def home(self):
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_HOME"
        ret = execute_adb(adb_command)
        return ret

    def tap(self, x, y):
        adb_command = f"adb -s {self.device} shell input tap {x} {y}"
        ret = execute_adb(adb_command)
        return ret

    def text(self, input_str):
        #adb_command = f'adb -s {self.device} input keyevent KEYCODE_MOVE_END'
        #ret = execute_adb(adb_command)
        adb_command = f'adb -s {self.device} shell input keyevent --press $(for i in {{1..100}}; do echo -n "67 "; done)'
        ret = execute_adb(adb_command)
        chars = input_str
        charsb64 = str(base64.b64encode(chars.encode('utf-8')))[1:]
        adb_command = f"adb -s {self.device} shell am broadcast -a ADB_INPUT_B64 --es msg {charsb64}"
        ret = execute_adb(adb_command)
        '''
        input_str = input_str.replace(" ", "%s")
        input_str = input_str.replace("'", "")
        adb_command = f"adb -s {self.device} shell input text {input_str}"
        ret = execute_adb(adb_command)'''
        return ret

    def long_press(self, x, y, duration=1000):
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x} {y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def kill_package(self, package_name):
        command = f"adb -s {self.device} shell am force-stop {package_name}"
        execute_adb(command)

    def swipe(self, x, y, direction, dist="medium", quick=False):
        unit_dist = int(self.width / 10)
        if x == None:
            x = self.width // 2
        if y == None:
            y = self.height // 2
        if dist == "long":
            unit_dist *= 10
        elif dist == "medium":
            unit_dist *= 2
        if direction == "up":
            offset = 0, -2 * unit_dist
        elif direction == "down":
            offset = 0, 2 * unit_dist
        elif direction == "left":
            offset = -1 * unit_dist, 0
        elif direction == "right":
            offset = unit_dist, 0
        else:
            return "ERROR"
        duration = 100 if quick else 400
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x + offset[0]} {y + offset[1]} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def swipe_precise(self, start, end, duration=400):
        start_x, start_y = start
        end_x, end_y = end
        adb_command = f"adb -s {self.device} shell input swipe {start_x} {start_x} {end_x} {end_y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def start_screen_record(self, prefix):
        print("Starting screen record")
        command = f'adb shell screenrecord /sdcard/{prefix}.mp4'
        return subprocess.Popen(command, shell=True)

if __name__ == '__main__':
    And = AndroidController("emulator-5554")
    And.text("北京南站")