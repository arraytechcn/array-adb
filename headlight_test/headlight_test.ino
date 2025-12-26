// ESP-NOW 接收测试 - 最简版本
#include <esp_now.h>
#include <WiFi.h>

String myDeviceId = "array996000100680";  // 设备ID前缀

void onDataRecv(const uint8_t *mac_addr, const uint8_t *data, int data_len) {
  Serial.print("[收到] MAC: ");
  for (int i = 0; i < 6; i++) {
    Serial.printf("%02X", mac_addr[i]);
    if (i < 5) Serial.print(":");
  }
  Serial.print(" 长度: ");
  Serial.print(data_len);
  Serial.print(" 数据: ");

  String receivedData = "";
  for (int i = 0; i < data_len; i++) {
    receivedData += (char)data[i];
  }
  Serial.println(receivedData);

  // 检查是否匹配设备ID
  if (receivedData.startsWith(myDeviceId)) {
    String cmd = receivedData.substring(17);
    Serial.print("[匹配] 命令: ");
    Serial.println(cmd);
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("\n\n=== ESP-NOW 接收测试 ===");

  WiFi.mode(WIFI_STA);
  Serial.print("MAC地址: ");
  Serial.println(WiFi.macAddress());
  Serial.print("设备ID: ");
  Serial.println(myDeviceId);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW 初始化失败!");
    return;
  }

  esp_now_register_recv_cb(onDataRecv);
  Serial.println("ESP-NOW 初始化成功，等待数据...");
}

void loop() {
  delay(1000);
}
