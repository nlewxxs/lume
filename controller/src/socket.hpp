#ifndef SOCKET_H_
#define SOCKET_H_

#include "Particle.h"
#include "filters.hpp"
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

std::variant<int, ErrorCode> SendSensorReadings(const filters::DataPacket& data);

void SendESTOP();

void SetManualMode();

void SetGestureMode();

void SendHardwareFailure();

} /* namespace socket */

#endif /* SOCKET_H_ */
