#include "ArduinoJson/Document/JsonDocument.hpp"
#include "Particle.h"
#include "socket.hpp"
#include "ArduinoJson.hpp"
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
                                     //
            Log.info("Received JSON: %s", recv_buffer);

            if (false) {
                Log.warn("JSON Parsing failed!");
            } else {
                // Store the server IP if the JSON has been reconstructed correctly
                server_ip = udp.remoteIP();
                // Update all the other params
                // const char* tcp_client_port = json_doc["tcp_client_port"];
            }
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
