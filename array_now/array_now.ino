#include "action.h"
const char *serviceUUID = "996000000000";  // 替换为您的服务UUID
const char *charUUID = "996000000000";     // 替换为您的特征值UUID
const char *deviceName = "996000000000";
String adb_L_Id = "array9960001002908";  // 边结尾是 8  凯美瑞
String adb_R_Id = "array9960001002916";  // 右边结尾是 6 凯美瑞
// String adb_L_Id = "array9960001002778";  // 边结尾是 8  任

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
  uart_long.begin(500000, SERIAL_8N1, 5, 4);
  uart_wide.begin(500000, SERIAL_8N1, 16, 17);
  // lin.begin(19200, SERIAL_8N1, 16, 17);
  Serial.begin(115200);
  readBleconfig1();
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_peer_info_t peerInfo1, peerInfo2;
  memcpy(peerInfo1.peer_addr, broadcastAddress1, 6);
  memcpy(peerInfo2.peer_addr, broadcastAddress2, 6);
  esp_now_add_peer(&peerInfo1);
  esp_now_add_peer(&peerInfo2);
  // delay(2333);

  // sendData("array9960001002916666", broadcastAddress1);
  // delay(333);
  // sendData("array9960001002916777", broadcastAddress1);
  // delay(333);
  // sendData("array9960001002916666", broadcastAddress1);
  // delay(333);
  // sendData("array9960001002916777", broadcastAddress1);
  // delay(333);
  // delay(2333);
  pixels.begin();
  pixels.setBrightness(6);
}
void adbmain() {
}
void loop() {

  uart_long_data = uart_long.read();
  uart_long_int = uart_long_data.toInt();
  if (uart_long_int >= 0) {
    zhulong = uart_long_int;
  } else {
    zhulong = "0";
  }
  uart_wide_data = uart_wide.read();
  uart_wide_int = uart_wide_data.toInt();
  if (uart_wide_int >= 0) {
    zhuwide = uart_wide_int;
  } else {
    zhuwide = "0";
  }
  if (uart_long_int >= 1) {
  }
  // adbmain();


  int value = uart_long_int;
  if (value == 99) {
    // sendData(adb_R_Id + "666", broadcastAddress1);
    adb_L = "99";
    adb_R = "99";  // 此处可以考虑是否需要与代码逻辑一致进行赋值
    // // onL();
    // // onR();
    adblight(123);
    Serial.println("full1");
    // count++;
    zhustatus = "~~~~远光全开";

    if (value == 99) {
      // onL();
      // onR();
      count++;  // 每次检测到99就增加计数器
      while (count >= 8) {
        // delay(30);  // 可以添加延迟，让你看到计数的过程（非必须）
        onL();  // 如果在计数未满10次之前再次检测到99，则再执行一次onLeft
        onR();
        fulllight(123);
        count = 0;
        break;
      }
      Serial.print("ci:");
      Serial.println(count);

    } else {
      offL();
      offR();
      count = 0;
      adblight(133);
      Serial.println("adb3");
    }


  } else if (value == 100) {
    // 特殊情况处理（如果需要处理）
    adb_L = "100";
    adb_R = "100";
    offR();
    offL();
    lowBeam();
    Serial.println("low1");
    zhustatus = "返回近光____";

  } else if (value >= 13 && value < 25) {  // 确保此条件与前面的条件互斥
    offR();
    offL();
    adb_L = 992;
    int adb_R_str = value - 12;
    adb_R = String(adb_R_str);
    zhustatus = "触发右边动作";
    //   // Serial.println(adb_R_str);
    // } else if (value == 12 || value == 11) {
    //   offR();
    //   offL();
    //   adb_L = String(value);
    //   adb_R = 5;
    //   zhustatus = "@触发左中心位置";
    // } else if (value == 13 || value == 14) {
    //   offR();
    //   offL();
    //   adb_L = 9;
    //   int adb_R_str = value - 12;
    //   adb_R = String(adb_R_str);
    //   zhustatus = "触发右中心位置$";
  } else if (value < 13) {
    adb_L = value;
    adb_R = 991;
    // Serial.print("value:");
    // Serial.println(value);
    zhustatus = "左边动作";
  } else {
    zhustatus = "未获取到摄像头状态";
    errlight();
  }

  int adbLint = adb_L.toInt();
  int adbRint = adb_R.toInt();

  // if (adbLint == 99 && adbRint == 99) {
  //   // 这里可以添加相应的逻辑处理，例如特定的操作或信息收集
  // } else {
  //   }
  // Serial.print("ADB Left:");
  // Serial.println(adb_L);  // 打印左半部分数据
  // Serial.print("ADB Right:");
  // Serial.println(adb_R);  // 打印右半部分数据
  // Serial.println("【adb L】：" + String(adb_L) + "【adb R】：" + String(adb_R));
  // sendData(adb_R_Id + "666", broadcastAddress1);
  // Serial.println("-----------广角：开右边激光---------");
  if (uart_wide_int == 66) {
    String dataToSend1 = adb_L_Id + "100";
    String dataToSend2 = adb_R_Id + "100";
    sendData(dataToSend1, broadcastAddress1);
    sendData(dataToSend2, broadcastAddress1);
    // Serial.println("广角数据：66, 不开 adb");
    offL();
    offR();
    lowBeam();
    count = 0;
    // Serial.println("low2");
    // } else if (uart_wide_int >= 0 && uart_wide_int <= 4) {
    //   String dataToSend1 = adb_L_Id + "1";  //
    //   sendData(dataToSend1, broadcastAddress1);
    // } else if (uart_wide_int >= 20 && uart_wide_int <= 24) {
    //   String dataToSend2 = adb_R_Id + "12";  //
    //   sendData(dataToSend2, broadcastAddress1);
    Serial.println("【adb状态】：" + String(zhustatus) + "【长焦】：" + String(zhulong) + "【广角】：" + String(zhuwide) + "【左透镜】：" + String(headlightL) + "【右透镜】：" + String(headlightR) + "【adb L】：" + String(adb_L) + "【adb R】：" + String(adb_R));

  } else {
    Serial.print("长焦：");
    Serial.println(value);
    if (value == 99) {
      // onL();
      // onR();
      count++;  // 每次检测到99就增加计数器
      while (count >= 5) {
        // delay(30);  // 可以添加延迟，让你看到计数的过程（非必须）
        onL();  // 如果在计数未满10次之前再次检测到99，则再执行一次onLeft
        onR();
        fulllight(123);
        count = 0;
        break;
      }
      Serial.print("ci:");
      Serial.println(count);

    } else {
      offL();
      offR();
      count = 0;
      adblight(133);
      Serial.println("adb3");
    }


    if (adbLint >= 0) {
      String dataToSend1 = adb_L_Id + adbLint;
      sendData(dataToSend1, broadcastAddress1);
      delay(33);
    }
    if (adbRint >= 0) {
      String dataToSend2 = adb_R_Id + adbRint;
      sendData(dataToSend2, broadcastAddress1);
      delay(33);
    }
    if (value >= 0) {
      Serial.println("【adb状态】：" + String(zhustatus) + "【长焦】：" + String(zhulong) + "【广角】：" + String(zhuwide) + "【左透镜】：" + String(headlightL) + "【右透镜】：" + String(headlightR) + "【adb L】：" + String(adb_L) + "【adb R】：" + String(adb_R));
    }
    // Serial.println("64, 环境够黑，可以开 adb");
  }

  // Serial.println("【长焦】：" + String(zhulong) + "【广角】：" + String(zhuwide) + "【左透镜】：" + String(headlightL) + "【右透镜】：" + String(headlightR) + "【adb L】：" + String(adb_L) + "【adb R】：" + String(adb_R));

  delay(13);
}
void onL() {
  sendData("array9960001002906666", broadcastAddress1);
  headlightL = "开";
  count = 0;
}
void offL() {
  sendData("array9960001002906777", broadcastAddress1);
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
