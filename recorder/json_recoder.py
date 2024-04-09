import time
import os
import json


class JSONRecorder:
    def __init__(self, id, instruction, page_executor, trace_dir, xml_dir, video_recoder=None, options={}):
        self.id = id
        self.instruction = instruction
        self.page_executor = page_executor

        self.turn_number = 0
        self.trace_file_path = os.path.join(trace_dir, 'trace.jsonl')
        self.xml_file_path = os.path.join(xml_dir)
        self.contents = []
        self.xml_history = []

        if video_recoder is not None:
            self.video_recoder = video_recoder
            self.video_recoder.start_screen_record(id)

        if "reset" in options:
            with open(self.trace_file_path, 'w') as f:
                f.write('')

    def update_response(self, context, response = None, prompt="** screenshot **", need_screenshot=False, status = None):
        if need_screenshot:
            self.page_executor.update_screenshot(prefix=str(self.turn_number), suffix=status)
        step = {
            "trace_id": self.id,
            "index": self.turn_number,
            "prompt": prompt if self.turn_number > 0 else f"{self.instruction}",
            "image": self.page_executor.current_screenshot,
            "response": response,
            # "url": map_url_to_real(page.url),
            "window": context.viewport_size,
            "target": self.instruction
        }
        self.contents.append(step)
        context.get_xml(prefix=str(self.turn_number), save_dir=self.xml_file_path)


    def update_execution(self, exe_res, status = None):
        self.contents[-1]['parsed_action'] = exe_res
        with open(self.trace_file_path, 'a') as f:
            f.write(json.dumps(self.contents[-1], ensure_ascii=False) + '\n')
        '''
        if status is not None:
            self.page_executor.update_screenshot(prefix=str(self.turn_number), suffix=status)
        else:
            self.page_executor.update_screenshot(prefix=str(self.turn_number))'''

    def format_history(self):
        history = []
        for turn in self.contents:
            history.append({"role": "user", "content": [{"type": "text", "text": turn['prompt']}]})
            history.append({"role": "assistant", "content": [{"type": "text", "text": turn['response']}]})
        return history
