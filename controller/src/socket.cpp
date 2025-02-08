#include "Particle.h"
#include "socket.hpp"
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

} /* namespace socket */
