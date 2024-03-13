import requests
import cv2


def plot_bbox(bbox, screenshot):
    image = cv2.imread(screenshot)
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 2)
    cv2.circle(image, (int(bbox[0] + bbox[2] / 2), int(bbox[1] + bbox[3] / 2)), radius=0, color=(0, 255, 0), thickness=2)
    cv2.imwrite(screenshot.replace('.png', '-bbox.png'), image)


def call_dino(instruction, screenshot_path):
    files = {'image': open(screenshot_path, 'rb')}
    response = requests.post("http://172.19.64.42:24026/v1/executor", files=files,
                             data={"text_prompt": f"{instruction}"})
    return [int(s) for s in response.json()['response'].split(',')]


def get_relative_bbox_center(page, instruction, screenshot):
    # 获取相对 bbox
    relative_bbox = call_dino(instruction, screenshot)

    # 获取页面的视口大小
    viewport_size = page.viewport_size
    # print(viewport_size)
    viewport_width = viewport_size['width']
    viewport_height = viewport_size['height']

    center_x = (relative_bbox[0] + relative_bbox[2]) / 2 * viewport_width / 1000
    center_y = (relative_bbox[1] + relative_bbox[3]) / 2 * viewport_height / 1000
    width_x = (relative_bbox[2] - relative_bbox[0]) * viewport_width / 1000
    height_y = (relative_bbox[3] - relative_bbox[1]) * viewport_height / 1000

    # 点击计算出的中心点坐标
    # print(center_x, center_y)
    plot_bbox([int(center_x - width_x / 2), int(center_y - height_y / 2), int(width_x), int(height_y)], screenshot)

    return (int(center_x), int(center_y)), relative_bbox
