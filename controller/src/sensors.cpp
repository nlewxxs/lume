#include "MPU9250.h"
#include "Particle.h"
#include "spark_wiring.h"
#include "sensors.hpp"

namespace {
byte MPU_EXPECTED_ADDRESS = 0x70;
byte AK_EXPECTED_ADDRESS = 0x48;
MPU9250 mpu; // MPU9250 object definition
byte address = 0x00;
bool initialised = false;
static constexpr int SUCCESS = 0;
// Define flex sensors
static constexpr int FLEX0PIN = A0;
static constexpr int FLEX1PIN = A2; // yes I soldered them wrong
static constexpr int FLEX2PIN = A1;
}

namespace sensors {

std::variant<int, ErrorCode> InitMPU9250() {

    Wire.begin();
    initialised = false;

    // Get the address of the MPU9250 and make sure it is as expected
    address = mpu.readByte(MPU9250_ADDRESS, WHO_AM_I_MPU9250);
    Log.info("Found MPU at %x", address);
    
    // Break early if MPU cannot be found at the right address
    if (address != MPU_EXPECTED_ADDRESS) return ErrorCode::MpuNotFound;

    else {

        // Start by performing self test and reporting values
        mpu.MPU9250SelfTest(mpu.SelfTest);

        // Calibrate gyro and accelerometers, load biases in bias registers
        mpu.calibrateMPU9250(mpu.gyroBias, mpu.accelBias);
        mpu.initMPU9250();
        initialised = true;
    }

    return SUCCESS;
}


std::variant<int, ErrorCode> InitAK8963() {

    Wire.begin();
    initialised = false;

    mpu.writeByte(MPU9250_ADDRESS, INT_PIN_CFG, 0x22);
    mpu.writeByte(MPU9250_ADDRESS, INT_ENABLE, 0x01);
    delay(100);

    // Get the address of the MPU9250 and make sure it is as expected
    address = mpu.readByte(AK8963_ADDRESS, WHO_AM_I_AK8963);
    Log.info("Found AK8963 at %x", address);
    
    // Break early if MPU cannot be found at the right address
    if (address != AK_EXPECTED_ADDRESS) return ErrorCode::AkNotFound;

    else {
        // Calibrate magnetometer
        mpu.initAK8963(mpu.magCalibration);
        initialised = true;
    }

    return SUCCESS;
}


void UpdateFlexSensors(int32_t* flex0, int32_t* flex1, int32_t* flex2) {
    *flex0 = analogRead(FLEX0PIN);
    *flex1 = analogRead(FLEX1PIN);
    *flex2 = analogRead(FLEX2PIN);
}


std::variant<int, ErrorCode> UpdateMPU9250Readings(float* pitch, float* roll, float* yaw) {

    // Break early if uninitialised
    if (!initialised) return ErrorCode::MpuUninitialised;

    mpu.readAccelData(mpu.accelCount);  // Read the x/y/z adc values
    mpu.getAres();

    mpu.ax = (float)mpu.accelCount[0]*mpu.aRes; // - accelBias[0];
    mpu.ay = (float)mpu.accelCount[1]*mpu.aRes; // - accelBias[1];
    mpu.az = (float)mpu.accelCount[2]*mpu.aRes; // - accelBias[2];

    mpu.readGyroData(mpu.gyroCount);  // Read the x/y/z adc values
    mpu.getGres();

    // Calculate the gyro value into actual degrees per second
    // This depends on scale being set
    mpu.gx = (float)mpu.gyroCount[0]*mpu.gRes;
    mpu.gy = (float)mpu.gyroCount[1]*mpu.gRes;
    mpu.gz = (float)mpu.gyroCount[2]*mpu.gRes;

    mpu.readMagData(mpu.magCount);  // Read the x/y/z adc values
    mpu.getMres();
    // User environmental x-axis correction in milliGauss, should be
    // automatically calculated
    mpu.magbias[0] = +470.;
    // User environmental x-axis correction in milliGauss
    mpu.magbias[1] = +120.;
    // User environmental x-axis correction in milliGauss
    mpu.magbias[2] = +125.;

    //compute

    // Calculate the magnetometer values in milliGauss
    // Include factory calibration per data sheet and user environmental
    // corrections
    // Get actual magnetometer value, this depends on scale being set
    mpu.mx = (float)mpu.magCount[0]*mpu.mRes*mpu.magCalibration[0] -
               mpu.magbias[0];
    mpu.my = (float)mpu.magCount[1]*mpu.mRes*mpu.magCalibration[1] -
               mpu.magbias[1];
    mpu.mz = (float)mpu.magCount[2]*mpu.mRes*mpu.magCalibration[2] -
               mpu.magbias[2];

    mpu.updateTime();
    
    MahonyQuaternionUpdate(mpu.ax, mpu.ay, mpu.az, mpu.gx*DEG_TO_RAD,
                         mpu.gy*DEG_TO_RAD, mpu.gz*DEG_TO_RAD, mpu.mx,
                         mpu.my, mpu.mz, mpu.deltat);

    mpu.delt_t = millis() - mpu.count;


    mpu.yaw   = atan2(2.0f * (*(getQ()+1) * *(getQ()+2) + *getQ() *
                    *(getQ()+3)), *getQ() * *getQ() + *(getQ()+1) * *(getQ()+1)
                    - *(getQ()+2) * *(getQ()+2) - *(getQ()+3) * *(getQ()+3));
    mpu.pitch = -asin(2.0f * (*(getQ()+1) * *(getQ()+3) - *getQ() *
                    *(getQ()+2)));
    mpu.roll  = atan2(2.0f * (*getQ() * *(getQ()+1) + *(getQ()+2) *
                    *(getQ()+3)), *getQ() * *getQ() - *(getQ()+1) * *(getQ()+1)
                    - *(getQ()+2) * *(getQ()+2) + *(getQ()+3) * *(getQ()+3));

    mpu.pitch *= RAD_TO_DEG;
    mpu.yaw   *= RAD_TO_DEG;
    mpu.roll  *= RAD_TO_DEG;

    // Declination of SparkFun Electronics (51°30'0.0"N 0°7'34.0"E) is
    // 	1° 1' E  ± 0° 23'  changing by  0° 10' E per year, 2025-03-02
    // - http://www.ngdc.noaa.gov/geomag-web/#declination
    
    mpu.yaw -= 1.1;

    // *pitch = mpu.pitch;
    // *roll = mpu.roll;
    // *yaw = mpu.yaw;
    *pitch = mpu.mx;
    *roll = mpu.my;
    *yaw = mpu.mz;

    mpu.count = millis();
    mpu.sumCount = 0;
    mpu.sum = 0;

    return SUCCESS;
}

} /* namespace socket */ 
