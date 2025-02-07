#ifndef SOCKET_H_
#define SOCKET_H_

#include "Particle.h"
#include <variant>


namespace socket {

enum class ErrorCode {
    NoServerConn 
};

std::variant<int, ErrorCode> InitServerConn();

} /* namespace socket */
#endif /* SOCKET_H_ */
