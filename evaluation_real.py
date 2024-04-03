from mobile_test import run
from utils_mobile.utils import print_with_color
from utils_mobile.and_controller import AndroidController, list_all_devices, execute_adb, execute_adb_no_output

import os
import sys
import yaml
import time
import pandas as pd

def get_package_name(app):
    apps_dict = {
        "Spotify": "com.spotify.music",
        "Clock": "com.google.android.deskclock",
        "TikTok": "com.zhiliaoapp.musically",
        "Clash": "com.github.kr328.clash",
        "Amazon Shopping": "com.amazon.mShop.android.shopping",
        "Snapchat": "com.snapchat.android",
        "Slack": "com.Slack",
        "Uber": "com.ubercab",
        "ADB Keyboard": "com.android.adbkeyboard",
        "Reddit": "com.reddit.frontpage",
        "Twitter": "com.twitter.android",
        "Quora": "com.quora.android",
        "Zoom": "us.zoom.videomeetings",
        "Booking": "com.booking",
        "Instagram": "com.instagram.android",
        "Facebook": "com.facebook.katana",
        "WhatsApp": "com.whatsapp",
        "Google Maps": "com.google.android.apps.maps",
        "YouTube": "com.google.android.youtube",
        "Netflix": "com.netflix.mediaclient",
        "LinkedIn": "com.linkedin.android",
        "Google Drive": "com.google.android.apps.docs",
        "Gmail": "com.google.android.gm",
        "Chrome": "com.android.chrome",
        "Twitch": "tv.twitch.android.app"
    }

    return apps_dict.get(app, None)

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

    return controller, device


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




    #avd_base = config["AVD_BASE"]
    #device_name = config["AVD_NAME"]
    #config["AVD_DIR"] = os.path.join(avd_base, device_name + ".avd")
    #config["AVD_NAME"] = device_name
    #config["AVD_BASE"] = avd_base

    #andorid_sdk_path = config["ANDROID_SDK_PATH"]
    #config["ANDROID_SDK_PATH"] = andorid_sdk_path
    #os.environ['ANDROID_HOME'] = andorid_sdk_path
    #os.environ['PATH'] += os.pathsep + os.path.join(os.environ['ANDROID_HOME'], 'emulator')

    return config

def kill_app(controller, package_name):
    controller.kill_package(package_name)
    controller.home()

def main(config_path = "config_files/evaluation.yaml"):
    eva_id = str(time.time())
    config = process_config_evaluation(config_path = config_path, evaid = eva_id)
    df_query = pd.read_excel(config["EVA_DATASET"])
    controller, device_name = get_mobile_device()
    for idx, row in df_query.iterrows():
        try:
            id = row["id"]
            query = row["query"]
            app = row["app"]
        except:
            continue
        config = process_config_evaluation(config_path=config_path, evaid=eva_id, taskid=id)
        package_name = get_package_name(app)
        if package_name is None:
            print_with_color(f"ERROR: Package name not found for {app}", "red")
            continue
        print_with_color(f"Processing {id} {query}", "yellow")
        query = f"Open {app}, {query}"
        run(controller, instruction=query, config = config, app = app)
        kill_app(controller, package_name)




if __name__ == "__main__":
    main(config_path = "config_files/evaluation.yaml")
