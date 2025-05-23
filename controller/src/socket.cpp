#include <iomanip>
#include <sstream>
#include <string>

#include "Particle.h"
#include "socket.hpp"
#include "filters.hpp"

namespace {
UDP udp;
// Ports on which config will be broadcast to
static constexpr unsigned int kUdpPort = 8888;
static constexpr std::size_t kPayloadSize = 49; // size of sensor data payload in bytes
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
SendSensorReadings(const filters::DataPacket& data) {

    // If the server IP has not been initialised, return error code
    if (!server_ip.has_value()) return ErrorCode::SendingBeforeInit;

    uint8_t msg[49]; // final message buffer

    // copy in all the floats, big-endian 
    memcpy(&msg[0], &data.pitch, sizeof(data.pitch));
    memcpy(&msg[4], &data.roll, sizeof(data.roll));
    memcpy(&msg[8], &data.yaw, sizeof(data.yaw));
    memcpy(&msg[12], &data.d_pitch, sizeof(data.d_pitch));
    memcpy(&msg[16], &data.d_roll, sizeof(data.d_roll));
    memcpy(&msg[20], &data.d_yaw, sizeof(data.d_yaw));
    memcpy(&msg[24], &data.acc_x, sizeof(data.acc_x));
    memcpy(&msg[28], &data.acc_y, sizeof(data.acc_y));
    memcpy(&msg[32], &data.acc_z, sizeof(data.acc_z));
    memcpy(&msg[36], &data.gy_x, sizeof(data.gy_x));
    memcpy(&msg[40], &data.gy_y, sizeof(data.gy_y));
    memcpy(&msg[44], &data.gy_z, sizeof(data.gy_z));

    /* bitpack the booleans for the flex sensors, in big-endian form. i.e. flex
     * sensor readings for 0, 1, and 2 will be packed:
     *
     * [flex0] [flex1] [flex2] 0 0 0 0 0 */

    uint8_t flex_readings = 0x0;
    flex_readings |= (data.flex0 ? 0b00000001 : 0b00000000);
    flex_readings <<= 1;
    flex_readings |= (data.flex1 ? 0b00000001 : 0b00000000);
    flex_readings <<= 1;
    flex_readings |= (data.flex2 ? 0b00000001 : 0b00000000);
    flex_readings <<= 5;

    msg[48] = flex_readings;

    // send off packet
    udp.beginPacket(server_ip.value(), kUdpPort);
    udp.write(msg, sizeof(msg));
    udp.endPacket();

    return SUCCESS;
}

} /* namespace socket */
