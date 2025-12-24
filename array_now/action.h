#include <esp_now.h>
#include <WiFi.h>
#include <Arduino.h>
#include <HardwareSerial.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <SPIFFS.h>
#include <FS.h>
#include <mbedtls/aes.h>
#include <mbedtls/entropy.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/cipher.h>
#include <HardwareSerial.h>
#include <Adafruit_NeoPixel.h>
#define NUMPIXELS 8
#define PIN 25
// 定义颜色变化的速度
#define GRADIENT_SPEED 5
// 定义渐变阶段的长度
#define GRADIENT_LENGTH 50
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

int loopCount;
File file;
String tempdeviceNameUUID = "arrayadb996000000000";
// 初始化 UART
BLEServer *pServer;
BLEService *pService;
BLECharacteristic *pCharacteristic;
HardwareSerial uart_long(1);
HardwareSerial uart_wide(2);
// Replace the following with the MAC address of your receiver devices
uint8_t broadcastAddress1[] = { 0x01, 0x23, 0x45, 0x67, 0x89, 0xAB };
uint8_t broadcastAddress2[] = { 0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56 };
const int channel = 1;  // Set Wi-Fi channel
String uart_data;
String adb_L;
String adb_R;
String arrayadbId = "array";
String uart_long_data;
String uart_wide_data;
String headlightL;
String headlightR;
String zhustatus;
String zhulong;
String zhuwide;
int uart_wide_int;
int uart_long_int;
int count = 0; // 添加计数器变量

bool writeBleFile(const char *u1, const char *u2) {
  if (SPIFFS.begin()) {
    File file = SPIFFS.open("/ble.txt", "w");

    if (file) {
      String data = String(u1) + "," + String(u2);
      file.print(data);
      file.close();

      return true;  // 写入成功
    } else {
      Serial.println("无法打开 ble.txt 文件进行写入。");
    }
  } else {
    Serial.println("无法启动 SPIFFS 文件系统。");
  }

  return false;  // 写入失败
}
void clrDataToFile_ble(const String &data) {
  // 初始化 SPIFFS
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS 初始化失败");
    return;
  }

  // 打开文件
  file = SPIFFS.open("/ble.txt", FILE_WRITE);
  if (!file) {
    Serial.println("无法打开文件1");
    return;
  }

  // 清空文件内容
  file.close();                                // 关闭文件
  file = SPIFFS.open("/ble.txt", FILE_WRITE);  // 重新以写入模式打开文件

  if (file.size() == 0) {
    Serial.println("ble 文件已成功清空");
  } else {
    Serial.println("ble 文件清空失败");
  }
  // 关闭文件
  file.close();
}
void clrDataToFile(const String &data) {
  // 初始化 SPIFFS
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS 初始化失败");
    return;
  }

  // 打开文件
  file = SPIFFS.open("/low.txt", FILE_WRITE);
  if (!file) {
    Serial.println("无法打开文件1");
    return;
  }

  // 清空文件内容
  file.close();                                // 关闭文件
  file = SPIFFS.open("/low.txt", FILE_WRITE);  // 重新以写入模式打开文件

  if (file.size() == 0) {
    Serial.println("文件已成功清空1");
  } else {
    Serial.println("文件清空失败");
  }
  // 关闭文件
  file.close();
}

// 设置前4个灯珠为绿色，其余为蓝色
void adHigh1() {
  // 设置前4个灯珠为绿色
  for (int i = 0; i < 4; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 255, 0));
  }

  // 设置剩下的灯珠为蓝色
  for (int i = 4; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();
}

// 设置前3个灯珠为绿色，其余为蓝色
void adHigh2() {
  // 设置前3个灯珠为绿色
  for (int i = 0; i < 3; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 255, 0));
  }

  // 设置剩下的灯珠为蓝色
  for (int i = 3; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();
}

// 设置前2个灯珠为绿色，其余为蓝色
void adHigh3() {
  // 设置前2个灯珠为绿色
  for (int i = 0; i < 2; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 255, 0));
  }

  // 设置剩下的灯珠为蓝色
  for (int i = 2; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();
}

