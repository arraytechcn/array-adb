#include "action.h"
const char *serviceUUID = "996000000000";  // 替换为您的服务UUID
const char *charUUID = "996000000000";     // 替换为您的特征值UUID
const char *deviceName = "996000000000";
String adb_L_Id = "array996000100680";  // 左灯 17字符
String adb_R_Id = "array996000100291";  // 右灯 17字符   

class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *pServer) {
    // 当设备连接时触发
    Serial.println("已经连接上了？ ");
    // ESP.restart();
  }

  void onDisconnect(BLEServer *pServer) {
    // 当设备断开连接时触发
    Serial.println("断开 ");
    ESP.restart();
  }
};
// 实现绿色常亮功能
void lowBeam() {
  pixels.fill(pixels.Color(0, 255, 0));
  // 显示设置的颜色
  pixels.show();
}
class MyCharacteristicCallbacks : public BLECharacteristicCallbacks {
  bool is_first_data = true;

  void onWrite(BLECharacteristic *pCharacteristic) {
    std::string value = pCharacteristic->getValue();

    if (value.length() > 0) {

      if (value.find("0offL0") != std::string::npos) {
        Serial.println("关左远光");
        offL();
      } else if (value.find("0offL1") != std::string::npos) {
        onL();
      } else if (value.find("0offR0") != std::string::npos) {
        offR();
      } else if (value.find("0offR1") != std::string::npos) {
        onR();
      } else if (value.find("1debug1") != std::string::npos) {
        Serial.println("调灯模式");  // 将std::string转换为C风格的字符串
      } else if (value.find("0adbdebug") != std::string::npos) {
        for (int i = 1; i <= 24; ++i) {
          std::string debugKey = "0adbdebug" + std::to_string(i);
          size_t index = value.find(debugKey);
          if (index != std::string::npos) {  // 如果找到了debugKey
            if (i > 12) {
              Serial.println("蓝牙调试，大于 12");
              // 假设 adb_R_Id 是一个字符串，并且 i 是一个整数
              String dataToSend1 = String(i);                        // 将 i 转换成字符串再进行拼接
              int newtosend = dataToSend1.toInt();                   // 将字符串转换成整数
              newtosend = newtosend - 12;                            // 从整数中减去 12
              String newtosendstr = String(newtosend);               // 将新的整数值转换回字符串
              sendData(adb_R_Id + newtosendstr, broadcastAddress1);  // 发送字符串
              Serial.println(newtosendstr);                          // 输出到串口监视器
            } else if (i < 12) {
              Serial.println("蓝牙调试，小于 12");
              String dataToSend2 = adb_L_Id + i;
              sendData(dataToSend2, broadcastAddress1);
              Serial.println(dataToSend2);
            }
            Serial.println(debugKey.c_str());
          }
        }
      }


    } else {
      if (is_first_data) {
        Serial.println("开始");
        clrDataToFile("1");
        is_first_data = false;
      }

      for (int i = 0; i < value.length(); i++) {
        char c = value[i];
        if (isalnum(c)) {
          Serial.print(c);
          writeDataToFile(c);  // 将接收到的字符写入文件中
        }
      }

      // 如果接收到的值中包含"0end0"，表示数据接收完成
      if (value.find("0end0") != std::string::npos) {
        Serial.println("数据接收完成");
        file.close();  // 关闭文件句柄
        ESP.restart();
      }

      // 检查是否以"88996"开头，并且后面跟着12位数字
      if (value.find("0jjj0") != std::string::npos && value.length() >= 17) {
        // 截取12位数字部分并打印
        // Serial.print("检测到以88996开头的12位数字：");
        std::string number = value.substr(value.find("0jjj0") + 5, 12);

        // delay(5555);
        Serial.println(number.c_str());  // 将std::string转换为C风格的字符串
        if (writeBleFile(number.c_str(), "996000000069")) {
          Serial.println("UUID已写入到 ble.txt 文件中。");
          delay(232);
          ESP.restart();
        }
      }

      if (value.find("0jjb0") != std::string::npos && value.length() >= 17) {
        // 截取12位数字部分并打印
        // Serial.print("检测到以88996开头的12位数字：");
        std::string number = value.substr(value.find("0jjb0") + 5, 12);

        // delay(5555);
        Serial.println(number.c_str());  // 将std::string转换为C风格的字符串
        clrDataToFile_ble("1");
        delay(232);
        ESP.restart();
      }
    }
  }
  // }




