from maix import uart, time

# GPS 模块通常使用 9600 波特率
device = "/dev/ttyS0"
gps = uart.UART(device, 9600)

print("GPS 模块测试 - 等待数据...")
print("按 Ctrl+C 退出")

while True:
    data = gps.read()
    if data:
        try:
            text = data.decode('utf-8', errors='ignore')
            print(text, end='')
        except:
            pass
    time.sleep_ms(100)
