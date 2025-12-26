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
serial = uart.UART(device, 500000)  # ESP32 转发器
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

# 环境亮度检测
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
recover_col_speed = 1.0  # 恢复动画速度（每帧移动的列数）
left_shade_col_range = None  # 左侧遮挡的列范围 (start, end)
right_shade_col_range = None  # 右侧遮挡的列范围 (start, end)
left_recover_col = None  # 左侧恢复到的列号（浮点数）
right_recover_col = None  # 右侧恢复到的列号（浮点数）

# LED 网格参数 (28列 x 4行)
LED_COLS = 28
LED_ROWS = 4
LED_SIZE = 8  # LED 直径
LED_GAP = 1   # LED 间距
LED_GRID_WIDTH = LED_COLS * (LED_SIZE + LED_GAP)  # 约 252 像素
LED_GRID_HEIGHT = LED_ROWS * (LED_SIZE + LED_GAP)  # 约 36 像素
LED_GRID_Y = new_height - 100  # 底部，不遮挡FPS
LED_LEFT_X = 10  # 左灯网格起始 X
LED_RIGHT_X = new_width - LED_GRID_WIDTH - 10  # 右灯网格起始 X

# LED 布局 - null 位置用 None 表示（与小程序一致）
LED_LAYOUT = {
    0: [None, None, None, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, None, None, None],
    1: [None, None, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, None, None],
    2: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    3: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
}

# LED ID 映射（与小程序一致）- 用于发送到 ESP32
LED_IDS = {
    0: [None, None, None, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, None, None, None],
    1: [None, None, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, None, None],
    2: [28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55],
    3: [200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227],
}

# 遮挡状态（用于发送到 ESP32）
# 格式紧凑：只发送列范围，255=无遮挡
last_sent_shade = None  # (left_start, left_end, right_start, right_end)
shade_change_threshold = 2  # 变化超过2列才发送

def send_shade_to_esp32(left_start, left_end, right_start, right_end):
    """发送遮挡状态到 ESP32（5字节二进制）
    格式：[0xAA, 左起始列, 左结束列, 右起始列, 右结束列]
    0xAA = 帧头，255 = 无遮挡
    """
    global last_sent_shade
    state = (left_start, left_end, right_start, right_end)

    # 防抖：只有变化超过阈值才发送
    if last_sent_shade is not None:
        l_s, l_e, r_s, r_e = last_sent_shade
        # 检查是否有显著变化
        l_changed = (left_start == 255) != (l_s == 255) or (left_start != 255 and abs(left_start - l_s) > shade_change_threshold)
        r_changed = (right_start == 255) != (r_s == 255) or (right_end != 255 and abs(right_end - r_e) > shade_change_threshold)
        if not l_changed and not r_changed:
            return  # 变化太小，跳过发送

    last_sent_shade = state
    # 发送二进制数据：帧头 + 4字节数据
    data = bytes([0xAA, left_start, left_end, right_start, right_end])
    serial.write(data)