  // 写入数据到文件
  void writeDataToFile(char data) {
    if (!file) {
      file = SPIFFS.open("/low.txt", "a");  // 如果文件未打开，则以追加模式打开文件
      if (!file) {
        Serial.println("Failed to open file for writing");
        return;
      }
    }

    size_t bytesWritten = file.write((const uint8_t *)&data, sizeof(data));
    if (bytesWritten != sizeof(data)) {
      Serial.println("Write failed");
    }

    delay(1);  // 添加延迟以释放资源
  }
};
void readBleconfig1() {
  if (SPIFFS.begin()) {
    Serial.println("read Ble config");
    // 尝试打开文件
    File fileble = SPIFFS.open("/ble.txt", "r");
    if (fileble) {
      Serial.println("正在读取 ble.txt 文件...");

      // 读取文件内容
      String fileContent = fileble.readString();  // 修改此处
      fileble.close();

      // 替换默认的UUID
      int index = fileContent.indexOf(',');
      if (index != -1) {
        String newServiceUUID = fileContent.substring(0, index);
        String newCharUUID = fileContent.substring(index + 1);

        String tempServiceUUID = "0000FFF0-0000-1000-8000-" + newServiceUUID;
        String tempCharUUID = "0000FFF1-0000-1000-8000-" + newServiceUUID;
        tempdeviceNameUUID = "arrayadb" + newServiceUUID;

        serviceUUID = tempServiceUUID.c_str();
        charUUID = tempCharUUID.c_str();
        deviceName = tempdeviceNameUUID.c_str();

        Serial.print("readBleconfig: 读取到了 ble.txt ");


        // 初始化BLE设备
        BLEDevice::init(deviceName);
        pServer = BLEDevice::createServer();
        pServer->setCallbacks(new MyServerCallbacks());
        pService = pServer->createService(serviceUUID);
        pCharacteristic = pService->createCharacteristic(
          charUUID,
          BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_NOTIFY);

        pCharacteristic->setCallbacks(new MyCharacteristicCallbacks());
        pCharacteristic->addDescriptor(new BLE2902());
        pService->start();
        pServer->getAdvertising()->start();
        Serial.println("等待连接...");
      } else {
        Serial.println("ble.txt 文件格式无效。");

        serviceUUID = "0000FFF0-0000-1000-8000-996000000000";
        charUUID = "0000FFF1-0000-1000-8000-996000000000";
        deviceName = "arrayadb996000000000";

        // Serial.print("readBleconfig服务 serviceUUID: ");
        // Serial.println(serviceUUID);
        // Serial.print("readBleconfig特征 charUUID: ");
        // Serial.println(charUUID);
        // Serial.print("readBleconfig设备 deviceName: ");
        // Serial.println(deviceName);

        // 初始化BLE设备
        BLEDevice::init(deviceName);
        pServer = BLEDevice::createServer();
        pServer->setCallbacks(new MyServerCallbacks());
        pService = pServer->createService(serviceUUID);
        pCharacteristic = pService->createCharacteristic(
          charUUID,
          BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_NOTIFY);

        pCharacteristic->setCallbacks(new MyCharacteristicCallbacks());
        pCharacteristic->addDescriptor(new BLE2902());
        pService->start();
        pServer->getAdvertising()->start();
        Serial.println("等待连接...");


        // if (writeBleFile("996000000000", "0000FFF0-0000-1000-8000-996000000005")) {
        //   Serial.println("UUID已写入到 ble.txt 文件中。");
        // } else {
        //   Serial.println("无法将UUID写入到 ble.txt 文件。");
        // }
      }
    } else {
      Serial.println("无法打开 ble.txt 文件。");
    }
  } else {
    Serial.println("readBleconfig 无法启动 SPIFFS。");
  }
  Serial.print("readBleconfig服务 serviceUUID: ");
  Serial.println(serviceUUID);
  Serial.print("readBleconfig特征 charUUID: ");
  Serial.println(charUUID);
  Serial.print("readBleconfig设备 deviceName: ");
  Serial.println(deviceName);
}

