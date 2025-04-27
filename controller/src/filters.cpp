#include <deque>

#include "Particle.h"
#include "filters.hpp"

namespace {
static constexpr std::size_t kWindowSize{
    50}; // number of readings to consider in a single window
static constexpr int kFlexSensorThreshold{
    1300}; // threshold above which sensor is deemed 'bent'

// accelerometer data window
static std::deque<float> accel_x_raw(kWindowSize, 0.0);
static std::deque<float> accel_y_raw(kWindowSize, 0.0);
static std::deque<float> accel_z_raw(kWindowSize, 0.0);

// gyroscope data window
static std::deque<float> gyro_x_raw(kWindowSize, 0.0);
static std::deque<float> gyro_y_raw(kWindowSize, 0.0);
static std::deque<float> gyro_z_raw(kWindowSize, 0.0);

// orientation (pitch / roll / yaw) data window 
static std::deque<float> pitch_raw(kWindowSize, 0.0);
static std::deque<float> roll_raw(kWindowSize, 0.0);
static std::deque<float> yaw_raw(kWindowSize, 0.0);

static filters::DataPacket packet;
}

namespace filters {

// LPF for Gyroscope readings
void GyroLowPass(const std::deque<float>& raw, float& filtered) {
    filtered = raw.back();
}

// LPF for Accelerometer readings
void AccelLowPass(const std::deque<float>& raw, float& filtered) {
    filtered = raw.back();
}

// LPF for Pitch, Roll and Yaw readings - use same coeffs for each one
void OrientationLowPass(const std::deque<float>& raw, float& filtered) {
    // TODO: actually do the filter
    filtered = raw.back();
}

bool IsBent(const int& data) {
    return (data <= kFlexSensorThreshold);
}

// Process new readings
void PushNewGyroReadings(Vector3& data) {
    // pop old elements
    gyro_x_raw.pop_front();
    gyro_y_raw.pop_front();
    gyro_z_raw.pop_front();
    // push in new elements
    gyro_x_raw.push_back(data.x);
    gyro_y_raw.push_back(data.y);
    gyro_z_raw.push_back(data.z);
    // apply filters
    GyroLowPass(gyro_x_raw, packet.gy_x);
    GyroLowPass(gyro_y_raw, packet.gy_y);
    GyroLowPass(gyro_z_raw, packet.gy_z);
}

void PushNewAccelReadings(Vector3& data) {
    // pop old elements
    accel_x_raw.pop_front();
    accel_y_raw.pop_front();
    accel_z_raw.pop_front();
    // push in new elements
    accel_x_raw.push_back(data.x);
    accel_y_raw.push_back(data.y);
    accel_z_raw.push_back(data.z);
    // apply filters
    AccelLowPass(accel_x_raw, packet.acc_x);
    AccelLowPass(accel_y_raw, packet.acc_y);
    AccelLowPass(accel_z_raw, packet.acc_z);
}

void PushNewYprReadings(const float &pitch, const float &roll,
                        const float &yaw) {
    // Pop old elements
    pitch_raw.pop_front();
    roll_raw.pop_front();
    yaw_raw.pop_front();
    // Push in new elements
    pitch_raw.push_back(pitch);
    roll_raw.push_back(roll);
    yaw_raw.push_back(yaw);
    // Apply lowpass filters and store in temps
    float new_pitch = 0.0;
    float new_roll = 0.0;
    float new_yaw = 0.0;
    OrientationLowPass(pitch_raw, new_pitch);
    OrientationLowPass(roll_raw, new_roll);
    OrientationLowPass(yaw_raw, new_yaw);
    // Calculate the diffs
    packet.d_pitch = new_pitch - packet.pitch;
    packet.d_roll = new_roll - packet.roll;
    packet.d_yaw = new_yaw - packet.yaw;
    // Copy in the new filtered ypr
    packet.pitch = new_pitch;
    packet.roll = new_roll;
    packet.yaw = new_yaw;
}

void PushNewFlexReadings(const int& flex0, const int& flex1, const int& flex2) {
    packet.flex0 = IsBent(flex0);
    packet.flex1 = IsBent(flex1);
    packet.flex2 = IsBent(flex2);
}

DataPacket* GetDataPacket() {
    return &packet;
};

} /* namespace filters */
