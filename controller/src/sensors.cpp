#include "MPU6050_6Axis_MotionApps20.h"
#include "Particle.h"
#include "helper_3dmath.h"
#include "spark_wiring.h"
#include "spark_wiring_error.h"
#include <filesystem>
#include "sensors.hpp"

namespace {
byte MPU_EXPECTED_ADDRESS = 0x70;
byte AK_EXPECTED_ADDRESS = 0x48;
MPU6050 mpu; // MPU9250 object definition
byte address = 0x00;
bool initialised = false;

uint16_t fifoCount;
uint8_t fifoBuffer[64];

Quaternion q;
VectorFloat gravity;
VectorInt16 gyro;
VectorInt16 accel;
float ypr[3];

static constexpr int SUCCESS = 0;
// Define flex sensors
static constexpr int FLEX0PIN = A0;
static constexpr int FLEX1PIN = A2; // yes I soldered them wrong
static constexpr int FLEX2PIN = A1;
}

namespace sensors {

std::variant<int, ErrorCode> InitMPU6050() {

    Wire.begin();
    Wire.setClock(400000);

    Log.info("Entered MPU initialisation...");
    mpu.initialize();
    
    initialised = mpu.testConnection();

    // Break early if MPU cannot be found at the right address
    if (!initialised) return ErrorCode::MpuUninitialised;
    Log.info("MPU initialised");
    
    initialised = (mpu.dmpInitialize() == 0);
    Log.info("DMP initialised");

    // Break early if DMP cannot be initialised
    if (!initialised) return ErrorCode::MpuDMPUninitialised;

    mpu.setXGyroOffset(220);
    mpu.setYGyroOffset(76);
    mpu.setZGyroOffset(-85);
    mpu.setZAccelOffset(1788);

    // Calibration Time: generate offsets and calibrate our MPU6050
    mpu.CalibrateAccel(6);
    mpu.CalibrateGyro(6);

    // Enable DMP
    mpu.setDMPEnabled(true);
    
    return SUCCESS;
}

void UpdateFlexSensors(int32_t* flex0, int32_t* flex1, int32_t* flex2) {
    *flex0 = analogRead(FLEX0PIN);

    int32_t temp = analogRead(FLEX1PIN);
    if (temp > 1000) *flex1 = temp;

    *flex2 = analogRead(FLEX2PIN);
}

std::variant<int, ErrorCode>
UpdateMPU6050Readings(float *pitch, float *roll, float *yaw, int *ac_x,
                      int *ac_y, int *ac_z, int *gy_x, int *gy_y, int *gy_z) {

  // Break early if uninitialised
  if (!initialised)
    return ErrorCode::MpuUninitialised;

  if (mpu.dmpGetCurrentFIFOPacket(fifoBuffer)) {
    mpu.dmpGetQuaternion(&q, fifoBuffer);
    mpu.dmpGetGravity(&gravity, &q);
    mpu.dmpGetYawPitchRoll(ypr, &q, &gravity);
    mpu.dmpGetGyro(&gyro, fifoBuffer);
    mpu.dmpGetAccel(&accel, fifoBuffer);
  } else {
    Log.error("Couldn't get DMP packet!!!!");
    return ErrorCode::ReadError;
  }

  *pitch = ypr[1];
  *roll = ypr[2];
  *yaw = ypr[0];

  *ac_x = accel.x;
  *ac_y = accel.y;
  *ac_z = accel.z;

  *gy_x = gyro.x;
  *gy_y = gyro.y;
  *gy_z = gyro.z;

  return SUCCESS;
}

} /* namespace socket */ 
