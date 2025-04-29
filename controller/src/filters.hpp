#ifndef FILTERS_H_
#define FILTERS_H_

#include "Particle.h"
#include <climits>
#include <cstring>
#include <deque>

static constexpr std::size_t kWindowSize{
    101}; // number of readings to consider in a single window

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

class FIRFilter {
public:
  FIRFilter(const std::array<float, kWindowSize>& coeffs) noexcept
  : data(kWindowSize, 0.0f), coeffs(coeffs) {}
      
  float process(float input);

private: 
    std::deque<float> data;
    const std::array<float, kWindowSize>& coeffs;
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
