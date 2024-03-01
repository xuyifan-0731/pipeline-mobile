import requests
import cv2

from PIL import Image, ImageDraw

def format_bbox(bbox, window=(1280, 720)):
    x1 = min(int(bbox[0] / window[0] * 1000), 999)
    y1 = min(int(bbox[1] / window[1] * 1000), 999)
    x2 = min(int(bbox[2] / window[0] * 1000) + x1, 999)
    y2 = min(int(bbox[3] / window[1] * 1000) + y1, 999)
    return f"{x1:03d},{y1:03d},{x2:03d},{y2:03d}"


def plot_bbox(bbox, CURRENT_SCREENSHOT):
    image = cv2.imread(CURRENT_SCREENSHOT)
    bbox = [int(i) for i in bbox]
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 2)
    # cv2.putText(image, prompt, (int(bbox[0] * 0.3), int(bbox[1] * 0.1)), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
    #             fontScale=0.5, color=(0, 0, 0), thickness=2)
    cv2.imwrite(CURRENT_SCREENSHOT.replace('.png', '-dino-test.png'), image)


def draw_rectangle_on_image(image_path, bbox_string):
    image_obj = Image.open(image_path)
    # Initialize ImageDraw
    draw = ImageDraw.Draw(image_obj)

    # Define the rectangle coordinates (left, top, right, bottom)
    bbox = [int(piece) / 1000 for piece in bbox_string.split(',')]
    x, y, width, height = bbox[0] * image_obj.size[0], bbox[1] * image_obj.size[1], (bbox[2] - bbox[0]) * \
                          image_obj.size[0], (bbox[3] - bbox[1]) * image_obj.size[1]
    rect_coords = [x, y, x + width, y + height]

    # Draw the rectangle
    draw.rectangle(rect_coords, outline='green', width=2)
    image_obj.save(image_path.replace('.png', '-image-draw-test.png'))


def call_box2caption(bbox, screenshot_path, window=(1280, 720)):
    files = {'image': open(screenshot_path, 'rb')}
    instruction = f"Tell me what you see within the designated area [[{format_bbox(bbox, window)}]] in the screenshot."
    response = requests.post("http://172.19.64.21:24025/v1/box2caption", files=files,
                             data={"text_prompt": instruction})
    return response.json()['response']


if __name__ == '__main__':
    # instruct, screenshot = sys.argv[1], sys.argv[2]
    screenshot = "test_cases/reddit-3.png"
    # bbox = (154.16, 279.67, 29.86, 14.00)
    # bbox = (151.16, 685.22, 60.45, 14)
    bbox = (1002.1, 432.13, 108.25, 37)  # x, y, w, h
    plot_bbox(bbox, screenshot)
    draw_rectangle_on_image(screenshot, format_bbox(bbox))
    print(call_box2caption(bbox, screenshot))
