/* 
 * Project myProject
 * Author: Your Name
 * Date: 
 * For comprehensive documentation and examples, please visit:
 * https://docs.particle.io/firmware/best-practices/firmware-template/
 */

// Include Particle Device OS APIs
#include "Particle.h"

// Let Device OS manage the connection to the Particle Cloud
SYSTEM_MODE(AUTOMATIC);

// Run the application and system concurrently in separate threads
SYSTEM_THREAD(ENABLED);

UDP Udp;
unsigned int rx_port = 8888;
unsigned int tx_port = 8889;

// Show system, cloud connectivity, and application logs over USB
// View logs with CLI using 'particle serial monitor --follow'
SerialLogHandler logHandler(LOG_LEVEL_INFO);

// setup() runs once, when the device is first turned on
void setup() {
    // Put initialization like pinMode and begin functions here
    Serial.begin(9600);
    Udp.begin(rx_port);
}

// loop() runs over and over again, as quickly as it can execute.
void loop() {
    // The core of your code will likely live here.
    // Example: Publish event to cloud every 10 seconds. Uncomment the next 3 lines to try it!
    // Particle.publish(std::to_string(analogRead(A1)).c_str());
    // Log.info("localIP=%s", WiFi.localIP().toString().c_str());
    delay(1000); // milliseconds and blocking - see docs for more info!

    if (Udp.parsePacket() > 0) {
        Particle.publish("Received packet!!");
        char c = Udp.read();

        while (Udp.available()) Udp.read();

        IPAddress ip = Udp.remoteIP(); 

        Udp.beginPacket(ip, tx_port);
        Udp.write(c);
        Udp.endPacket();
        Particle.publish("echoed packet!!");
    }
}
