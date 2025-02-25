#ifndef SOCKET_H_
#define SOCKET_H_

#include "Particle.h"
#include "spark_wiring_ipaddress.h"
#include <variant>


namespace socket {

enum class ErrorCode {
    NoServerConn,
    SendingBeforeInit,
};

void InitSockets();

std::variant<int, ErrorCode> ListenForServerConn();

std::variant<IPAddress, ErrorCode> GetServerIP();

std::variant<int, ErrorCode> SendSensorReadings(std::array<float, 3>& imu_readings, std::array<int32_t, 3>& flex_readings);

} /* namespace socket */
#endif /* SOCKET_H_ */
