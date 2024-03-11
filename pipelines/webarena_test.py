from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import random
import subprocess
import tempfile
import time
import re
import copy
import getpass
import signal

from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
from tqdm import tqdm
from typing import List
from ..page_executor import WebarenaPageExecutor
from ..recorder import JSONRecorder
from ..gpt4v import OpenaiEngine
from ..webarena_tools import (
    setup,
    evaluator_router,
)

from ..webarena_tools.auto_login import (
    get_site_comb_from_filepath
)

from ..webarena_tools.actions import (
    is_equivalent,
    create_none_action,
    create_stop_action,
    Action,
    ActionTypes,
)

from playwright.sync_api import Playwright, sync_playwright

ROOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    
# For logs
LOG_FOLDER = "log_files"
Path(LOG_FOLDER).mkdir(parents=True, exist_ok=True)
LOG_FILE_NAME = f"{LOG_FOLDER}/log_{time.strftime('%Y%m%d%H%M%S', time.localtime())}_{random.randint(0, 10000)}.log"

logger = logging.getLogger("logger")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

file_handler = logging.FileHandler(LOG_FILE_NAME)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Set the log format
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)


openai_engine = OpenaiEngine()
config_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(config_path)

# Timeout handler
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException

signal.signal(signal.SIGALRM, timeout_handler)

def get_code_snippet(content):
    code = re.search(r'```.*?\n([\s\S]+?)\n```', content)
    if code is None:
        return ""
        # raise RuntimeError()
    code = code.group(1)
    return code

def early_stop(actions: list, threshold: int=5) -> tuple[bool, str]:
    # Case: same action for k times
    k = threshold
    last_k_actions = actions[-k:]  # type: ignore[assignment]
    
    if len(last_k_actions) == 0:
        return False, ""

    last_action: Action = actions[-1]

    if len(last_k_actions) >= k:
        if all([
            is_equivalent(action, last_action)
            for action in last_k_actions
        ]):
            return True, f"Same action for {k} times"

    return False, ""

def update_action_history(path: str, task_id: int, raw_actions: List[Action], score: float=0):
    actions = copy.deepcopy(raw_actions)
    for action in actions:
        action["coords"] = action["coords"].tolist()
        action["action_type"] = action["action_type"].__str__()
    
    obj = {
        "task_id": task_id,
        "score": score,
        "actions": actions
    }
    json.dump(obj, open(path, "w"), indent=4)
    
def run(
    playwright: Playwright,
    instruction: str=None,
    config_file: str=None,
    options: dict[str, str] | None=None
) -> float:
    stt = time.time()
    context, page = setup(playwright, config_file, options)
    page_executor = WebarenaPageExecutor(
        context=context,
        page=page,
        engine=openai_engine,
        screenshot_dir=os.path.join(options["result_dir"], "screenshots"),
        options=options,
    )
    page_executor.__update_screenshot__()
    record = JSONRecorder(
        instruction=instruction,
        page_executor=page_executor,
        options=options,
        trace_dir=os.path.join(options["result_dir"], "traces"),
    )
    
    print('[Setup Time]', time.time() - stt)
    
    actions = []
    task_id = options.get("task_id", -1)
    out_path = os.path.join(options["result_dir"], "actions", f"{task_id}.json")
                
    timeout_count = 0
    while record.turn_number + timeout_count * 0.1 <= options.get("max_steps", 30):
        update_action_history(out_path, task_id, raw_actions=actions)
        if True:
        # try:
            stt = time.time()
            prompt = page_executor.__get_current_status__() if record.turn_number > 0 else instruction
            print('model generating...')
            
            signal.alarm(90)
            try:
                content = openai_engine.webarena_generate(
                    prompt=prompt,
                    image_path=page_executor.current_screenshot,
                    turn_number=record.turn_number,
                    ouput__0=record.format_history(),
                    sys_prompt=options.get("sites", "basic")[0],
                )
            except TimeoutException:
                timeout_count += 1
                print('[Prediction Timeout]', time.time() - stt)
                continue
            
            # input('your move > ')
            # content = open("action.txt", "r").read()

            record.update_response(page, content, prompt=prompt)
            print(content)
            print('[Predict Time]', time.time() - stt)
            
            stt = time.time()
            print('system executing...')
            exe_res = page_executor(get_code_snippet(content))
            record.update_execution(exe_res)
            actions.append(page_executor.action_return)
            print(page_executor.action_return)
            print('[Execute Time]', time.time() - stt)
            
            if exe_res['operation'] == 'exit':
                break
            
            esignal, reason = early_stop(actions)
            if esignal:
                actions.append(create_stop_action(reason))
                break
        # except:
        #     pass
        
        record.turn_number += 1
        
    evaluator = evaluator_router(config_file)
    score = evaluator(
        trajectory=actions,
        config_file=config_file,
        page=page,
        client=None,
    )
    
    if score == 1:
        logger.info(f"[Result] (PASS) {config_file}")
    else:
        logger.info(f"[Result] (FAIL) {config_file}")
        
    update_action_history(out_path, task_id, raw_actions=actions, score=score)
        
    return score


