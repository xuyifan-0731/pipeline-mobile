import jsonlines
import os
import math
from PIL import Image, ImageDraw

def draw_cross_on_image(image_path, coordinates):
    # 加载图片
    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)
        x, y = coordinates

        # 定义十字架参数
        cross_length = 100  # 十字架线的长度
        line_width = 20  # 线宽

        # 绘制十字架
        # 水平线
        draw.line((x - cross_length//2, y, x + cross_length//2, y), fill="green", width=line_width)
        # 垂直线
        draw.line((x, y - cross_length//2, x, y + cross_length//2), fill="green", width=line_width)

        # 显示图片
        img.show()


def draw_arrow_on_image(image_path, start, end):
    # 加载图片
    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)

        # 箭头参数
        arrow_length = 50  # 箭头长度
        arrow_angle = math.pi / 6  # 箭头角度

        # 绘制线
        draw.line([start, end], fill="green", width=10)

        # 计算箭头方向
        angle = math.atan2(end[1] - start[1], end[0] - start[0]) + math.pi

        # 计算箭头两点
        arrow_point1 = (end[0] + arrow_length * math.cos(angle - arrow_angle),
                        end[1] + arrow_length * math.sin(angle - arrow_angle))
        arrow_point2 = (end[0] + arrow_length * math.cos(angle + arrow_angle),
                        end[1] + arrow_length * math.sin(angle + arrow_angle))

        # 绘制箭头
        draw.polygon([end, arrow_point1, arrow_point2], fill="green")

        # 显示图片
        img.show()




log_path = "/Users/xuyifan/Desktop/agent/Pipeline/label_logs/This_is_a_task_description_1712576186.0056179"

trace_file = os.path.join(log_path, "traces", "trace.jsonl")
with jsonlines.open(trace_file) as reader:
    for obj in reader:
        image = obj["image"]
        window = obj["window"]
        parsed_action = obj["parsed_action"]
        if parsed_action["type"] == "click":
            start_pos = [parsed_action["position_start"][0] * window[0], parsed_action["position_start"][1] * window[1]]
            draw_cross_on_image(image, start_pos)
        elif parsed_action["type"] == "swipe":
            start_pos = (parsed_action["position_start"][0] * window[0], parsed_action["position_start"][1] * window[1])
            end_pos = (parsed_action["position_end"][0] * window[0], parsed_action["position_end"][1] * window[1])
            draw_arrow_on_image(image, start_pos, end_pos)

