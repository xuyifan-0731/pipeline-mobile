import openai
import os
import backoff
import time
from openai.error import (
    APIConnectionError,
    APIError,
    RateLimitError,
    ServiceUnavailableError,
    InvalidRequestError
)
from .templates.template_with_loop import SYSTEM_PROMPT

import base64
from dotenv import load_dotenv

config_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(config_path)

openai.api_base = "https://one-api.glm.ai/v1"
openai.api_key = os.getenv('GPT4V_TOKEN')


def run_connection_test():
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": "你好"}],
        max_tokens=1024,
        temperature=0.95
    )
    print([choice["message"]["content"] for choice in response["choices"]])


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


class Engine:
    def __init__(self) -> None:
        pass

    def tokenize(self, input):
        return self.tokenizer(input)


class OpenaiEngine(Engine):
    def __init__(
            self,
            stop=["\n\n"],
            rate_limit=-1,
            model='gpt-4-vision-preview',
            temperature=0,
            **kwargs,
    ) -> None:
        """Init an OpenAI GPT/Codex engine

        Args:
            api_key (_type_, optional): Auth key from OpenAI. Defaults to None.
            stop (list, optional): Tokens indicate stop of sequence. Defaults to ["\n"].
            rate_limit (int, optional): Max number of requests per minute. Defaults to -1.
            model (_type_, optional): Model family. Defaults to None.
        """
        self.stop = stop
        self.temperature = temperature
        self.model = model
        # convert rate limit to minmum request interval
        self.request_interval = 0 if rate_limit == -1 else 60.0 / rate_limit
        self.current_key_idx = 0
        run_connection_test()
        Engine.__init__(self, **kwargs)

    def encode_image(self, image_path):
        with open(self, image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @backoff.on_exception(
        backoff.expo,
        (APIError, RateLimitError, APIConnectionError, ServiceUnavailableError, InvalidRequestError),
    )
    def single_turn_generation(self, prompt, system_prompt, image_path, **kwargs):
        base64_image = encode_image(image_path)
        prompt2_input = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                         {"role": "user", "content": [{"type": "image_url",
                                                       "image_url": {
                                                           "url": f"data:image/jpeg;base64,{base64_image}",
                                                           "detail": "high"}, },
                                                      {"type": "text", "text": prompt}]}]
        # if current_feedback is not None:
        #     prompt2_input[-1]["content"].append({"type": "text", "text": current_feedback})
        response2 = openai.ChatCompletion.create(
            model=self.model,
            messages=prompt2_input,
            max_tokens=4096,
            temperature=self.temperature,
            **kwargs,
        )
        return [choice["message"]["content"] for choice in response2["choices"]][0]

    @backoff.on_exception(
        backoff.expo,
        (APIError, RateLimitError, APIConnectionError, ServiceUnavailableError, InvalidRequestError),
    )
    def generate(self, prompt: str, max_new_tokens=4096, temperature=None, model=None, image_path=None,
                 ouput__0=None, turn_number=0, current_feedback=None, **kwargs):
        start_time = time.time()
        if (
                self.request_interval > 0
                and start_time < self.next_avil_time[self.current_key_idx]
        ):
            time.sleep(self.next_avil_time[self.current_key_idx] - start_time)

        if turn_number == 0:
            # Assume one turn dialogue
            prompt1_input = [
                {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]},
            ]
            response1 = openai.ChatCompletion.create(
                model=model if model else self.model,
                messages=prompt1_input,
                max_tokens=max_new_tokens if max_new_tokens else 4096,
                temperature=temperature if temperature else self.temperature,
                **kwargs,
            )
            answer1 = [choice["message"]["content"] for choice in response1["choices"]][0]

            return answer1
        elif turn_number > 0:
            base64_image = encode_image(image_path)
            prompt2_input = [{"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}] + \
                            ouput__0 + \
                            [
                                {"role": "user", "content": [
                                    {"type": "image_url",
                                     "image_url": {
                                         "url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}
                                     }
                                ]},
                                {"role": "user", "content": [{"type": "text", "text": prompt}]}
                            ]
            # if current_feedback is not None:
            #     prompt2_input[-1]["content"].append({"type": "text", "text": current_feedback})
            response2 = openai.ChatCompletion.create(
                model=model if model else self.model,
                messages=prompt2_input,
                max_tokens=max_new_tokens if max_new_tokens else 4096,
                temperature=temperature if temperature else self.temperature,
                **kwargs,
            )
            return [choice["message"]["content"] for choice in response2["choices"]][0]
