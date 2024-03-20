from mobile_test import run, get_mobile_device
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
import pandas as pd

def process_config_evaluation(evaid, taskid):
    config = {}
    config_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(config_path)

    LOG_DIR = "evaluation_logs/" + evaid
    config["LOG_DIR"] = LOG_DIR

    if LOG_DIR is None:
        LOG_DIR = '../logs'

    TRACE_DIR = os.path.join(LOG_DIR, taskid, 'traces')
    SCREENSHOT_DIR = os.path.join(LOG_DIR, taskid, 'Screen')
    XML_DIR = os.path.join(LOG_DIR, taskid, 'xml')
    Video_DIR = os.path.join(LOG_DIR, taskid, 'video')
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
    df_query = pd.read_excel("evaluation_dataset/query.xlsx")
    controller = get_mobile_device()
    eva_id = str(time.time())
    for idx,row in df_query.iterrows():
        id = row["id"]
        query = row["query"]
        app = row["app"]
        print_with_color(f"Processing {id} {query}", "yellow")
        config = process_config_evaluation(eva_id, id)
        query = f"打开{app}, {query}"
        run(controller, instruction=query, config = config)
        for i in range(0,10):
            controller.home()

if __name__ == "__main__":
    main()