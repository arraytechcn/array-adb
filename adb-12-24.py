import os
import random
import math

from maix import camera, display, image, nn, app, time, uart, touchscreen
import cv2
import numpy as np
from datetime import datetime

# 边框粗细定义
border_thickness = 15  # 原始粗细
border_thickness *= 2  # 加粗5倍
detected_border_thickness = 6  # 识别到目标的蓝色框粗细
blue_box_thickness = 6  # 蓝色方框的粗细

# UART设备和YOLOv5模型设置
device = "/dev/ttyS0"
serial = uart.UART(device, 500000)
save_counter = 0

# 加载YOLOv5模型
detector = nn.YOLOv5(model="/root/models/model_159818.mud", dual_buff=True)

# 新的分辨率
new_width = 1080 // 2
new_height = 720 // 2

# 更新摄像头设置
cam = camera.Camera(new_width, new_height, detector.input_format())
dis = display.Display()

# 画面宽度
frame_width = detector.input_width()

# 初始化索引和数字
last_sent_index = -1
last_sent_number = -1

# 初始化触摸屏
ts = touchscreen.TouchScreen()

# 初始化变量以跟踪蓝色方框状态
box_added = False  # 是否已经添加蓝色方框

def save_image(original_img, counter):
    if counter % 18 == 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = random.randint(1000, 9999)
        file_path = os.path.join("/root/images", f"{timestamp}_{random_suffix}.jpg")
        try:
            original_img.save(file_path)
            print(f"保存图像到 {file_path}")
        except Exception as e:
            print(f"图像保存失败: {e}")

def save_detected_image(original_img):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = random.randint(1000, 9999)
    file_path = os.path.join("/root/pic9162/ok", f"{timestamp}_{random_suffix}.jpg")
    try:
        original_img.save(file_path)
        print(f"保存图像到 {file_path}")
    except Exception as e:
        print(f"图像保存失败: {e}")

def send_number(number):
    if not 0 <= number <= 100:
        raise ValueError("数字必须在0到100之间。")
    byte_content = number.to_bytes(1, 'big')
    serial.write(byte_content)

# 计数器
no_detection_count = 0
max_no_detection = 10
consecutive_detection_count = 0  # 新增计数器

# 停车/行车检测（稳定性检测）
prev_frame = None
stable_threshold = 0.95  # 95%稳定才判定为停车
stable_count = 0
max_stable_count = 12
is_parked = False
check_interval = 5
frame_counter = 0
brightness = 0  # 环境亮度

# 目标平滑（防止闪烁）
last_objs = []  # 上一帧的目标
smooth_frames = 5  # 保持显示的帧数
no_detect_frames = 0  # 未检测到目标的帧数

# 目标跟踪（用于判断对向/同向车）
last_obj_positions = {}  # {目标ID: (x, y)}

def logo():
    logo_path = "/root/logo320.png"
    logo0 = cv2.imread(logo_path)
    img = logo0.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 150, 255)
    edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    img_show = cv2.addWeighted(img, 0.8, edges_colored, 0.2, 0)

    img_show = image.cv2image(img_show)
    dis.show(img_show)
    time.sleep(3)

logo()

# 初始化计时器和帧计数器
frame_count = 0
start_time = datetime.now()