def draw_led_grid(img, grid_x, grid_y, shade_start_col, shade_end_col, is_recovering=False, recover_col=None, is_left=True):
    """绘制 LED 网格
    shade_start_col, shade_end_col: 遮挡的列范围 (0-27)
    is_recovering: 是否在恢复动画中
    recover_col: 恢复到的列位置
    is_left: 是否是左灯（影响恢复方向）
    注意：只有上两排（第0、1行）响应遮挡，下两排（第2、3行）始终点亮
    """
    for row in range(LED_ROWS):
        for col in range(LED_COLS):
            # 检查该位置是否存在 LED
            if LED_LAYOUT[row][col] is None:
                continue  # 跳过 null 位置

            x = grid_x + col * (LED_SIZE + LED_GAP)
            y = grid_y + row * (LED_SIZE + LED_GAP)

            # 下两排（第2、3行）始终点亮
            if row >= 2:
                img.draw_rect(x, y, LED_SIZE, LED_SIZE, color=image.COLOR_WHITE, thickness=-1)
                continue

            # 上两排判断是否被遮挡
            is_shaded = shade_start_col <= col <= shade_end_col
            is_recovered = False  # 是否是���恢复的（显示紫色）

            # 恢复动画：紫色只显示在恢复前沿，推过的地方变白
            if is_recovering and recover_col is not None and is_shaded:
                if is_left:
                    # 左灯：recover_col 从 start 向 end 增加，col <= recover_col 的已恢复
                    if col <= recover_col:
                        # 紫色前沿（2列宽度）
                        if col > recover_col - 2:
                            is_recovered = True
                        is_shaded = False  # 已恢复的不再是灰色
                else:
                    # 右灯：recover_col 从 end 向 start 减少，col >= recover_col 的已恢复
                    if col >= recover_col:
                        # 紫色前沿（2列宽度）
                        if col < recover_col + 2:
                            is_recovered = True
                        is_shaded = False  # 已恢复的不再是灰色

            if is_shaded:
                img.draw_rect(x, y, LED_SIZE, LED_SIZE, color=image.COLOR_GRAY, thickness=-1)
            elif is_recovered:
                img.draw_rect(x, y, LED_SIZE, LED_SIZE, color=image.COLOR_PURPLE, thickness=-1)
            else:
                img.draw_rect(x, y, LED_SIZE, LED_SIZE, color=image.COLOR_WHITE, thickness=-1)

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

    # 计算环境亮度（每5帧一次）
    frame_counter += 1
    if frame_counter >= check_interval:
        frame_counter = 0
        cv_img = image.image2cv(img)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (135, 90))

        # 计算上方区域亮度（对数感知模型）
        center_gray = gray[8:38, 42:93]  # 上方区域
        mean_val = cv2.mean(center_gray)[0]
        # 对数变换：模拟人眼感知，低光更敏感
        if mean_val > 0:
            brightness = int(math.log(mean_val + 1) / math.log(256) * 100)
        else:
            brightness = 0

    # YOLOv5 检测
    objs = detector.detect(img, conf_th=0.3, iou_th=0.45)

    # ========== 近距离大目标检测优化 ==========
    # 如果正常检测没有结果，尝试多尺度检测
    if not objs:
        # 方案1：缩小图像检测（让大目标变成正常尺寸）
        small_img = img.resize(new_width // 2, new_height // 2)
        small_objs = detector.detect(small_img, conf_th=0.3, iou_th=0.45)
        if small_objs:
            # 将坐标映射回原图
            class ScaledObj:
                def __init__(self, obj, scale=2):
                    self.x = obj.x * scale
                    self.y = obj.y * scale
                    self.w = obj.w * scale
                    self.h = obj.h * scale
                    self.score = obj.score
                    self.class_id = obj.class_id if hasattr(obj, 'class_id') else 0
            objs = [ScaledObj(o) for o in small_objs]
            print(f"[多尺度] 缩小检测到 {len(objs)} 个目标")

    # 方案2：亮度检测补充（近距离尾灯很亮）
    if not objs and frame_counter == 0:
        # 检测画面中的高亮区域
        cv_img = image.image2cv(img)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        # 高亮阈值（尾灯通常很亮）
        _, bright_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        # 找轮廓
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # 过滤太小或太大的区域
            if 500 < area < new_width * new_height * 0.3:
                x, y, w, h = cv2.boundingRect(cnt)
                # 宽高比过滤（尾灯通常是横向的）
                if 0.5 < w / max(h, 1) < 5:
                    class BrightObj:
                        def __init__(self, x, y, w, h):
                            self.x, self.y, self.w, self.h = x, y, w, h
                            self.score = 0.5  # 亮度检测置信度
                            self.class_id = 0
                    objs.append(BrightObj(x, y, w, h))
        if objs:
            print(f"[亮度] 检测到 {len(objs)} 个高亮区域")

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

        for obj in objs:
            center_x = obj.x + obj.w // 2
            center_y = obj.y + obj.h // 2
            index = int(center_x * 24 / frame_width)
            index = min(max(index, 0), 23)

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

        # 计算左侧遮挡范围（从画面中心向左扩展）
        if left_objs:
            target_min_x = min(o[0].x for o in left_objs)
            target_min_y = min(o[0].y for o in left_objs)
            target_max_x = max(o[0].x + o[0].w for o in left_objs)
            target_max_y = max(o[0].y + o[0].h for o in left_objs)

            # 直接使用目标的实际范围（不固定到中心）
            if left_box is None:
                left_box = (target_min_x, target_min_y, target_max_x, target_max_y)

            old_min_x, old_min_y, old_max_x, old_max_y = left_box
            # 平滑更新边界
            new_min_x = old_min_x + (target_min_x - old_min_x) * box_smooth_speed
            new_max_x = old_max_x + (target_max_x - old_max_x) * box_smooth_speed
            left_box = (int(new_min_x), target_min_y, int(new_max_x), target_max_y)

            # 显示目标信息
            obj, dist_label, direction = left_objs[0]
            msg = f'{dist_label}{direction} {obj.score:.2f}'
            img.draw_string(target_min_x, target_min_y, msg, color=image.COLOR_WHITE)
            left_recover_col = None  # 有目标时停止恢复

        # 计算右侧遮挡范围（从画面中心向右扩展）
        if right_objs:
            target_min_x = min(o[0].x for o in right_objs)
            target_min_y = min(o[0].y for o in right_objs)
            target_max_x = max(o[0].x + o[0].w for o in right_objs)
            target_max_y = max(o[0].y + o[0].h for o in right_objs)

            # 使用实际目标范围（不固定在中心）
            if right_box is None:
                right_box = (target_min_x, target_min_y, target_max_x, target_max_y)

            old_min_x, old_min_y, old_max_x, old_max_y = right_box
            # 左边界平滑移动到目标左边界
            new_min_x = old_min_x + (target_min_x - old_min_x) * box_smooth_speed
            # 右边界平滑移动到目标右边界
            new_max_x = old_max_x + (target_max_x - old_max_x) * box_smooth_speed
            right_box = (int(new_min_x), target_min_y, int(new_max_x), target_max_y)

            # 显示目标信息
            obj, dist_label, direction = right_objs[0]
            msg = f'{dist_label}{direction} {obj.score:.2f}'
            img.draw_string(target_min_x, target_min_y, msg, color=image.COLOR_WHITE)
            right_recover_col = None  # 有目标时停止恢复

        no_detection_count = 0

    else:
        no_detection_count += 1
        consecutive_detection_count = 0  # 重置连续检测计数

        # 目标消失后的恢复动画（使用列号控制）
        # 左侧恢复：从 shade_start 向 shade_end 推进（从左向右）
        if left_shade_col_range is not None:
            start_col, end_col = left_shade_col_range
            if left_recover_col is None:
                left_recover_col = float(start_col)  # 从遮挡的最左边开始
            left_recover_col += recover_col_speed  # 向右推进
            # 当恢复超过 end_col 时结束
            if left_recover_col > end_col + 2:  # +2 是紫色宽度
                left_box = None
                left_recover_col = None
                left_shade_col_range = None

        # 右侧恢复：从 shade_end 向 shade_start 推进（从右向左）
        if right_shade_col_range is not None:
            start_col, end_col = right_shade_col_range
            if right_recover_col is None:
                right_recover_col = float(end_col)  # 从遮挡的最右边开始
            right_recover_col -= recover_col_speed  # 向左推进
            # 当恢复低于 start_col 时结束
            if right_recover_col < start_col - 2:  # -2 是紫色宽度
                right_box = None
                right_recover_col = None
                right_shade_col_range = None

        # print("空白归零：" + str(no_detection_count))
        border_color = image.COLOR_GREEN
        if no_detection_count >= max_no_detection:
            send_number(99)
            no_detection_count = 0
            last_sent_number = -1

    # 绘制外边框（停车时黄色加粗）
    img.draw_rect(0, 0, new_width, new_height, color=border_color, thickness=border_thickness)

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

    # 在上方中间显示环境亮度（描边效果）
    lx, ly = new_width // 2 - 30, 35
    for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
        img.draw_string(lx+dx, ly+dy, f"L:{brightness}", color=image.COLOR_BLACK, scale=2)
    img.draw_string(lx, ly, f"L:{brightness}", color=image.COLOR_WHITE, scale=2)

    # 绘制 LED 网格（左灯和右灯）
    # 左灯：根据 left_box 计算遮挡范围（直接遮挡目标所在位置）
    left_shade_start = LED_COLS  # 默认不遮挡
    left_shade_end = LED_COLS - 1
    left_is_recovering = False
    left_rc = None  # 局部变量，避免与全局 left_recover_col 冲突

    if left_recover_col is not None and left_shade_col_range is not None:
        # 恢复动画中（优先判断）- 直接使用列号
        left_is_recovering = True
        left_shade_start, left_shade_end = left_shade_col_range
        left_rc = int(left_recover_col)
    elif left_box is not None:
        min_x, _, max_x, _ = left_box
        # 直接将目标位置映射到 LED 列号（目标在哪就遮哪）
        left_shade_start = int(min_x * LED_COLS / screen_center)
        left_shade_end = int(max_x * LED_COLS / screen_center)
        left_shade_start = max(0, min(left_shade_start, LED_COLS - 1))
        left_shade_end = max(0, min(left_shade_end, LED_COLS - 1))
        # 记录当前遮挡范围（用于恢复动画）
        left_shade_col_range = (left_shade_start, left_shade_end)

    draw_led_grid(img, LED_LEFT_X, LED_GRID_Y, left_shade_start, left_shade_end, left_is_recovering, left_rc, is_left=True)

    # 右灯：根据 right_box 计算遮挡范围（直接遮挡目标所在位置）
    right_shade_start = 0
    right_shade_end = -1  # 默认不遮挡
    right_is_recovering = False
    right_rc = None  # 局部变量

    if right_recover_col is not None and right_shade_col_range is not None:
        # 恢复动画中（优先判断）- 直接使用列号
        right_is_recovering = True
        right_shade_start, right_shade_end = right_shade_col_range
        right_rc = int(right_recover_col)
    elif right_box is not None:
        min_x, _, max_x, _ = right_box
        # 直接将目标位置映射到 LED 列号（目标在哪就遮哪）
        right_shade_start = int((min_x - screen_center) * LED_COLS / (new_width - screen_center))
        right_shade_end = int((max_x - screen_center) * LED_COLS / (new_width - screen_center))
        right_shade_start = max(0, min(right_shade_start, LED_COLS - 1))
        right_shade_end = max(0, min(right_shade_end, LED_COLS - 1))
        # 记录当前遮挡范围（用于恢复动画）
        right_shade_col_range = (right_shade_start, right_shade_end)

    draw_led_grid(img, LED_RIGHT_X, LED_GRID_Y, right_shade_start, right_shade_end, right_is_recovering, right_rc, is_left=False)

    # 发送遮挡状态到 ESP32（4字节：左起始、左结束、右起始、右结束）
    # 255 表示无遮挡
    # 恢复动画期间发送 255（全开）
    if left_is_recovering:
        l_start, l_end = 255, 255
    else:
        l_start = left_shade_start if left_shade_start <= left_shade_end else 255
        l_end = left_shade_end if left_shade_start <= left_shade_end else 255

    if right_is_recovering:
        r_start, r_end = 255, 255
    else:
        r_start = right_shade_start if right_shade_start <= right_shade_end else 255
        r_end = right_shade_end if right_shade_start <= right_shade_end else 255
    send_shade_to_esp32(l_start, l_end, r_start, r_end)

    dis.show(img)
    # time.sleep(1)  # sleep some time to free some CPU usage
