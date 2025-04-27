#ifndef FILTERS_H_
#define FILTERS_H_

#include "Particle.h"
#include <climits>
#include <cstring>

namespace filters {

struct Vector3 {
    float x; 
    float y; 
    float z; 
};

struct DataPacket {
    float pitch; 
    float roll; 
    float yaw; 
    float d_pitch; 
    float d_roll; 
    float d_yaw; 
    float acc_x; 
    float acc_y; 
    float acc_z; 
    float gy_x; 
    float gy_y; 
    float gy_z; 
    bool flex0;
    bool flex1;
    bool flex2;
};

// Process new readings
void PushNewFlexReadings(const int &flex0, const int &flex1,
                         const int &flex2); // flexsensors
void PushNewGyroReadings(Vector3& data);  // gyro
void PushNewAccelReadings(Vector3& data); // accel
void PushNewYprReadings(const float &pitch, const float &roll,
                        const float &yaw); // pitch, roll, yaw

DataPacket* GetDataPacket(); 

} /* namespace filters */

#endif /* FILTERS_H_ */
