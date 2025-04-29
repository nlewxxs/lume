#include <deque>

#include "Particle.h"
#include "filters.hpp"

namespace {
static constexpr int kFlexSensorThreshold{
    1700}; // threshold above which sensor is deemed 'bent'

static filters::DataPacket packet;

static constexpr std::array<float, kWindowSize> kGyroLPFCoeffs = {
    -4.70446993e-04, -2.91949771e-04,  6.11132306e-19,  3.31610501e-04,
    6.03730161e-04,  7.11082490e-04,  5.74378721e-04,  1.78727573e-04,
    -3.96977400e-04, -9.78505607e-04, -1.33549532e-03, -1.25907226e-03,
    -6.55986686e-04,  3.77746926e-04,  1.54268255e-03,  2.40453669e-03,
    2.53833544e-03,  1.70594227e-03, -2.51492230e-18, -2.11412925e-03,
    -3.89934090e-03, -4.58095088e-03, -3.64729783e-03, -1.10919181e-03,
    2.39420572e-03,  5.71577996e-03,  7.54375492e-03,  6.87611651e-03,
    3.46658796e-03, -1.93478775e-03, -7.67553876e-03, -1.16532886e-02,
    -1.20202224e-02, -7.92129461e-03,  5.74745203e-18,  9.55239877e-03,
    1.74992637e-02,  2.05266010e-02,  1.64152968e-02,  5.04856235e-03,
    -1.11091352e-02, -2.72966964e-02, -3.75183405e-02, -3.61477887e-02,
    -1.96427937e-02,  1.21381258e-02,  5.54470280e-02,  1.03198880e-01,
    1.46481428e-01,  1.76652565e-01,  1.87467727e-01,  1.76652565e-01,
    1.46481428e-01,  1.03198880e-01,  5.54470280e-02,  1.21381258e-02,
    -1.96427937e-02, -3.61477887e-02, -3.75183405e-02, -2.72966964e-02,
    -1.11091352e-02,  5.04856235e-03,  1.64152968e-02,  2.05266010e-02,
    1.74992637e-02,  9.55239877e-03,  5.74745203e-18, -7.92129461e-03,
    -1.20202224e-02, -1.16532886e-02, -7.67553876e-03, -1.93478775e-03,
    3.46658796e-03,  6.87611651e-03,  7.54375492e-03,  5.71577996e-03,
    2.39420572e-03, -1.10919181e-03, -3.64729783e-03, -4.58095088e-03,
    -3.89934090e-03, -2.11412925e-03, -2.51492230e-18,  1.70594227e-03,
    2.53833544e-03,  2.40453669e-03,  1.54268255e-03,  3.77746926e-04,
    -6.55986686e-04, -1.25907226e-03, -1.33549532e-03, -9.78505607e-04,
    -3.96977400e-04,  1.78727573e-04,  5.74378721e-04,  7.11082490e-04,
    6.03730161e-04,  3.31610501e-04,  6.11132306e-19, -2.91949771e-04,
    -4.70446993e-04 };

static constexpr std::array<float, kWindowSize> kAccelLPFCoeffs = {
    9.92182149e-05,  4.05709213e-04,  5.53786308e-04,  4.60823912e-04,
    1.27327902e-04, -3.41344531e-04, -7.49529997e-04, -8.75590470e-04,
    -5.75606148e-04,  1.15207114e-04,  9.43165061e-04,  1.50511023e-03,
    1.42351510e-03,  5.61370591e-04, -8.33856959e-04, -2.15947219e-03,
    -2.69133612e-03, -1.94555840e-03,  2.93043231e-18,  2.41107919e-03,
    4.13437752e-03,  4.11407157e-03,  1.97145205e-03, -1.64837254e-03,
    -5.19551398e-03, -6.83271261e-03, -5.32761588e-03, -8.09578946e-04,
    5.02645576e-03,  9.47856947e-03,  1.00161206e-02,  5.59398717e-03,
    -2.53508903e-03, -1.10078600e-02, -1.56244084e-02, -1.32745306e-02,
    -3.69062984e-03,  9.85348830e-03,  2.14209839e-02,  2.47330224e-02,
    1.61079359e-02, -3.21385344e-03, -2.64965271e-02, -4.32115045e-02,
    -4.26255808e-02, -1.80384972e-02,  2.99704499e-02,  9.26811028e-02,
    1.55310741e-01,  2.01465129e-01,  2.18440738e-01,  2.01465129e-01,
    1.55310741e-01,  9.26811028e-02,  2.99704499e-02, -1.80384972e-02,
    -4.26255808e-02, -4.32115045e-02, -2.64965271e-02, -3.21385344e-03,
    1.61079359e-02,  2.47330224e-02,  2.14209839e-02,  9.85348830e-03,
    -3.69062984e-03, -1.32745306e-02, -1.56244084e-02, -1.10078600e-02,
    -2.53508903e-03,  5.59398717e-03,  1.00161206e-02,  9.47856947e-03,
    5.02645576e-03, -8.09578946e-04, -5.32761588e-03, -6.83271261e-03,
    -5.19551398e-03, -1.64837254e-03,  1.97145205e-03,  4.11407157e-03,
    4.13437752e-03,  2.41107919e-03,  2.93043231e-18, -1.94555840e-03,
    -2.69133612e-03, -2.15947219e-03, -8.33856959e-04,  5.61370591e-04,
    1.42351510e-03,  1.50511023e-03,  9.43165061e-04,  1.15207114e-04,
    -5.75606148e-04, -8.75590470e-04, -7.49529997e-04, -3.41344531e-04,
    1.27327902e-04,  4.60823912e-04,  5.53786308e-04,  4.05709213e-04,
    9.92182149e-05 };

static constexpr std::array<float, kWindowSize> kOrientLPFCoeffs = {
    3.60568101e-04,  2.01379742e-04, -4.07991328e-19, -2.28736734e-04,
    -4.62721286e-04, -6.70761828e-04, -8.13430194e-04, -8.47574980e-04,
    -7.34544437e-04, -4.50986505e-04,  8.18898687e-19,  5.80297744e-04,
    1.21380051e-03,  1.79137912e-03,  2.18473373e-03,  2.26819174e-03,
    1.94547484e-03,  1.17671685e-03, -1.67895966e-18, -1.45827415e-03,
    -2.98860012e-03, -4.32119625e-03, -5.16527175e-03, -5.26009057e-03,
    -4.43010230e-03, -2.63436367e-03,  2.77540666e-18,  3.16915481e-03,
    6.41437749e-03,  9.17529211e-03,  1.08700318e-02,  1.09925097e-02,
    9.21274626e-03,  5.46391339e-03, -3.83699334e-18, -6.58900876e-03,
    -1.34120876e-02, -1.93626768e-02, -2.32472018e-02, -2.39416619e-02,
    -2.05557129e-02, -1.25808597e-02,  4.60109734e-18,  1.66602672e-02,
    3.63459100e-02,  5.75623087e-02,  7.85236031e-02,  9.73471724e-02,
    1.12268823e-01,  1.21850576e-01,  1.25153271e-01,  1.21850576e-01,
    1.12268823e-01,  9.73471724e-02,  7.85236031e-02,  5.75623087e-02,
    3.63459100e-02,  1.66602672e-02,  4.60109734e-18, -1.25808597e-02,
    -2.05557129e-02, -2.39416619e-02, -2.32472018e-02, -1.93626768e-02,
    -1.34120876e-02, -6.58900876e-03, -3.83699334e-18,  5.46391339e-03,
    9.21274626e-03,  1.09925097e-02,  1.08700318e-02,  9.17529211e-03,
    6.41437749e-03,  3.16915481e-03,  2.77540666e-18, -2.63436367e-03,
    -4.43010230e-03, -5.26009057e-03, -5.16527175e-03, -4.32119625e-03,
    -2.98860012e-03, -1.45827415e-03, -1.67895966e-18,  1.17671685e-03,
    1.94547484e-03,  2.26819174e-03,  2.18473373e-03,  1.79137912e-03,
    1.21380051e-03,  5.80297744e-04,  8.18898687e-19, -4.50986505e-04,
    -7.34544437e-04, -8.47574980e-04, -8.13430194e-04, -6.70761828e-04,
    -4.62721286e-04, -2.28736734e-04, -4.07991328e-19,  2.01379742e-04,
    3.60568101e-04 };
}

