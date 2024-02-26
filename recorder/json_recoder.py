import time
import os
import json

TRACE_DIR = os.environ.get('TRACE_DIR')
SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR')
if TRACE_DIR is None:
    TRACE_DIR = '../traces'
if SCREENSHOT_DIR is None:
    SCREENSHOT_DIR = '../temp'
os.makedirs(TRACE_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class JSONRecorder:
    def __init__(self, instruction, page_executor):
        self.id = int(time.time())
        self.instruction = instruction
        self.page_executor = page_executor

        self.turn_number = 0
        self.file_path = f'{TRACE_DIR}/{self.id}.jsonl'
        self.contents = []

    def update_response(self, page, response, prompt="** screenshot **"):
        step = {
            "trace_id": self.id, "index": self.turn_number,
            "prompt": prompt if self.turn_number > 0 else f"{self.instruction}",
            "image": self.page_executor.current_screenshot, "response": response, "url": page.url,
            "window": page.viewport_size, "target": self.instruction
        }
        self.contents.append(step)

    def update_execution(self, exe_res):
        self.contents[-1]['parsed_action'] = exe_res
        with open(self.file_path, 'a') as f:
            f.write(json.dumps(self.contents[-1], ensure_ascii=False) + '\n')

    def format_history(self):
        history = []
        for turn in self.contents:
            history.append({"role": "user", "content": [{"type": "text", "text": turn['prompt']}]})
            history.append({"role": "assistant", "content": [{"type": "text", "text": turn['response']}]})
        return history
