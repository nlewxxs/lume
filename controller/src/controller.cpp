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
#include <climits>
#include <cstring>
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
}

void setup() {

    Serial.begin(9600);

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
        Log.error("Failed to obtain server IP!");
        ip = socket::GetServerIP();
    }

    Particle.publish("Server IP", std::get<IPAddress>(ip).toString().c_str());
    Log.info("Server IP: %s", std::get<IPAddress>(ip).toString().c_str());

    Particle.publish("CONTROLLER INITIALISED");
    Log.info("Controller successfully initialised");
}

void loop() {

    // We optimistically assume that nothing can go wrong with flex sensors
    // apart from a physical wiring issue
    sensors::UpdateFlexSensors(&flex0, &flex1, &flex2);
    filters::PushNewFlexReadings(flex0, flex1, flex2);

    // Attempt to update the MPU readings
    std::variant<int, sensors::ErrorCode> read_res;
    read_res = sensors::UpdateMPU6050Readings(
        &pitch, &roll, &yaw, &acc_x, &acc_y, &acc_z, &gyro_x, &gyro_y, &gyro_z);

    delay(5);

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
        // Only attempt print if completely necessary, this slows down the loop
        // a lot and contributes to cloud disconnect 
        // Log.info("pitch = %f, roll = %f, yaw = %f", pitch, roll, yaw);
    } else {
        Log.error("Failed to read from MPU!");
    }

    if (millis() - lastUpdate > 5000) {
        Particle.publish("Ping");
        lastUpdate = millis();
        // Handle background callbacks (i.e. cloud conn)
        Particle.process();
    }

    delay(5);
} 
