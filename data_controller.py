import json
import os
import re
import asyncio

from Pipeline.simple_test_async import main


class DataController:
    def __init__(self, data_dir, dataset_name, concurrency=1):
        self.data_dir = data_dir
        self.concurrency = concurrency
        self.dataset_name = dataset_name
        self.base_dir = f'/Users/shaw/Downloads/{dataset_name}'
        os.makedirs(f'{self.base_dir}', exist_ok=True)

        self.file_paths = [f"{data_dir}/{filename}" for filename in os.listdir(self.data_dir)][:3]

        self.semaphore = asyncio.Semaphore(self.concurrency)  # Limit concurrent tasks
        self.tasks = []

    async def run_single(self, i, doc):
        async with self.semaphore:
            instruction = doc["instruction"]
            if re.match(r"[A-Za-z0-9]", instruction[-1]):
                instruction = instruction + '.'
            instruction = instruction + f' Start on {doc["url"]}'
            print(instruction)

            screenshot_temp = f'{self.base_dir}/{doc["trace_id"]}/screenshots'
            record_temp = f'{self.base_dir}/{doc["trace_id"]}'
            os.makedirs(screenshot_temp, exist_ok=True)

            await main(instruction=instruction, _id=doc['trace_id'], url=doc['url'],
                       screenshot_temp=screenshot_temp, record_temp=record_temp)

    async def run_all(self):
        for index, file_path in enumerate(self.file_paths):
            doc = json.load(open(file_path))
            task = asyncio.create_task(self.run_single(index, doc))
            self.tasks.append(task)

        await asyncio.gather(*self.tasks)


if __name__ == '__main__':
    controller = DataController(data_dir='/Volumes/data/clean_data_en-v1-split',
                                dataset_name='clean_data_en-v1')
    asyncio.run(controller.run_all())
