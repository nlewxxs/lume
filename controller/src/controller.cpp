/* 
 * Project Lume
 * Author: Nik Lewis
 * Date: 
 * For comprehensive documentation and examples, please visit:
 * https://docs.particle.io/firmware/best-practices/firmware-template/
 */

#include "Particle.h"
#include "sensors.hpp"
#include "socket.hpp"
#include "filters.hpp"
#include "spark_wiring_ipaddress.h"
#include "wlan_hal.h"
#include <array>
#include <climits>
#include <cstring>
#include "neopixel.h"
#include <variant>

// Let Device OS manage the connection to the Particle Cloud
SYSTEM_MODE(AUTOMATIC);
// Run the application and system concurrently in separate threads
SYSTEM_THREAD(ENABLED);
// Show system, cloud connectivity, and application logs over USB
// View logs with CLI using 'particle serial monitor --follow'
SerialLogHandler logHandler(LOG_LEVEL_INFO);
// Select the external antenna
STARTUP(WiFi.selectAntenna(ANT_EXTERNAL));

#define SDA_PIN D1
#define SCL_PIN D0

#if (PLATFORM_ID == 32)
// MOSI pin MO
#define PIXEL_PIN SPI
// MOSI pin D2
// #define PIXEL_PIN SPI1
#else // #if (PLATFORM_ID == 32)
#define PIXEL_PIN S0
#endif
#define PIXEL_COUNT 12
#define PIXEL_TYPE WS2812B

// Define the neopixels
Adafruit_NeoPixel strip(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);

namespace {
// Keep track of the pitch, roll and yaw as globals in an anonymous namespace
static float pitch;
static float roll;
static float yaw;

static int acc_x;
static int acc_y;
static int acc_z;
static int gyro_x;
static int gyro_y;
static int gyro_z;

static int32_t flex0; // thumb
static int32_t flex1; // index
static int32_t flex2; // ring
static unsigned long lastUpdate = 0;

// Define colours
static constexpr std::array<uint8_t, 3> purple {128, 0, 128};
static constexpr std::array<uint8_t, 3> cyan {0, 128, 128};
}

// Prototypes for local build, ok to leave in for Build IDE
uint32_t Wheel(byte WheelPos);

void loading(const std::array<uint8_t, 3> &colour) {
    uint16_t i;
    for(i=0; i<strip.numPixels(); i++) {
        strip.setPixelColor(i, colour[0], colour[1], colour[2]);
        if (i >= 4) strip.setPixelColor(i - 4, 0, 0, 0);
        else if (i == 0) strip.setPixelColor(strip.numPixels() - 4, 0, 0, 0);
        else if (i == 1) strip.setPixelColor(strip.numPixels() - 3, 0, 0, 0);
        else if (i == 2) strip.setPixelColor(strip.numPixels() - 2, 0, 0, 0);
        else if (i == 3) strip.setPixelColor(strip.numPixels() - 1, 0, 0, 0);
        strip.show();
        delay(100);
    }
    delay(20);
}

void setup() {

    Serial.begin(9600);

    strip.begin();
    strip.setBrightness(96);
    strip.show(); // Initialize all pixels to 'off'

    // Wait for cloud connection
    while (!Particle.connected()) {
        Log.info("Attempting to connect to cloud...");
        Particle.process();
        delay(500);
    }

    socket::InitSockets();

    // Attempt MPU9250 initialisation
    std::variant<int, sensors::ErrorCode> init_res;
    init_res = sensors::InitMPU6050();

    while (!std::holds_alternative<int>(init_res)) {
        Log.error("Failed to initialise MPU!");
        init_res = sensors::InitMPU6050();
    }

    std::variant<int, socket::ErrorCode> conn_res; 
    conn_res = socket::ListenForServerConn();

    while (!std::holds_alternative<int>(conn_res)) {
        loading(purple);
        Log.error("Failed to connect to server!");
        conn_res = socket::ListenForServerConn();
        delay(500);
    }

    Particle.publish("Controller IP", WiFi.localIP().toString().c_str());
    Log.info("localIP=%s", WiFi.localIP().toString().c_str());

    std::variant<IPAddress, socket::ErrorCode> ip;
    ip = socket::GetServerIP();

    while (!std::holds_alternative<IPAddress>(ip)) {
        // bueno
        loading(purple);
        Log.error("Failed to obtain server IP!");
        ip = socket::GetServerIP();
    }

    Particle.publish("Server IP", std::get<IPAddress>(ip).toString().c_str());
    Log.info("Server IP: %s", std::get<IPAddress>(ip).toString().c_str());

    Particle.publish("CONTROLLER INITIALISED");
    Log.info("Controller successfully initialised");
}

void loop() {

    loading(cyan);
    // We optimistically assume that nothing can go wrong with flex sensors
    // apart from a physical wiring issue
    sensors::UpdateFlexSensors(&flex0, &flex1, &flex2);
    filters::PushNewFlexReadings(flex0, flex1, flex2);

    // Attempt to update the MPU readings
    std::variant<int, sensors::ErrorCode> read_res;
    read_res = sensors::UpdateMPU6050Readings(
        &pitch, &roll, &yaw, &acc_x, &acc_y, &acc_z, &gyro_x, &gyro_y, &gyro_z);

    delay(10);

    // handle errors 
    if (std::holds_alternative<int>(read_res)) {
        // bueno 

        // convert gyro and acc to Vector3 (floats x,y,z)
        filters::Vector3 acc = {static_cast<float>(acc_x), static_cast<float>(acc_y),
                       static_cast<float>(acc_z)};
        filters::Vector3 gyro = {static_cast<float>(gyro_x), static_cast<float>(gyro_y),
                       static_cast<float>(gyro_z)};

        filters::PushNewAccelReadings(acc);
        filters::PushNewGyroReadings(gyro);
        filters::PushNewYprReadings(pitch, roll, yaw);
        socket::SendSensorReadings(*filters::GetDataPacket());
        // filters::DataPacket* packet_ptr = filters::GetDataPacket();
        // Only attempt print if completely necessary, this slows down the loop
        // a lot and contributes to cloud disconnect 
        // Log.info("pitch = %f, roll = %f, yaw = %f", pitch, roll, yaw);
        // Log.info("%f | %f | %f", packet_ptr->pitch, packet_ptr->roll, packet_ptr->yaw);
        // Log.info("%d | %d | %d", packet_ptr->flex0, packet_ptr->flex1, packet_ptr->flex2);
    } else {
        Log.error("Failed to read from MPU!");
    }

    if (millis() - lastUpdate > 5000) {
        Particle.publish("Ping");
        lastUpdate = millis();
        // Handle background callbacks (i.e. cloud conn)
        Particle.process();
    }
}


// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
   return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
   WheelPos -= 170;
   return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}
