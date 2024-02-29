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
import getpass

from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
from tqdm import tqdm

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


def get_code_snippet(content):
    code = re.search(r'```.*?\n([\s\S]+?)\n```', content)
    if code is None:
        raise RuntimeError()
    code = code.group(1)
    return code

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
        screenshot_dir=os.getenv('SCREENSHOT_DIR')
    )
    page_executor.__update_screenshot__()
    record = JSONRecorder(instruction=instruction, page_executor=page_executor)
    print('[Setup Time]', time.time() - stt)
    
    actions = []
    while record.turn_number <= options.get("max_steps", 30):
        stt = time.time()
        prompt = page_executor.__get_current_status__() if record.turn_number > 0 else instruction
        content = openai_engine.generate(
            prompt=prompt,
            image_path=page_executor.current_screenshot,
            turn_number=record.turn_number,
            ouput__0=record.format_history()
        )
        
        # content = '```\n'+ input(prompt+'\n') + '\n```'
        
        record.update_response(page, content)
        print(content)
        print('[Predict Time]', time.time() - stt)
        
        stt = time.time()
        exe_res = page_executor(get_code_snippet(content))
        record.update_execution(exe_res)
        actions.append(page_executor.action_return)
        print(page_executor.action_return)
        print('[Execute Time]', time.time() - stt)
        
        if exe_res['operation'] == 'exit':
            break

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
        
    return score


def test(args: argparse.Namespace, config_file_list: list[str]) -> None:
    scores = []
    for config_file in tqdm(config_file_list):
        with open(config_file) as f:
            _c = json.load(f)
            intent = _c["intent"]
            task_id = _c["task_id"]
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
            "max_steps": args.max_steps
        }
         
        with sync_playwright() as playwright:
            score = run(playwright, instruction=intent, config_file=config_file, options=options)
        scores.append(score)

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

    # example config
    parser.add_argument("--test_start_idx", type=int, default=0)
    parser.add_argument("--test_end_idx", type=int, default=1000)

    # logging related
    parser.add_argument("--result_dir", type=str, default="")
    args = parser.parse_args()

    return args

def prepare(args: argparse.Namespace) -> None:
    # prepare result dir
    result_dir = args.result_dir
    if not result_dir:
        result_dir = f"cache/results_{time.strftime('%Y%m%d%H%M%S', time.localtime())}"
    
    # os.makedirs("temp", exist_ok=True)
    # os.makedirs("dev", exist_ok=True)
    os.makedirs(os.path.join(result_dir, "traces"), exist_ok=True)
    
    logger.info(f"Result dir: {result_dir}")
    
    # log the log file
    with open(os.path.join(result_dir, "log_files.txt"), "a+") as f:
        f.write(f"{LOG_FILE_NAME}\n")

if __name__ == '__main__':
    print(ROOT_PATH)

    args = config()
    args.sleep_after_execution = 2.0
    prepare(args)

    test_file_list = []
    st_idx = args.test_start_idx
    ed_idx = args.test_end_idx
    for i in range(st_idx, ed_idx):
        if not os.path.exists(f"{ROOT_PATH}/config_files/{i}.json"):
            continue
        test_file_list.append(f"{ROOT_PATH}/config_files/{i}.json")
    
    # test_file_list = get_unfinished(test_file_list, args.result_dir)

    if len(test_file_list) == 0:
        logger.info("No task left to run")
    else:
        print(f"Total {len(test_file_list)} tasks left")
        test(args, test_file_list)