void setup() {
  uart_cam.begin(500000, SERIAL_8N1, 16, 17);  // 单目摄像头
  Serial.begin(115200);
  Serial.println("array_now 启动");

  // 初始化BLE (用于被小程序连接配置)
  BLEDevice::init("arrayadb_now");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());
  pService = pServer->createService("0000FFF0-0000-1000-8000-996000000000");
  pCharacteristic = pService->createCharacteristic(
    "0000FFF1-0000-1000-8000-996000000000",
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_NOTIFY);
  pCharacteristic->setCallbacks(new MyCharacteristicCallbacks());
  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();
  pServer->getAdvertising()->start();

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_peer_info_t peerInfo1;
  memset(&peerInfo1, 0, sizeof(peerInfo1));
  memcpy(peerInfo1.peer_addr, broadcastAddress1, 6);
  peerInfo1.channel = 0;  // 0 = 当前channel
  peerInfo1.encrypt = false;
  if (esp_now_add_peer(&peerInfo1) != ESP_OK) {
    Serial.println("添加peer失败");
  } else {
    Serial.println("添加peer成功");
  }

  pixels.begin();
  pixels.setBrightness(6);

  // ADB 测试动画：下两排全开，上两排移动
  delay(1000);
  Serial.println("ADB 测试开始");

  // Row2: 28-55, Row3: 200-227 (下两排，固定全开)
  // Row0: 80-101 (去掉null), Row1: 56-79 (去掉null) (上两排，做移动)

  // 全开
  uint8_t allLeds[112];
  int cnt = 0;
  for (int i = 80; i <= 101; i++) allLeds[cnt++] = i;   // Row0: 22个
  for (int i = 56; i <= 79; i++) allLeds[cnt++] = i;    // Row1: 24个
  for (int i = 28; i <= 55; i++) allLeds[cnt++] = i;    // Row2: 28个
  for (int i = 200; i <= 227; i++) allLeds[cnt++] = i;  // Row3: 28个
  Serial.print("全开LED总数: ");
  Serial.println(cnt);  // 应该是 102
  Serial.print("最后几个LED ID: ");
  Serial.print(allLeds[cnt-3]); Serial.print(",");
  Serial.print(allLeds[cnt-2]); Serial.print(",");
  Serial.println(allLeds[cnt-1]);  // 应该是 225,226,227
  sendLedIds(adb_L_Id, allLeds, cnt, broadcastAddress1);
  sendLedIds(adb_R_Id, allLeds, cnt, broadcastAddress1);
  delay(1000);

  // 上两排逐渐遮挡（从右向左）
  for (int col = 24; col >= 5; col -= 2) {
    cnt = 0;
    // Row0: 80+col (col 3-24 有效)
    for (int c = 3; c <= col; c++) allLeds[cnt++] = 80 + (c - 3);
    // Row1: 56+col (col 2-25 有效)
    for (int c = 2; c <= col; c++) allLeds[cnt++] = 56 + (c - 2);
    // Row2 & Row3 全开
    for (int i = 28; i <= 55; i++) allLeds[cnt++] = i;
    for (int i = 200; i <= 227; i++) allLeds[cnt++] = i;
    sendLedIds(adb_L_Id, allLeds, cnt, broadcastAddress1);
    sendLedIds(adb_R_Id, allLeds, cnt, broadcastAddress1);
    delay(600);
  }
  delay(1000);

  // 上两排逐渐恢复
  for (int col = 5; col <= 24; col += 2) {
    cnt = 0;
    for (int c = 3; c <= col; c++) allLeds[cnt++] = 80 + (c - 3);
    for (int c = 2; c <= col; c++) allLeds[cnt++] = 56 + (c - 2);
    for (int i = 28; i <= 55; i++) allLeds[cnt++] = i;
    for (int i = 200; i <= 227; i++) allLeds[cnt++] = i;
    sendLedIds(adb_L_Id, allLeds, cnt, broadcastAddress1);
    sendLedIds(adb_R_Id, allLeds, cnt, broadcastAddress1);
    delay(600);
  }

  // 全开
  cnt = 0;
  for (int i = 80; i <= 101; i++) allLeds[cnt++] = i;
  for (int i = 56; i <= 79; i++) allLeds[cnt++] = i;
  for (int i = 28; i <= 55; i++) allLeds[cnt++] = i;
  for (int i = 200; i <= 227; i++) allLeds[cnt++] = i;
  sendLedIds(adb_L_Id, allLeds, cnt, broadcastAddress1);
  sendLedIds(adb_R_Id, allLeds, cnt, broadcastAddress1);
  Serial.println("ADB 测试完成");
}
void adbmain() {
}

