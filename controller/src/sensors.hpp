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
    MpuUninitialised
};

// Initialise the sensor
std::variant<int, ErrorCode> InitMPU9250(void);

// Update the flex sensor readings
void UpdateFlexSensors(float* flex0, float* flex1, float* flex2);

// Update the IMU readings
std::variant<int, ErrorCode> UpdateMPU9250Readings(float* pitch, float* roll, float* yaw);

} /* namespace sensors */

#endif /* SENSORS_H_ */