namespace filters {

// Define LP FIR filters, num taps is according to kWindowSize
FIRFilter accel_x_lpf(kAccelLPFCoeffs);
FIRFilter accel_y_lpf(kAccelLPFCoeffs);
FIRFilter accel_z_lpf(kAccelLPFCoeffs);
FIRFilter gyro_x_lpf(kGyroLPFCoeffs);
FIRFilter gyro_y_lpf(kGyroLPFCoeffs);
FIRFilter gyro_z_lpf(kGyroLPFCoeffs);
FIRFilter pitch_lpf(kOrientLPFCoeffs);
FIRFilter roll_lpf(kOrientLPFCoeffs);
FIRFilter yaw_lpf(kOrientLPFCoeffs);

// Process new reading
float FIRFilter::process(float input) {
    // Push the data along one, popping from front of deque
    data.pop_back();
    data.push_front(input);

    // process LPF readings
    float output = 0.0f;
    for (std::size_t i = 0; i < kWindowSize; i++) {
      output += (coeffs)[i] * data[i];
    }

    return output;
}

bool IsBent(const int& data) {
    return (data <= kFlexSensorThreshold);
}

// Process new readings
void PushNewGyroReadings(Vector3& data) {
    packet.gy_x = gyro_x_lpf.process(data.x);
    packet.gy_y = gyro_y_lpf.process(data.y);
    packet.gy_z = gyro_z_lpf.process(data.z);
}

void PushNewAccelReadings(Vector3& data) {
    packet.acc_x = accel_x_lpf.process(data.x);
    packet.acc_y = accel_y_lpf.process(data.y);
    packet.acc_z = accel_z_lpf.process(data.z);
}

void PushNewYprReadings(const float &pitch, const float &roll,
                        const float &yaw) {
    float new_pitch = pitch_lpf.process(pitch);
    float new_roll = pitch_lpf.process(roll);
    float new_yaw = pitch_lpf.process(yaw);

    // Calculate the deltas first before replacing in packet
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