// LED 位置映射（与 headlight 一致）
const uint8_t LED_ROW0[] = {0,0,0, 80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101, 0,0,0};  // 22个有效
const uint8_t LED_ROW1[] = {0,0, 56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79, 0,0};  // 24个有效
const uint8_t LED_ROW2[] = {28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55};  // 28个
const uint8_t LED_ROW3[] = {200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227};  // 28个

// 构建 ADB LED 列表：上两行根据列范围，下两行全开
void buildAdbLeds(uint8_t* leds, int& count, int fromCol, int toCol) {
  count = 0;
  // 上两行：根据列范围点亮
  for (int col = fromCol; col <= toCol && col < 28; col++) {
    if (LED_ROW0[col] > 0) leds[count++] = LED_ROW0[col];
  }
  for (int col = fromCol; col <= toCol && col < 28; col++) {
    if (LED_ROW1[col] > 0) leds[count++] = LED_ROW1[col];
  }
  // 下两行：始终全开
  for (int i = 0; i < 28; i++) leds[count++] = LED_ROW2[i];
  for (int i = 0; i < 28; i++) leds[count++] = LED_ROW3[i];
}

// 全开 LED 列表（缓存）
uint8_t allLedsCache[112];
int allLedsCacheCount = 0;
unsigned long lastSendTime = 0;
bool testModeSent = false;  // 测试模式是否已发送

// 状态缓存，避免重复发送
uint8_t last_l_start = 255, last_l_end = 255;
uint8_t last_r_start = 255, last_r_end = 255;

// 命令队列
struct LedCommand {
  String prefix;
  uint8_t ledIds[112];
  uint8_t count;
  bool valid;
};
#define QUEUE_SIZE 8
LedCommand cmdQueue[QUEUE_SIZE];
int queueHead = 0;
int queueTail = 0;
unsigned long lastQueueSendTime = 0;
const unsigned long QUEUE_SEND_INTERVAL = 100;  // 队列发送间隔 100ms

// 添加命令到队列
void enqueueCmd(String prefix, uint8_t* leds, uint8_t cnt) {
  int nextTail = (queueTail + 1) % QUEUE_SIZE;
  if (nextTail == queueHead) {
    // 队列满，丢弃最旧的
    queueHead = (queueHead + 1) % QUEUE_SIZE;
  }
  cmdQueue[queueTail].prefix = prefix;
  cmdQueue[queueTail].count = cnt;
  for (int i = 0; i < cnt; i++) {
    cmdQueue[queueTail].ledIds[i] = leds[i];
  }
  cmdQueue[queueTail].valid = true;
  queueTail = nextTail;
}

// 处理队列中的命令
void processQueue() {
  if (queueHead == queueTail) return;  // 队列空
  if (millis() - lastQueueSendTime < QUEUE_SEND_INTERVAL) return;  // 间隔未到

  if (cmdQueue[queueHead].valid) {
    sendLedIds(cmdQueue[queueHead].prefix, cmdQueue[queueHead].ledIds,
               cmdQueue[queueHead].count, broadcastAddress1);
    cmdQueue[queueHead].valid = false;
  }
  queueHead = (queueHead + 1) % QUEUE_SIZE;
  lastQueueSendTime = millis();
}

