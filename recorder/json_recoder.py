import time
import os
import json

class JSONRecorder:
    def __init__(self, instruction, page_executor, trace_dir="../traces", options={}):
        self.id = int(options.get("task_id", time.time()))
        self.instruction = instruction
        self.page_executor = page_executor

        self.turn_number = 0
        self.file_path = os.path.join(trace_dir, f'{self.id}.jsonl')
        self.contents = []
        
        if "reset" in options:
            with open(self.file_path, 'w') as f:
                f.write('')

    def update_response(self, context, response, prompt="** screenshot **"):
        step = {
            "trace_id": self.id,
            "index": self.turn_number,
            "prompt": prompt if self.turn_number > 0 else f"{self.instruction}",
            "image": self.page_executor.current_screenshot,
            "response": response,
            #"url": map_url_to_real(page.url),
            "window": context.viewport_size,
            "target": self.instruction
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