// 设置前1个灯珠为绿色，其余为蓝色
void adHigh4() {
  // 设置前1个灯珠为绿色
  pixels.setPixelColor(0, pixels.Color(0, 255, 0));

  // 设置剩下的灯珠为蓝色
  for (int i = 1; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();
}

// 设置所有灯珠为蓝色
void adHigh5() {
  // 设置所有LED为蓝色
  pixels.fill(pixels.Color(0, 0, 255));
  // 显示设置的颜色
  pixels.show();
}
// 实现从绿色到蓝色的逐个灯珠渐变效果
void adHigh() {
  static int currentPixel = 0;
  static int gradientStep = 0;

  // 如果所有灯珠都已处理完毕
  if (currentPixel >= NUMPIXELS) {
    currentPixel = 0;  // 重置为第一个灯珠
    gradientStep = 0;  // 重置渐变步数
  }

  // 检查是否需要进入下一个阶段
  if (gradientStep >= GRADIENT_LENGTH) {
    gradientStep = 0;
    currentPixel++;
  }

  // 逐个灯珠改变颜色
  if (currentPixel < 4) {  // 处理前四个灯珠
    // 计算当前阶段的绿色和蓝色混合值
    int green = 255 - (gradientStep * 255 / GRADIENT_LENGTH);
    int blue = gradientStep * 255 / GRADIENT_LENGTH;

    // 设置颜色
    pixels.setPixelColor(currentPixel, pixels.Color(0, green, blue));
  } else if (currentPixel >= 4 && currentPixel < 8) {  // 处理后四个灯珠
    // 直接设置为蓝色
    pixels.setPixelColor(currentPixel, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();

  // 增加渐变步数
  gradientStep++;
}

// 实现全部灯珠变成蓝色，并有渐变效果
void fullHigh() {
  static int gradientStep = 0;

  // 创建一个渐变效果
  for (int i = 0; i < 256; i += GRADIENT_SPEED) {
    for (int j = 0; j < NUMPIXELS; j++) {
      // 从纯绿到纯蓝渐变
      uint32_t color = pixels.Color(0, 255 - i, i);
      pixels.setPixelColor(j, color);
    }
    pixels.show();
    delay(10);  // 短暂延时以观察渐变效果
  }

  // 重置渐变步数
  gradientStep = 0;
}

// 设置前1个灯珠为绿色，后面蓝色
void fullHigh1() {
  static int gradientStep = 0;

  // 如果已经处理完毕
  if (gradientStep >= GRADIENT_LENGTH) {
    gradientStep = 0;  // 重置渐变步数
  }

  // 逐个灯珠改变颜色
  pixels.setPixelColor(0, pixels.Color(0, 255 - (gradientStep * 255 / GRADIENT_LENGTH), gradientStep * 255 / GRADIENT_LENGTH));

  // 设置剩下的灯珠为蓝色
  for (int i = 1; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();

  // 增加渐变步数
  gradientStep++;
}

// 设置前2个灯珠为绿色，后面蓝色
void fullHigh2() {
  static int gradientStep = 0;

  // 如果已经处理完毕
  if (gradientStep >= GRADIENT_LENGTH) {
    gradientStep = 0;  // 重置渐变步数
  }

  // 逐个灯珠改变颜色
  for (int i = 0; i < 2; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 255 - (gradientStep * 255 / GRADIENT_LENGTH), gradientStep * 255 / GRADIENT_LENGTH));
  }

  // 设置剩下的灯珠为蓝色
  for (int i = 2; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();

  // 增加渐变步数
  gradientStep++;
}

// 设置前3个灯珠为绿色，后面蓝色
void fullHigh3() {
  static int gradientStep = 0;

  // 如果已经处理完毕
  if (gradientStep >= GRADIENT_LENGTH) {
    gradientStep = 0;  // 重置渐变步数
  }

  // 逐个灯珠改变颜色
  for (int i = 0; i < 3; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 255 - (gradientStep * 255 / GRADIENT_LENGTH), gradientStep * 255 / GRADIENT_LENGTH));
  }

  // 设置剩下的灯珠为蓝色
  for (int i = 3; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();

  // 增加渐变步数
  gradientStep++;
}

// 设置前4个灯珠为绿色，后面蓝色
void fullHigh4() {
  static int gradientStep = 0;

  // 如果已经处理完毕
  if (gradientStep >= GRADIENT_LENGTH) {
    gradientStep = 0;  // 重置渐变步数
  }

  // 逐个灯珠改变颜色
  for (int i = 0; i < 4; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 255 - (gradientStep * 255 / GRADIENT_LENGTH), gradientStep * 255 / GRADIENT_LENGTH));
  }

  // 设置剩下的灯珠为蓝色
  for (int i = 4; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  // 显示设置的颜色
  pixels.show();

  // 增加渐变步数
  gradientStep++;
}

void fulllight(int dd) {
  adHigh5();
}

void adblight(int dd) {
  fullHigh4();
}
void errlight() {
  pixels.fill(pixels.Color(255, 0, 0));
  // 显示设置的颜色
  pixels.show();
}