void loop() {
  // 先处理队列中的命令
  processQueue();

  // 读取二进制数据（5字节：0xAA + L_start + L_end + R_start + R_end）
  if (uart_cam.available() >= 5) {
    uint8_t header = uart_cam.read();
    if (header == 0xAA) {
      uint8_t l_start = uart_cam.read();
      uint8_t l_end = uart_cam.read();
      uint8_t r_start = uart_cam.read();
      uint8_t r_end = uart_cam.read();

      // 只有状态变化时才加入队列
      bool l_changed = (l_start != last_l_start);
      bool r_changed = (r_end != last_r_end);

      if (l_changed) {
        uint8_t ledIds[112];
        int ledCount = 0;
        if (l_start == 255) {
          buildAdbLeds(ledIds, ledCount, 0, 27);
        } else {
          buildAdbLeds(ledIds, ledCount, 0, l_start > 0 ? l_start - 1 : -1);
        }
        enqueueCmd(adb_L_Id, ledIds, ledCount);  // 加入队列
        last_l_start = l_start;
        last_l_end = l_end;
      }

      if (r_changed) {
        uint8_t ledIds[112];
        int ledCount = 0;
        if (r_start == 255) {
          buildAdbLeds(ledIds, ledCount, 0, 27);
        } else {
          buildAdbLeds(ledIds, ledCount, r_end < 27 ? r_end + 1 : 28, 27);
        }
        enqueueCmd(adb_R_Id, ledIds, ledCount);  // 加入队列
        last_r_start = r_start;
        last_r_end = r_end;
      }

      // LED 状态指示
      if (l_start == 255 && r_start == 255) {
        fulllight(123);
      } else {
        adblight(133);
      }

      lastSendTime = millis();
      testModeSent = false;
    }
  } else {
    // 没有摄像头数据时，只发送一次全开命令
    if (!testModeSent && millis() - lastSendTime > 3000) {
      if (allLedsCacheCount == 0) {
        for (int i = 80; i <= 101; i++) allLedsCache[allLedsCacheCount++] = i;
        for (int i = 56; i <= 79; i++) allLedsCache[allLedsCacheCount++] = i;
        for (int i = 28; i <= 55; i++) allLedsCache[allLedsCacheCount++] = i;
        for (int i = 200; i <= 227; i++) allLedsCache[allLedsCacheCount++] = i;
      }
      enqueueCmd(adb_L_Id, allLedsCache, allLedsCacheCount);
      enqueueCmd(adb_R_Id, allLedsCache, allLedsCacheCount);
      Serial.println("空闲: 全开");
      testModeSent = true;
    }
  }

  delay(5);
}
void onL() {
  sendData(adb_L_Id + "666", broadcastAddress1);
  headlightL = "开";
  count = 0;
}
void offL() {
  sendData(adb_L_Id + "777", broadcastAddress1);
  headlightL = "关";
  count = 0;
}
void onR() {
  sendData(adb_R_Id + "666", broadcastAddress1);
  headlightR = "开";
}
void offR() {
  sendData(adb_R_Id + "777", broadcastAddress1);
  headlightR = "关";
}
void sendData(String data, uint8_t *receiverAddress) {
  // Create a variable to hold the data
  uint8_t dataBytes[data.length() + 1];
  data.getBytes(dataBytes, data.length() + 1);
  Serial.print("wifi 发送：");
  Serial.println(data);
  // Send data
  esp_now_send(receiverAddress, dataBytes, data.length() + 1);
}

// 发送 LED ID 列表: prefix + 'S' + count + ids
void sendLedIds(String prefix, uint8_t* ledIds, uint8_t count, uint8_t* receiverAddress) {
  uint8_t data[150];
  int len = prefix.length();
  // 手动复制，避免 getBytes 添加 null 终止符
  for (int i = 0; i < len; i++) {
    data[i] = prefix[i];
  }
  data[len] = 'S';
  data[len + 1] = count;
  for (int i = 0; i < count; i++) {
    data[len + 2 + i] = ledIds[i];
  }
  Serial.print("发送LED数量: ");
  Serial.println(count);
  esp_now_send(receiverAddress, data, len + 2 + count);
}
