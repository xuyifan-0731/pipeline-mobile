import requests
import sys

import cv2


def plot_bbox(bbox, CURRENT_SCREENSHOT, prompt):
    image = cv2.imread(CURRENT_SCREENSHOT)
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 2)
    cv2.putText(image, prompt, (int(bbox[0] * 0.3), int(bbox[1] * 0.1)), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=0.5, color=(0, 0, 0), thickness=2)
    cv2.imwrite(CURRENT_SCREENSHOT.replace('.png', '-dino-test.png'), image)


def call_dino(instruction, screenshot_path):
    files = {'image': open(screenshot_path, 'rb')}
    response = requests.post("http://172.19.64.21:24026/v1/executor", files=files,
                             data={"text_prompt": f"{instruction}"})
    return [int(s) for s in response.json()['response'].split(',')]


def main(dino_prompt, CURRENT_SCREENSHOT):
    relative_bbox = call_dino(dino_prompt, CURRENT_SCREENSHOT)

    # 获取页面的视口大小
    image = cv2.imread(CURRENT_SCREENSHOT)
    viewport_height, viewport_width = image.shape[:2]
    print(image.shape)

    center_x = (relative_bbox[0] + relative_bbox[2]) / 2 * viewport_width / 100
    center_y = (relative_bbox[1] + relative_bbox[3]) / 2 * viewport_height / 100
    width_x = (relative_bbox[2] - relative_bbox[0]) * viewport_width / 100
    height_y = (relative_bbox[3] - relative_bbox[1]) * viewport_height / 100

    # 点击计算出的中心点坐标
    print(center_x, center_y)
    plot_bbox([int(center_x - width_x / 2), int(center_y - height_y / 2), int(width_x), int(height_y)],
              CURRENT_SCREENSHOT, dino_prompt)


if __name__ == '__main__':
    instruct, screenshot = sys.argv[1], sys.argv[2]
    main(instruct, screenshot)