while not app.need_exit():
    frame_start_time = datetime.now()  # 记录每帧的开始时间
    img = cam.read()

    # 保存原始图像以供保存使用（没有边框）
    original_img = img.copy()

    # 停车/行车检测（稳定性比例检测，每5帧一次）
    frame_counter += 1
    if frame_counter >= check_interval:
        frame_counter = 0
        cv_img = image.image2cv(img)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (135, 90))
        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            total_pixels = 135 * 90
            changed_pixels = cv2.countNonZero(thresh)
            stable_ratio = 1 - (changed_pixels / total_pixels)
            if stable_ratio >= stable_threshold:
                stable_count += 1
                if stable_count >= max_stable_count:
                    is_parked = True
            else:
                stable_count = 0
                is_parked = False
        prev_frame = gray
        # 计算中心区域亮度（对数感知模型）
        center_gray = gray[30:60, 42:93]
        mean_val = cv2.mean(center_gray)[0]
        # 对数变换：模拟人眼感知，低光更敏感
        if mean_val > 0:
            brightness = int(math.log(mean_val + 1) / math.log(256) * 100)
        else:
            brightness = 0

    # 根据停车状态决定是否执行 YOLOv5 检测
    if is_parked:
        objs = []
        border_color = image.COLOR_YELLOW
        parked_border = 40  # 停车时加粗边框
    else:
        objs = detector.detect(img, conf_th=0.5, iou_th=0.45)
        parked_border = border_thickness

    # 目标平滑：如果当前没检测到但之前有，保持显示几帧
    if objs:
        last_objs = objs
        no_detect_frames = 0
    elif last_objs and no_detect_frames < smooth_frames:
        objs = last_objs  # 使用上一帧的目标
        no_detect_frames += 1
    else:
        last_objs = []

    # 检测触摸事件
    x, y, pressed = ts.read()

    if pressed:
        # 检测是否触摸了屏幕的中心区域
        screen_center_x = new_width // 2
        screen_center_y = new_height // 2
        touch_radius = 50  # 定义一个中心区域的半径

        # 如果触摸点在中心区域
        if abs(x - screen_center_x) <= touch_radius and abs(y - screen_center_y) <= touch_radius:
            print(f"屏幕中心被触摸, x: {x}, y: {y}")

            # 切换蓝色方框的显示状态
            box_added = not box_added

    if objs:
        if len(objs) > 3:
            print("目标太多")
            send_number(100)
            border_color = image.COLOR_WHITE
        else:
            border_color = image.COLOR_RED

        for obj in objs:
            center_x = obj.x + obj.w // 2
            center_y = obj.y + obj.h // 2
            index = int(center_x * 24 / frame_width)
            index = min(max(index, 0), 23)

            # 目标距离估算（框越大距离越近）
            if obj.h > 100:
                dist_label = "近"
            elif obj.h > 50:
                dist_label = "中"
            else:
                dist_label = "远"

            # 对向/同向车判断
            obj_id = f"{index}"  # 简单用区域索引作为ID
            direction = ""
            if obj_id in last_obj_positions:
                last_x = last_obj_positions[obj_id][0]
                dx = center_x - last_x
                if dx > 5:
                    direction = "→"  # 向右移动
                elif dx < -5:
                    direction = "←"  # 向左移动
            last_obj_positions[obj_id] = (center_x, center_y)

            if index != last_sent_index and (last_sent_number is None or abs(index - last_sent_number) > 1):
                send_number(index)
                last_sent_number = index
                last_sent_index = index

            img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_BLUE, thickness=detected_border_thickness)
            fill_width = obj.w
            fill_height = obj.h // 3
            img.draw_rect(obj.x, obj.y + obj.h - fill_height, fill_width, fill_height, color=image.COLOR_RED)

            # 显示距离和方向
            msg = f'{dist_label}{direction} {obj.score:.2f}'
            img.draw_string(obj.x, obj.y, msg, color=image.COLOR_WHITE)

        no_detection_count = 0

    else:
        no_detection_count += 1
        consecutive_detection_count = 0  # 重置连续检测计数

        # print("空白归零：" + str(no_detection_count))
        border_color = image.COLOR_GREEN
        if no_detection_count >= max_no_detection:
            send_number(99)
            no_detection_count = 0
            last_sent_number = -1

    # 绘制外边框（停车时黄色加粗）
    img.draw_rect(0, 0, new_width, new_height, color=border_color, thickness=parked_border)

    # 如果已经添加蓝色方框，则绘制比绿色方框小一圈的蓝色方框
    if box_added:
        blue_box_margin = 20  # 蓝色框相对于绿色框的缩进距离
        img.draw_rect(blue_box_margin, blue_box_margin, new_width - 2 * blue_box_margin, new_height - 2 * blue_box_margin, color=image.COLOR_BLUE, thickness=blue_box_thickness)
        save_image(original_img, save_counter)  # 使用原始图像进行保存
        save_counter += 1

    # 计算 FPS 并显示在画面右上角
    frame_count += 1
    elapsed_time = (datetime.now() - start_time).total_seconds()
    if elapsed_time >= 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = datetime.now()
    else:
        fps = frame_count / (datetime.now() - start_time).total_seconds()

    # 在右上角显示 FPS
    fps_text = f"FPS: {fps:.2f}"
    img.draw_string(20, new_height - 50, fps_text, color=image.COLOR_BLACK, scale=2)  # 将文本绘制在左下角，scale=2 为大字体

    # 在上方中间显示环境亮度（描边效果）
    lx, ly = new_width // 2 - 30, 35
    for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
        img.draw_string(lx+dx, ly+dy, f"L:{brightness}", color=image.COLOR_BLACK, scale=2)
    img.draw_string(lx, ly, f"L:{brightness}", color=image.COLOR_WHITE, scale=2)

    # 画框标出亮度测量区域（原图中心 200x120）
    bx, by, bw, bh = new_width//2 - 100, new_height//2 - 60, 200, 120
    img.draw_rect(bx, by, bw, bh, color=image.COLOR_PURPLE, thickness=2)

    # 显示停车状态（黄色方块）
    if is_parked:
        img.draw_rect(new_width // 2 - 60, new_height // 2 - 40, 120, 80, color=image.COLOR_YELLOW, thickness=-1)
        img.draw_string(new_width // 2 - 50, new_height // 2 - 15, "STOP", color=image.COLOR_BLACK, scale=3)

    dis.show(img)
    # time.sleep(1)  # sleep some time to free some CPU usage
