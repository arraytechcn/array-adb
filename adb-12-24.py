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
# serial = uart.UART(device, 500000)  # ESP32 暂时禁用
save_counter = 0

# GPS 模块（暂时禁用）
gps_enabled = False
# gps_device = "/dev/ttyS0"
# try:
#     gps_serial = uart.UART(gps_device, 9600)
#     gps_enabled = True
# except:
#     gps_enabled = False
#     print("GPS 串口初始化失败")

# GPS 数据
gps_satellites = 0  # 卫星数量
gps_speed_kmh = 0.0  # 速度 km/h
gps_buffer = ""     # GPS 数据缓冲区
gps_parse_counter = 0  # GPS 解析计数器

def parse_gps():
    """解析 GPS NMEA 数据"""
    global gps_satellites, gps_speed_kmh, gps_buffer, gps_parse_counter
    if not gps_enabled:
        return

    # 每 10 帧解析一次 GPS（GPS 数据每秒更新一次，不需要每帧解析）
    gps_parse_counter += 1
    if gps_parse_counter < 10:
        return
    gps_parse_counter = 0

    # 读取 GPS 数据
    data = gps_serial.read()
    if data:
        try:
            gps_buffer += data.decode('utf-8', errors='ignore')
            # 限制缓冲区大小
            if len(gps_buffer) > 1000:
                gps_buffer = gps_buffer[-500:]
        except:
            pass

    # 解析完整的 NMEA 语句
    while '\n' in gps_buffer:
        line, gps_buffer = gps_buffer.split('\n', 1)
        line = line.strip()

        # 解析 $GNGGA - 卫星数量
        if line.startswith('$GNGGA') or line.startswith('$GPGGA'):
            parts = line.split(',')
            if len(parts) > 7 and parts[7]:
                try:
                    gps_satellites = int(parts[7])
                except:
                    pass

        # 解析 $GNVTG - 速度 km/h
        elif line.startswith('$GNVTG') or line.startswith('$GPVTG'):
            parts = line.split(',')
            if len(parts) > 7 and parts[7]:
                try:
                    gps_speed_kmh = float(parts[7])
                except:
                    pass

# 加载YOLOv5模型
detector = nn.YOLOv5(model="/root/models/model_207754.mud", dual_buff=True)

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
    pass  # ESP32 暂时禁用
    # if not 0 <= number <= 100:
    #     raise ValueError("数字必须在0到100之间。")
    # byte_content = number.to_bytes(1, 'big')
    # serial.write(byte_content)

# 计数器
no_detection_count = 0
max_no_detection = 10
consecutive_detection_count = 0  # 新增计数器

# 停车/行车检测（四区域检测：上方路灯+中心路面+左右边缘）
prev_top = None
prev_center = None
prev_left_edge = None
prev_right_edge = None
stable_threshold = 0.85  # 稳定比例阈值
diff_threshold = 15      # 像素差异阈值
stable_count = 0
max_stable_count = 25
is_parked = False
check_interval = 5
frame_counter = 0
brightness = 0  # 环境亮度

# 目标平滑（防止闪烁）
last_objs = []  # 上一帧的目标
smooth_frames = 12  # 保持显示的帧数（增加稳定性）
no_detect_frames = 0  # 未检测到目标的帧数

# 目标跟踪（用于判断对向/同向车）
last_obj_positions = {}  # {目标ID: (x, y)}

