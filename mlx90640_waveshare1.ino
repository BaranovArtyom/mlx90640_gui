#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <Adafruit_MLX90640.h>

// ==== Настройки Wi-Fi ====
const char* ssid     = "yyyyyyyyyy";
const char* password = "xxxxxxxxxxx";

// ==== UDP ====
WiFiUDP udp;
IPAddress remoteIP(192, 168, 1, 97);  // IP компьютера/Jetson для получения
const int remotePort = 12345;        // Порт приёма на клиенте

// ==== MLX90640 ====
Adafruit_MLX90640 mlx;
float frame[32 * 24]; // 768 точек

void setup() {
  Serial.begin(115200);
  Wire.begin(); // SDA/SCL по умолчанию
  Wire.setClock(400000); // 400kHz I2C для стабильности

  // Подключение к Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected, IP: " + WiFi.localIP().toString());

  // Запуск UDP
  udp.begin(remotePort);

  // Инициализация MLX90640
  if (!mlx.begin(0x33)) {
    Serial.println("MLX90640 not found!");
    while (1);
  }

  mlx.setMode(MLX90640_INTERLEAVED);          // Интерливинг — по умолчанию (MLX90640_CHESS ?)
  mlx.setResolution(MLX90640_ADC_16BIT);      // Лучше качество (MLX90640_ADC_18BIT ?)
  mlx.setRefreshRate(MLX90640_8_HZ);          // Умеренная частота для стабильности (MLX90640_4_HZ ?)
}

void loop() {
  // Получаем кадр
  if (mlx.getFrame(frame) != 0) {
    Serial.println("Frame read error!");
    return;
  }

  // Отправим по 96 значений за раз (всего 768 точек => 8 пакетов)
  for (int i = 0; i < 768; i += 96) {
    String packet = "";
    for (int j = 0; j < 96; j++) {
      packet += String(frame[i + j], 2); // 2 знака после запятой
      if (j < 95) packet += ",";         // запятые между числами
    }

    // Отправка по UDP
    udp.beginPacket(remoteIP, remotePort);
    udp.print(packet);
    udp.endPacket();

    delay(3); // короткая пауза между пакетами
  }

  delay(50); // ~20 FPS макс. (8Hz MLX = 8 кадр/с)
}
