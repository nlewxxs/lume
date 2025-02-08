#ifndef SOCKET_H_
#define SOCKET_H_

#include "Particle.h"
#include "spark_wiring_ipaddress.h"
#include <variant>


namespace socket {

enum class ErrorCode {
    NoServerConn 
};

void InitSockets();

std::variant<int, ErrorCode> ListenForServerConn();

std::variant<IPAddress, ErrorCode> GetServerIP();

} /* namespace socket */
#endif /* SOCKET_H_ */
