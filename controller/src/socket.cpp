#include "Particle.h"
#include "socket.hpp"
#include <iomanip>
#include <sstream>
#include <string>

namespace {
UDP udp;
// Ports on which config will be broadcast to
static constexpr unsigned int kUdpPort = 8888;
static constexpr unsigned int kTcpRxPort = 8889;
static constexpr unsigned int kTcpTxPort = 8890;
// Maximum number of attempts to listen to config for
static constexpr int kMaxAttempts = 100;
static char recv_buffer[128];
static std::optional<IPAddress> server_ip;
static constexpr int SUCCESS = 0;
static char readings_buffer[100];
}

namespace socket {

void InitSockets() {
    udp.begin(kUdpPort);
}

std::variant<int, ErrorCode> ListenForServerConn() {

    int attempts = 0;
    while (!server_ip && attempts < kMaxAttempts) {
        int packet_size = udp.parsePacket();
        if (packet_size > 0) {
            Log.info("received server greeting");
            break;
        }
        attempts++;
    }
   
    // Handle error if no config received
    if (attempts >= kMaxAttempts) {
        Log.info("Exhausted connection attempts");
        server_ip = std::nullopt;  // reset server ip
        return ErrorCode::NoServerConn;  
    }

    // Otherwise set the server IP and return success
    server_ip = udp.remoteIP();
    return SUCCESS;
}

std::variant<IPAddress, ErrorCode> GetServerIP() {
    if (server_ip.has_value()) return server_ip.value();
    else return ErrorCode::NoServerConn;
}

std::variant<int, ErrorCode>
SendSensorReadings(std::array<float, 3> &imu_readings,
                   std::array<int32_t, 3> &flex_readings) {

    // If the server IP has not been initialised, return error code
    if (!server_ip.has_value()) return ErrorCode::SendingBeforeInit;

    // Convert floats to a string
    uint8_t buffer[24];

    // Copy in the IMU readings
    for (int i = 0; i < 3; i++) {
        // Convert float to 4 bytes in network byte order (big-endian)
        uint32_t floatBits;
        memcpy(&floatBits, &imu_readings[i], 4);
        // Copy the bytes to the buffer
        memcpy(&buffer[i * 4], &floatBits, 4);
    }

    // Copy in the Flex sensor readings
    for (int i = 0; i < 3; i++) {
        uint32_t intBits;
        memcpy(&intBits, &flex_readings[i], 4);
        // Copy the bytes to the buffer
        memcpy(&buffer[(i + 3) * 4], &intBits, 4);
    }

    udp.beginPacket(server_ip.value(), kUdpPort);
    udp.write(buffer, sizeof(buffer));
    udp.endPacket();

    return SUCCESS;
}

} /* namespace socket */
