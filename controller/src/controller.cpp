/* 
 * Project myProject
 * Author: Your Name
 * Date: 
 * For comprehensive documentation and examples, please visit:
 * https://docs.particle.io/firmware/best-practices/firmware-template/
 */

#include "Particle.h"
#include "sensors.hpp"
#include "socket.hpp"
#include "spark_wiring_ipaddress.h"
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

namespace {
// Keep track of the pitch, roll and yaw as globals in an anonymous namespace
static float pitch;
static float roll;
static float yaw;
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
        init_res = sensors::InitMPU9250();
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

    std::variant<int, sensors::ErrorCode> read_res;
    read_res = sensors::UpdateMPU9250Readings(&pitch, &roll, &yaw);
    if (std::holds_alternative<int>(read_res)) {
        // bueno
        Log.info("pitch = %f, roll = %f, yaw = %f", pitch, roll, yaw);
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
