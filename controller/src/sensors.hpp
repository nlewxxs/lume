#ifndef SENSORS_H_
#define SENSORS_H_

#include "Particle.h"
#include "system_mode.h"
#include <climits>
#include <cstring>
#include <variant>

#define AHRS true  // enable filtering and fusion. 

namespace sensors {

enum class ErrorCode {
    MpuNotFound,
    ReadError,
    MpuUninitialised,
    MpuDMPUninitialised,
    AkNotFound,
};

// Initialise the mpu
std::variant<int, ErrorCode> InitMPU6050(void);

// Update the flex sensor readings
void UpdateFlexSensors(int32_t* flex0, int32_t* flex1, int32_t* flex2);

// Update the IMU readings
std::variant<int, ErrorCode> UpdateMPU6050Readings(float *pitch, float *roll, float *yaw, int *ac_x,
                      int *ac_y, int *ac_z, int *gy_x, int *gy_y, int *gy_z);

} /* namespace sensors */

#endif /* SENSORS_H_ */
