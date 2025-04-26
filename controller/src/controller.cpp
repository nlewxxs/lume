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
static float old_pitch = 0.0;
static float old_roll = 0.0;
static float old_yaw = 0.0;
static float pitch;
static float roll;
static float yaw;
static int ac_x;
static int ac_y;
static int ac_z;
static int gy_x;
static int gy_y;
static int gy_z;
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
    bool initialised = false;

    while (!initialised) { 

        delay(1000);
        Particle.process();
        initialised = true;

        // Attempt MPU9250 initialisation
        std::variant<int, sensors::ErrorCode> init_res;
        init_res = sensors::InitMPU6050();
        //
        if (std::holds_alternative<int>(init_res)) {
            // bueno
        } else {
            Log.error("Failed to initialise MPU!");
            initialised = false; 
            continue;
        }

        std::variant<int, socket::ErrorCode> conn_res; 
        conn_res = socket::ListenForServerConn();

        if (std::holds_alternative<int>(conn_res)) {
            // bueno
            Particle.publish("Controller IP", WiFi.localIP().toString().c_str());
            Log.info("localIP=%s", WiFi.localIP().toString().c_str());
        } else {
            Log.error("Failed to connect to server!");
            initialised = false; 
            continue;
        }

        std::variant<IPAddress, socket::ErrorCode> ip;
        ip = socket::GetServerIP();

        if (std::holds_alternative<IPAddress>(ip)) {
            // bueno
            Particle.publish("Server IP", std::get<IPAddress>(ip).toString().c_str());
            Log.info("Server IP: %s", std::get<IPAddress>(ip).toString().c_str());
        } else {
            Log.error("Failed to obtain server IP!");
            initialised = false; 
            continue;
        }
    }

    Particle.publish("CONTROLLER INITIALISED");
    Log.info("Controller successfully initialised");
}

void loop() {

    // We optimistically assume that nothing can go wrong with flex sensors
    // apart from a physical wiring issue
    sensors::UpdateFlexSensors(&flex0, &flex1, &flex2);

    // Attempt to update the MPU readings
    std::variant<int, sensors::ErrorCode> read_res;
    read_res = sensors::UpdateMPU6050Readings(&pitch, &roll, &yaw, &ac_x, &ac_y, &ac_z, &gy_x, &gy_y, &gy_z);

    // handle errors 
    if (std::holds_alternative<int>(read_res)) {
        // bueno
        std::array<float, 3> imu_deltas = {pitch - old_pitch, roll - old_roll, yaw - old_yaw};
        std::tie(old_pitch, old_roll, old_yaw) = {pitch, roll, yaw};
        std::array<int32_t, 3> flex_readings = {flex0, flex1, flex2};
        socket::SendSensorReadings(imu_deltas, flex_readings);
        // Only attempt print if completely necessary, this slows down the loop
        // a lot and contributes to cloud disconnect 
        // Log.info("pitch = %f, roll = %f, yaw = %f", pitch, roll, yaw);
        Log.info("ac_x = %d, ac_y = %d, ac_z = %d", ac_x, ac_y, ac_z);
        // Log.info("gy_x = %d, gy_y = %d, gy_z = %d", gy_x, gy_y, gy_z);
    } else {
        // Log.error("Failed to read from MPU!");
        // std::variant<int, sensors::ErrorCode> init_res;
        // init_res = sensors::InitMPU6050();
    }

    if (millis() - lastUpdate > 5000) {
        Particle.publish("Ping");
        lastUpdate = millis();
        // Handle background callbacks (i.e. cloud conn)
        Particle.process();
    }

    delay(5);
} 