def test(args: argparse.Namespace, config_file_list: list[str]) -> None:
    scores = []
    for config_file in tqdm(config_file_list):
        try:
            with open(config_file) as f:
                _c = json.load(f)
                intent = _c["intent"]
                task_id = _c["task_id"]
                sites = _c["sites"]
                # automatically login
                if _c["storage_state"]:
                    cookie_file_name = os.path.basename(_c["storage_state"])
                    comb = get_site_comb_from_filepath(cookie_file_name)
                    temp_dir = tempfile.mkdtemp()
                    # subprocess to renew the cookie
                    subprocess.run([
                        "python",
                        "-m",
                        f"Pipeline.webarena_tools.auto_login",
                        "--auth_folder",
                        temp_dir,
                        "--site_list",
                        *comb,
                    ])
                    _c["storage_state"] = f"{temp_dir}/{cookie_file_name}"
                    assert os.path.exists(_c["storage_state"])
                    # update the config file
                    config_file = f"{temp_dir}/{os.path.basename(config_file)}"
                    with open(config_file, "w") as f:
                        json.dump(_c, f)
            
            options = {
                "storage_state": _c["storage_state"],
                "headless": False,
                "slow_mo": args.slow_mo,
                "viewport": {
                    "width": args.viewport_width,
                    "height": args.viewport_height
                },
                "max_steps": args.max_steps,
                "task_id": task_id,
                "sites": sites,
                "result_dir": args.result_dir,
                "reset": True,
            }
        except:
            logger.info(f"Config Error: {config_file}")
            continue
        
        if True:
        # try:
            with sync_playwright() as playwright:
                score = run(playwright, instruction=intent, config_file=config_file, options=options)
            scores.append(score)
        # except:
        #     logger.info(f"Runtime Error: {config_file}")

    scores = [0.0] if len(scores) == 0 else scores
    logger.info(f"Average score: {sum(scores) / len(scores)}")
        
def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run end-to-end evaluation on the benchmark"
    )
    parser.add_argument(
        "--slow_mo",
        type=int,
        default=0,
        help="Slow down the browser by the specified amount",
    )
    parser.add_argument("--viewport_width", type=int, default=1280)
    parser.add_argument("--viewport_height", type=int, default=720)
    parser.add_argument("--sleep_after_execution", type=float, default=0.0)
    parser.add_argument("--max_steps", type=int, default=30)

    # test config
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=1000)
    parser.add_argument("--sample", type=int, default=1)
    parser.add_argument("--sites", type=str, default="shopping,shopping_admin,gitlab,reddit,wikipedia,map")

    # logging related
    parser.add_argument("--result_dir", type=str, default="")
    args = parser.parse_args()

    return args

def prepare(args: argparse.Namespace) -> None:
    # prepare result dir
    result_dir = args.result_dir
    if not result_dir:
        result_dir = f"cache/results_{time.strftime('%Y%m%d%H%M%S', time.localtime())}"
        args.result_dir = result_dir
    
    # os.makedirs("temp", exist_ok=True)
    # os.makedirs("dev", exist_ok=True)
    os.makedirs(os.path.join(result_dir, "actions"), exist_ok=True)
    os.makedirs(os.path.join(result_dir, "traces"), exist_ok=True)
    os.makedirs(os.path.join(result_dir, "screenshots"), exist_ok=True)
    
    logger.info(f"Result dir: {result_dir}")
    
    # log the log file
    with open(os.path.join(result_dir, "log_files.txt"), "a+") as f:
        f.write(f"{LOG_FILE_NAME}\n")

def get_unfinished(config_files: list[str], result_dir: str) -> list[str]:
    task_ids = []
    result_files = glob.glob(os.path.join(result_dir, "actions/*.json"))
    for fn in result_files:
        try:
            with open(fn, "r") as f:
                jd = json.load(f)
        except:
            jd = {}
        
        if len(jd.get('actions', [])) >= 0:
            task_id = os.path.basename(fn).split(".")[0]
            task_ids.append(task_id)

    unfinished_configs = []
    for config_file in config_files:
        task_id = os.path.basename(config_file).split(".")[0]
        if task_id not in task_ids:
            unfinished_configs.append(config_file)
    return unfinished_configs

if __name__ == '__main__':
    print(ROOT_PATH)

    args = config()
    args.sleep_after_execution = 2.0
    prepare(args)

    test_file_list = []
    st_idx = args.start_idx
    ed_idx = args.end_idx
    
    sites = args.sites.split(",")
            
    for i in range(st_idx, ed_idx):
        path = os.path.join(ROOT_PATH, "config_files", f"{i}.json")
        if not os.path.exists(path):
            continue
        if i % args.sample != 0:
            continue
        jdata = json.load(open(path, "r"))
        if jdata["sites"][0] not in sites:
            continue
                
        test_file_list.append(path)
    
    test_file_list = get_unfinished(test_file_list, args.result_dir)
    
    if len(test_file_list) == 0:
        logger.info("No task left to run")
    else:
        print(f"Total {len(test_file_list)} tasks left")
        test(args, test_file_list)

