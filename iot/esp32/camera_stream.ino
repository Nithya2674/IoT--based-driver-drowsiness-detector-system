/*
 * ESP32-CAM Drowsiness Detection Camera Stream
 * ==============================================
 * Arduino sketch for ESP32-CAM module.
 * Captures camera frames and streams via MJPEG over WiFi.
 * Can also send frames to the backend server via HTTP POST.
 *
 * Hardware: AI-Thinker ESP32-CAM
 * Board:    ESP32 Wrover Module
 *
 * Connections:
 *   - Built-in OV2640 Camera (No external wiring needed)
 *   - Built-in Flash LED on GPIO 4
 *   - External Buzzer: GPIO 12 (optional)
 *   - External LED:    GPIO 13 (optional)
 *
 * Setup in Arduino IDE:
 *   1. Install ESP32 board support
 *   2. Select Board: "AI Thinker ESP32-CAM"
 *   3. Set Upload Speed: 115200
 *   4. Set Partition Scheme: "Huge APP (3MB No OTA)"
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_http_server.h"

// ═══════════════════════════════════════════════════════════════
//  CONFIGURATION — CHANGE THESE VALUES
// ═══════════════════════════════════════════════════════════════

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Backend server URL (Flask API)
const char* serverUrl = "http://YOUR_SERVER_IP:5000/api/events";

// Device credentials
const char* deviceId = "ESP32-CAM-001";
const char* deviceApiKey = "your-device-api-key";

// Alert pin (external buzzer/LED)
#define BUZZER_PIN 12
#define LED_PIN 13
#define FLASH_PIN 4

// Stream configuration
#define FRAME_INTERVAL_MS 100  // 10 FPS for streaming
#define UPLOAD_INTERVAL_MS 5000 // Upload frame every 5 seconds

// ═══════════════════════════════════════════════════════════════
//  AI-THINKER ESP32-CAM PIN DEFINITIONS
// ═══════════════════════════════════════════════════════════════

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ═══════════════════════════════════════════════════════════════
//  GLOBAL VARIABLES
// ═══════════════════════════════════════════════════════════════

httpd_handle_t stream_httpd = NULL;
unsigned long lastUploadTime = 0;
bool wifiConnected = false;

// ═══════════════════════════════════════════════════════════════
//  CAMERA INITIALIZATION
// ═══════════════════════════════════════════════════════════════

void initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    // Optimize for streaming
    if (psramFound()) {
        config.frame_size = FRAMESIZE_VGA;    // 640x480
        config.jpeg_quality = 12;
        config.fb_count = 2;
        Serial.println("[CAM] PSRAM found — using VGA resolution");
    } else {
        config.frame_size = FRAMESIZE_QVGA;   // 320x240
        config.jpeg_quality = 15;
        config.fb_count = 1;
        Serial.println("[CAM] No PSRAM — using QVGA resolution");
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[CAM] Init failed: 0x%x\n", err);
        ESP.restart();
    }

    // Camera settings
    sensor_t *s = esp_camera_sensor_get();
    s->set_brightness(s, 1);
    s->set_contrast(s, 1);
    s->set_saturation(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_aec2(s, 1);
    s->set_ae_level(s, 0);
    s->set_gainceiling(s, (gainceiling_t)6);

    Serial.println("[CAM] Camera initialized successfully");
}

// ═══════════════════════════════════════════════════════════════
//  WIFI CONNECTION
// ═══════════════════════════════════════════════════════════════

void connectWiFi() {
    Serial.printf("[WiFi] Connecting to %s", ssid);
    WiFi.begin(ssid, password);
    WiFi.setSleep(false);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        Serial.println("\n[WiFi] Connected!");
        Serial.printf("[WiFi] IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WiFi] Stream URL: http://%s:81/stream\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[WiFi] Connection failed!");
        wifiConnected = false;
    }
}

// ═══════════════════════════════════════════════════════════════
//  MJPEG STREAM SERVER
// ═══════════════════════════════════════════════════════════════

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    char part_buf[64];

    res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
    if (res != ESP_OK) return res;

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("[STREAM] Frame capture failed");
            res = ESP_FAIL;
            break;
        }

        size_t hlen = snprintf(part_buf, 64, STREAM_PART, fb->len);
        res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
        if (res == ESP_OK) res = httpd_resp_send_chunk(req, part_buf, hlen);
        if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);

        esp_camera_fb_return(fb);

        if (res != ESP_OK) break;

        delay(FRAME_INTERVAL_MS);
    }

    return res;
}

void startStreamServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 81;

    httpd_uri_t stream_uri = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = stream_handler,
        .user_ctx = NULL
    };

    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        Serial.println("[STREAM] Server started on port 81");
    }
}

// ═══════════════════════════════════════════════════════════════
//  ALERT FUNCTIONS
// ═══════════════════════════════════════════════════════════════

void triggerBuzzer(int durationMs) {
    digitalWrite(BUZZER_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH);
    delay(durationMs);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
}

void blinkLed(int count, int delayMs) {
    for (int i = 0; i < count; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(delayMs);
        digitalWrite(LED_PIN, LOW);
        delay(delayMs);
    }
}

// ═══════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════

void setup() {
    Serial.begin(115200);
    Serial.println("\n=========================================");
    Serial.println("  DrowsiGuard ESP32-CAM Module");
    Serial.println("=========================================");

    // Configure alert pins
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    pinMode(FLASH_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    digitalWrite(FLASH_PIN, LOW);

    // Startup indication
    blinkLed(3, 200);

    // Initialize camera
    initCamera();

    // Connect WiFi
    connectWiFi();

    // Start stream server
    if (wifiConnected) {
        startStreamServer();
    }

    Serial.println("\n[SYSTEM] ESP32-CAM ready!");
    Serial.println("=========================================\n");
}

// ═══════════════════════════════════════════════════════════════
//  LOOP
// ═══════════════════════════════════════════════════════════════

void loop() {
    // Reconnect WiFi if disconnected
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[WiFi] Reconnecting...");
        connectWiFi();
    }

    // Periodic status
    static unsigned long lastStatusTime = 0;
    if (millis() - lastStatusTime > 60000) { // Every 60 seconds
        Serial.printf("[STATUS] Uptime: %lu min | WiFi: %s | IP: %s\n",
            millis() / 60000,
            WiFi.status() == WL_CONNECTED ? "OK" : "FAIL",
            WiFi.localIP().toString().c_str());
        lastStatusTime = millis();
    }

    delay(100);
}