# 蓝色框平滑扩展
left_box = None   # (min_x, min_y, max_x, max_y)
right_box = None
box_smooth_speed = 0.15  # 扩展速度 (越小越慢，效果越明显)
left_box_hold = 0   # 左框保持计数
right_box_hold = 0  # 右框保持计数
box_hold_frames = 50  # 目标消失后保持的帧数

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

    # 解析 GPS 数据
    parse_gps()

    # 保存原始图像以供保存使用（没有边框）
    original_img = img.copy()

    # 停车/行车检测（混合检测：中心+边缘，每5帧一次）
    frame_counter += 1
    if frame_counter >= check_interval:
        frame_counter = 0
        cv_img = image.image2cv(img)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (135, 90))

        # 提取四个区域
        top = gray[:25, 30:105]       # 上方路灯区域
        center = gray[40:70, 30:105]  # 中心路面区域
        left_edge = gray[:, :25]      # 左边缘
        right_edge = gray[:, -25:]    # 右边缘

        if prev_top is not None:
            # 计算各区域变化
            center_diff = cv2.absdiff(prev_center, center)
            left_diff = cv2.absdiff(prev_left_edge, left_edge)
            right_diff = cv2.absdiff(prev_right_edge, right_edge)
            top_diff = cv2.absdiff(prev_top, top)

            _, center_thresh = cv2.threshold(center_diff, diff_threshold, 255, cv2.THRESH_BINARY)
            _, left_thresh = cv2.threshold(left_diff, diff_threshold, 255, cv2.THRESH_BINARY)
            _, right_thresh = cv2.threshold(right_diff, diff_threshold, 255, cv2.THRESH_BINARY)
            _, top_thresh = cv2.threshold(top_diff, diff_threshold, 255, cv2.THRESH_BINARY)

            center_change = cv2.countNonZero(center_thresh) / center.size
            left_change = cv2.countNonZero(left_thresh) / left_edge.size
            right_change = cv2.countNonZero(right_thresh) / right_edge.size
            top_change = cv2.countNonZero(top_thresh) / top.size

            # 任意区域有明显变化就判定为行车（上方路灯区域权重更高）
            max_change = max(center_change, left_change, right_change, top_change * 2)
            stable_ratio = 1 - max_change

            # 低亮度环境下禁用停车检测（画面变化不可靠）
            if brightness < 30:
                stable_count = 0
                is_parked = False
            elif stable_ratio >= stable_threshold:
                stable_count += 1
                if stable_count >= max_stable_count:
                    is_parked = True
            else:
                stable_count = 0
                is_parked = False

        prev_top = top
        prev_center = center
        prev_left_edge = left_edge
        prev_right_edge = right_edge

        # 计算上方区域亮度（对数感知模型）
        center_gray = gray[8:38, 42:93]  # 上方区域
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
        objs = detector.detect(img, conf_th=0.3, iou_th=0.45)
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

        # 分离左右区域的目标
        left_objs = []
        right_objs = []
        screen_center = new_width // 2

        # 调试：打印目标信息
        print(f"--- 检测到 {len(objs)} 个目标 ---")

        for obj in objs:
            center_x = obj.x + obj.w // 2
            center_y = obj.y + obj.h // 2
            index = int(center_x * 24 / frame_width)
            index = min(max(index, 0), 23)

            # 调试：打印每个目标的位置
            side = "左" if center_x < screen_center else "右"
            print(f"  目标: x={center_x}, y={center_y}, w={obj.w}, h={obj.h}, 区域={side}, score={obj.score:.2f}")

            # 目标距离估算（框越大距离越近）
            if obj.h > 100:
                dist_label = "N"  # Near
            elif obj.h > 50:
                dist_label = "M"  # Mid
            else:
                dist_label = "F"  # Far

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

            # 按中心点分左右
            if center_x < screen_center:
                left_objs.append((obj, dist_label, direction))
            else:
                right_objs.append((obj, dist_label, direction))

        # 绘制左侧合并框（从画面中心向左扩展）
        if left_objs:
            left_box_hold = box_hold_frames  # 重置保持计数
            target_min_x = min(o[0].x for o in left_objs)
            target_min_y = min(o[0].y for o in left_objs)
            target_max_x = max(o[0].x + o[0].w for o in left_objs)
            target_max_y = max(o[0].y + o[0].h for o in left_objs)

            # 右边界固定在画面中心
            fixed_max_x = screen_center

            if left_box is None:
                # 从画面中心开始（宽度为0）
                left_box = (fixed_max_x, target_min_y, fixed_max_x, target_max_y)
                print(f"[左框] 新建: 从画面中心 x={fixed_max_x} 开始")

            old_min_x, old_min_y, old_max_x, old_max_y = left_box
            # 左边界只能向左扩展，不能向右收缩
            if target_min_x < old_min_x:
                new_min_x = old_min_x + (target_min_x - old_min_x) * box_smooth_speed
            else:
                new_min_x = old_min_x  # 保持不动
            new_max_x = fixed_max_x  # 右边固定在画面中心
            new_min_y = target_min_y
            new_max_y = target_max_y
            left_box = (int(new_min_x), new_min_y, new_max_x, new_max_y)
            print(f"[左框] 更新: min_x={int(new_min_x)} -> {target_min_x}, 宽度={new_max_x - int(new_min_x)}")

            min_x, min_y, max_x, max_y = left_box
            if max_x - min_x > 2:
                img.draw_rect(min_x, min_y, max_x - min_x, max_y - min_y, color=image.COLOR_BLUE, thickness=detected_border_thickness)
            obj, dist_label, direction = left_objs[0]
            msg = f'{dist_label}{direction} {obj.score:.2f}'
            img.draw_string(target_min_x, target_min_y, msg, color=image.COLOR_WHITE)
        else:
            # 目标消失后保持几帧
            if left_box_hold > 0:
                left_box_hold -= 1
                print(f"[左框] 保持中: 剩余 {left_box_hold} 帧")
                if left_box is not None:
                    min_x, min_y, max_x, max_y = left_box
                    if max_x - min_x > 2:
                        img.draw_rect(min_x, min_y, max_x - min_x, max_y - min_y, color=image.COLOR_BLUE, thickness=detected_border_thickness)
            else:
                if left_box is not None:
                    print("[左框] 清除")
                left_box = None

        # 绘制右侧合并框（从画面中心向右扩展）
        if right_objs:
            right_box_hold = box_hold_frames  # 重置保持计数
            target_min_x = min(o[0].x for o in right_objs)
            target_min_y = min(o[0].y for o in right_objs)
            target_max_x = max(o[0].x + o[0].w for o in right_objs)
            target_max_y = max(o[0].y + o[0].h for o in right_objs)

            # 左边界固定在画面中心
            fixed_min_x = screen_center

            if right_box is None:
                # 从画面中心开始（宽度为0）
                right_box = (fixed_min_x, target_min_y, fixed_min_x, target_max_y)

            old_min_x, old_min_y, old_max_x, old_max_y = right_box
            # 右边界只能向右扩展，不能向左收缩
            new_min_x = fixed_min_x  # 左边固定在画面中心
            if target_max_x > old_max_x:
                new_max_x = old_max_x + (target_max_x - old_max_x) * box_smooth_speed
            else:
                new_max_x = old_max_x  # 保持不动
            new_min_y = target_min_y
            new_max_y = target_max_y
            right_box = (new_min_x, new_min_y, int(new_max_x), new_max_y)

            min_x, min_y, max_x, max_y = right_box
            if max_x - min_x > 2:
                img.draw_rect(min_x, min_y, max_x - min_x, max_y - min_y, color=image.COLOR_BLUE, thickness=detected_border_thickness)
            obj, dist_label, direction = right_objs[0]
            msg = f'{dist_label}{direction} {obj.score:.2f}'
            img.draw_string(target_min_x, target_min_y, msg, color=image.COLOR_WHITE)
        else:
            # 目标消失后保持几帧
            if right_box_hold > 0:
                right_box_hold -= 1
                if right_box is not None:
                    min_x, min_y, max_x, max_y = right_box
                    if max_x - min_x > 2:
                        img.draw_rect(min_x, min_y, max_x - min_x, max_y - min_y, color=image.COLOR_BLUE, thickness=detected_border_thickness)
            else:
                right_box = None

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

    # 显示 GPS 信息（下方中间）
    if gps_enabled:
        gps_text = f"SAT:{gps_satellites} {gps_speed_kmh:.0f}km/h"
        gx = new_width // 2 - 80
        gy = new_height - 50
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            img.draw_string(gx+dx, gy+dy, gps_text, color=image.COLOR_BLACK, scale=2)
        img.draw_string(gx, gy, gps_text, color=image.COLOR_WHITE, scale=2)

        # GPS 速度小于 3km/h 判定为停车
        if gps_speed_kmh < 3:
            is_parked = True
        else:
            is_parked = False
            stable_count = 0

    # 在上方中间显示环境亮度（描边效果）
    lx, ly = new_width // 2 - 30, 35
    for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
        img.draw_string(lx+dx, ly+dy, f"L:{brightness}", color=image.COLOR_BLACK, scale=2)
    img.draw_string(lx, ly, f"L:{brightness}", color=image.COLOR_WHITE, scale=2)

    # 画框标出亮度测量区域（上方区域）
    bx, by, bw, bh = new_width//2 - 100, new_height//4 - 60, 200, 120
    img.draw_rect(bx, by, bw, bh, color=image.COLOR_PURPLE, thickness=2)

    # 画出停车检测的四个区域（缩放比例 4x）
    # 上方路灯区域 (top): gray[:25, 30:105]
    img.draw_rect(120, 0, 300, 100, color=image.COLOR_ORANGE, thickness=2)
    # 中心路面区域 (center): gray[40:70, 30:105]
    img.draw_rect(120, 160, 300, 120, color=image.COLOR_GREEN, thickness=2)
    # 左边缘 (left_edge): gray[:, :25]
    img.draw_rect(0, 0, 100, 360, color=image.COLOR_WHITE, thickness=2)
    # 右边缘 (right_edge): gray[:, -25:]
    img.draw_rect(440, 0, 100, 360, color=image.COLOR_WHITE, thickness=2)

    # 显示停车状态（黄色方块）
    if is_parked:
        img.draw_rect(new_width // 2 - 60, new_height // 2 - 40, 120, 80, color=image.COLOR_YELLOW, thickness=-1)
        img.draw_string(new_width // 2 - 50, new_height // 2 - 15, "STOP", color=image.COLOR_BLACK, scale=3)

    dis.show(img)
    # time.sleep(1)  # sleep some time to free some CPU usage
