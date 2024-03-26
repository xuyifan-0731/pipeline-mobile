from mobile_test import run
from utils_mobile.utils import print_with_color
from utils_mobile.and_controller import AndroidController, list_all_devices, execute_adb, execute_adb_no_output

import os
import sys
import time
import yaml
import subprocess
from dotenv import load_dotenv
import pandas as pd


def get_device_list():
    emulator_list_command = ["emulator", "-list-avds"]
    device_list = subprocess.run(emulator_list_command, capture_output=True, text=True).stdout.splitlines()

    return device_list


def get_adb_device_name(avd_name=None):
    device_list = list_all_devices()
    for device in device_list:
        command = f"adb -s {device} emu avd name"
        ret = execute_adb_no_output(command)
        ret = ret.split("\n")[0]
        if ret == avd_name:
            return device
    return None


def start_emulator(config):
    avd_name = config["AVD_NAME"]
    print_with_color(f"Starting Android Emulator with AVD name: {avd_name}", "blue")
    if not os.path.exists(config["AVD_LOG_DIR"]):
        os.makedirs(config["AVD_LOG_DIR"], exist_ok=True)
    out_file = open(os.path.join(config["AVD_LOG_DIR"], 'emulator_output.txt'), 'a')
    emulator_process = subprocess.Popen(["emulator", "-avd", avd_name, "-no-snapshot-save"], stdout=out_file,
                                        stderr=out_file)
    print_with_color(f"Waiting for the emulator to start...", "blue")
    while True:
        try:
            device = get_adb_device_name(avd_name)
        except:
            continue
        if device is not None:
            break
    while True:
        boot_complete = f"adb -s {device} shell getprop init.svc.bootanim"
        boot_complete = execute_adb_no_output(boot_complete)
        if boot_complete == 'stopped':
            print_with_color("Emulator started successfully", "blue")
            break
        time.sleep(1)
    time.sleep(1)
    return emulator_process, out_file


def stop_emulator(emulator_process, out_file, config):
    print_with_color("Stopping Android Emulator...", "blue")
    emulator_process.terminate()
    while True:
        try:
            device = get_adb_device_name(config["AVD_NAME"])
        except:
            device = None
        if device is None:
            print_with_color("Emulator stopped successfully", "blue")
            break
        time.sleep(1)

    out_file.close()
    sleep_time = 3


def get_mobile_evaluation_device(config, emulator_process=None, out_file=None):
    if "AVD_NAME" not in config:
        print_with_color("ERROR: AVD_NAME not found in config!", "red")
        sys.exit()
    AVD_NAME = config["AVD_NAME"]
    print_with_color(f"Devices attached:\n{AVD_NAME}", "yellow")

    if emulator_process is None:
        emulator_process, out_file = start_emulator(config)
    else:
        stop_emulator(emulator_process, out_file, config)
        emulator_process, out_file = start_emulator(config)

    print_with_color("Successfully start", "blue")
    device_list = list_all_devices()
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

    return controller, emulator_process, out_file


def process_config_evaluation(evaid=None, taskid=None, config=None, config_path = None):
    if config is None and config_path is not None:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)

    assert "GPT4V_TOKEN" in config, "GPT4V_TOKEN not found in config!"

    os.environ["GPT4V_TOKEN"] = config["GPT4V_TOKEN"]

    if evaid is not None and taskid is not None:
        LOG_DIR = "evaluation_logs/" + evaid
        config["LOG_DIR"] = LOG_DIR

        if LOG_DIR is None:
            LOG_DIR = '../logs'

        TRACE_DIR = os.path.join(LOG_DIR, taskid, 'traces')
        SCREENSHOT_DIR = os.path.join(LOG_DIR, taskid, 'Screen')
        XML_DIR = os.path.join(LOG_DIR, taskid, 'xml')
        Video_DIR = os.path.join(LOG_DIR, taskid, 'video')
        AVD_LOG_DIR = os.path.join(LOG_DIR, taskid, 'avd_logs')
        config["TRACE_DIR"] = TRACE_DIR
        config["SCREENSHOT_DIR"] = SCREENSHOT_DIR
        config["XML_DIR"] = XML_DIR
        config["Video_DIR"] = Video_DIR
        config["AVD_LOG_DIR"] = AVD_LOG_DIR

        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(TRACE_DIR, exist_ok=True)
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        os.makedirs(XML_DIR, exist_ok=True)
        os.makedirs(Video_DIR, exist_ok=True)

    avd_base = config["AVD_BASE"]
    device_name = config["AVD_NAME"]
    config["AVD_DIR"] = os.path.join(avd_base, device_name + ".avd")
    config["AVD_NAME"] = device_name
    config["AVD_BASE"] = avd_base

    andorid_sdk_path = config["ANDROID_SDK_PATH"]
    config["ANDROID_SDK_PATH"] = andorid_sdk_path
    os.environ['ANDROID_HOME'] = andorid_sdk_path
    os.environ['PATH'] += os.pathsep + os.path.join(os.environ['ANDROID_HOME'], 'emulator')

    return config


def main(config_path = "config_files/evaluation.yaml"):
    config = process_config_evaluation(config_path = config_path)
    df_query = pd.read_excel(config["EVA_DATASET"])
    eva_id = str(time.time())
    emulator_process = None
    out_file = None

    for idx, row in df_query.iterrows():
        try:
            id = row["id"]
            query = row["query"]
            app = row["app"]
        except:
            continue
        print_with_color(f"Processing {id} {query}", "yellow")
        config = process_config_evaluation(eva_id, id, config)
        controller, emulator_process, out_file = get_mobile_evaluation_device(config, emulator_process, out_file)
        '''
        while True:
            done = input("input done to continue:")
            if done == "done":
                break
        '''
        query = f"打开{app}, {query}"
        run(controller, instruction=query, config = config)



if __name__ == "__main__":
    main(config_path = "config_files/evaluation.yaml")
