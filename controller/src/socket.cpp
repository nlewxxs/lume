#include "ArduinoJson-v7.3.0.h"
#include "Particle.h"
#include "socket.hpp"
#include "ArduinoJson.h"
#include <string>

namespace {
static UDP udp;
// Port on which config will be broadcast to
static constexpr unsigned int kUdpPort = 8888;
static constexpr unsigned int kTxPort = 8889;
// Maximum number of attempts to listen to config for
static constexpr int kMaxAttempts = 10;
static char recv_buffer[128];
static std::optional<IPAddress> server_ip;
static constexpr int SUCCESS = 0;
}

namespace socket {

std::variant<int, ErrorCode> ListenForServerConn() {
    udp.begin(kUdpPort);

    int attempts = 0;
    while (!server_ip && attempts < kMaxAttempts) {
        int packet_size = udp.parsePacket();
        if (packet_size) {
            int len = udp.read(recv_buffer, sizeof(recv_buffer) - 1);
            recv_buffer[len] = '\0'; // null termination
        }
        attempts++;
    }
   
    // Handle error if no config received
    if (attempts >= kMaxAttempts) {
        server_ip = std::nullopt;  // reset server ip
        return ErrorCode::NoServerConn;  
    }

    return SUCCESS;
}
} /* namespace socket */
