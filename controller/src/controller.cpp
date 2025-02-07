/* 
 * Project myProject
 * Author: Your Name
 * Date: 
 * For comprehensive documentation and examples, please visit:
 * https://docs.particle.io/firmware/best-practices/firmware-template/
 */

#include "Particle.h"
#include "sensors.h"
#include <climits>
#include <cstring>
#include <variant>

// Let Device OS manage the connection to the Particle Cloud
SYSTEM_MODE(AUTOMATIC);

// Run the application and system concurrently in separate threads
SYSTEM_THREAD(ENABLED);

// UDP Udp;
// unsigned int rx_port = 8888;
// unsigned int tx_port = 8889;

static float pitch;
static float roll;
static float yaw;

// Show system, cloud connectivity, and application logs over USB
// View logs with CLI using 'particle serial monitor --follow'
SerialLogHandler logHandler(LOG_LEVEL_INFO);

void setup() {

    Serial.begin(9600);
    Wire.begin();
    // Udp.begin(rx_port);

    // Attempt MPU9250 initialisation
    std::variant<int, sensors::ErrorCode> init_res;
    init_res = sensors::InitMPU9250();
    
    if (std::holds_alternative<int>(init_res)) {
        // bueno
    } else {
        Log.error("Failed to initialise MPU!");
    }
}

void loop() {
    // The core of your code will likely live here.
    // Example: Publish event to cloud every 10 seconds. Uncomment the next 3 lines to try it!
    // Particle.publish(std::to_string(analogRead(A1)).c_str()); 
    // Log.info("localIP=%s", WiFi.localIP().toString().c_str());
    
    std::variant<int, sensors::ErrorCode> read_res;
    read_res = sensors::UpdateMPU9250Readings(&pitch, &roll, &yaw);

    if (std::holds_alternative<int>(read_res)) {
        // bueno
        Log.info("pitch = %f, roll = %f, yaw = %f", pitch, roll, yaw);
    } else {
        Log.error("Failed to read from MPU!");
    }
} 
