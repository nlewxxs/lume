#ifndef SENSORS_H_
#define SENSORS_H_

#include "Particle.h"
#include "MPU9250.h"
#include "quaternionFilters.h"
#include "system_mode.h"
#include <climits>
#include <cstring>
#include <variant>

#define AHRS true  // enable filtering and fusion. 

namespace sensors {

enum class ErrorCode {
    MpuNotFound,
    MpuUninitialised,
    AkNotFound,
};

// Initialise the mpu
std::variant<int, ErrorCode> InitMPU9250(void);

// Initialise the magnetometer
std::variant<int, ErrorCode> InitAK8963(void);

// Update the flex sensor readings
void UpdateFlexSensors(int32_t* flex0, int32_t* flex1, int32_t* flex2);

// Update the IMU readings
std::variant<int, ErrorCode> UpdateMPU9250Readings(float* pitch, float* roll, float* yaw);

} /* namespace sensors */

#endif /* SENSORS_H_ */
