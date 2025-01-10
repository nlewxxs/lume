/* 
 * Project myProject
 * Author: Your Name
 * Date: 
 * For comprehensive documentation and examples, please visit:
 * https://docs.particle.io/firmware/best-practices/firmware-template/
 */

#include "Particle.h"
#include "MPU9250.h"
#include "quaternionFilters.h"
#include "system_mode.h"
#include <climits>
#include <cstring>

#define AHRS true  // enable filtering and fusion. Think this is the same as the DMP? not sure yet. 
MPU9250 mpu; // MPU9250 object definition

// Let Device OS manage the connection to the Particle Cloud
SYSTEM_MODE(AUTOMATIC);

// Run the application and system concurrently in separate threads
SYSTEM_THREAD(ENABLED);

UDP Udp;
unsigned int rx_port = 8888;
unsigned int tx_port = 8889;
byte MPU_EXPECTED_ADDRESS = 0x70;
byte address = 0x00;
bool mpu_online = false; 

// Show system, cloud connectivity, and application logs over USB
// View logs with CLI using 'particle serial monitor --follow'
SerialLogHandler logHandler(LOG_LEVEL_INFO);

void setup() {

    Serial.begin(9600);
    Wire.begin();

    // Udp.begin(rx_port);

    Log.info("attempting read byte...");
    address = mpu.readByte(MPU9250_ADDRESS, WHO_AM_I_MPU9250);
    Log.info("MPU9250 is at: %x", address);
    Log.info("MPU9250 should be at: %x", MPU_EXPECTED_ADDRESS);
    
    if (address == MPU_EXPECTED_ADDRESS) {
        Log.info("MPU9250 is online...");
        mpu_online = true;

        // Start by performing self test and reporting values
        mpu.MPU9250SelfTest(mpu.SelfTest);

        /* Log.info("x-axis self test: acceleration trim within : ");
        Log.info("%f", mpu.SelfTest[0]);
        Log.info("y-axis self test: acceleration trim within : ");
        Log.info("%f", mpu.SelfTest[1]); 
        Log.info("z-axis self test: acceleration trim within : ");
        Log.info("%f", mpu.SelfTest[2]);
        Log.info("x-axis self test: gyration trim within : ");
        Log.info("%f", mpu.SelfTest[3]); 
        Log.info("y-axis self test: gyration trim within : ");
        Log.info("%f", mpu.SelfTest[4]); 
        Log.info("z-axis self test: gyration trim within : ");
        Log.info("%f", mpu.SelfTest[5]);  */

        // Calibrate gyro and accelerometers, load biases in bias registers
        mpu.calibrateMPU9250(mpu.gyroBias, mpu.accelBias);
        mpu.initMPU9250();
    } 

    byte d = mpu.readByte(AK8963_ADDRESS, WHO_AM_I_AK8963);
    Log.info("AK8963 "); Log.info("I AM "); Log.info("%x", d);
    Log.info(" I should be "); Log.info("0x48");

    mpu.initAK8963(mpu.magCalibration);

}

void loop() {
    // The core of your code will likely live here.
    // Example: Publish event to cloud every 10 seconds. Uncomment the next 3 lines to try it!
    // Particle.publish(std::to_string(analogRead(A1)).c_str()); 
    // Log.info("localIP=%s", WiFi.localIP().toString().c_str());
/*     delay(1000); // milliseconds and blocking - see docs for more info!

    char* addy_buf = new char[3];
    std::sprintf(addy_buf, "%02X", address);

    Particle.publish(addy_buf);

    if (mpu_online) {
        Particle.publish("MPU is initialised");
    }

    delete[] addy_buf; */

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
    // User environmental x-axis correction in milliGauss TODO axis??
    mpu.magbias[1] = +120.;
    // User environmental x-axis correction in milliGauss
    mpu.magbias[2] = +125.;

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
    // Declination of SparkFun Electronics (40°05'26.6"N 105°11'05.9"W) is
    // 	8° 30' E  ± 0° 21' (or 8.5°) on 2016-07-19
    // - http://www.ngdc.noaa.gov/geomag-web/#declination
    mpu.yaw   -= 8.5;
    mpu.roll  *= RAD_TO_DEG;

    Log.info("Yaw: %f, Pitch: %f, Roll: %f", mpu.yaw, mpu.pitch, mpu.roll);
    Log.info("rate = %f Hz", (float)mpu.sumCount/mpu.sum);

    mpu.count = millis();
    mpu.sumCount = 0;
    mpu.sum = 0;


    /* if (Udp.parsePacket() > 0) {
        Particle.publish("Received packet!!");
        char c = Udp.read();

        while (Udp.available()) Udp.read();

        IPAddress ip = Udp.remoteIP(); 

        Udp.beginPacket(ip, tx_port);
        Udp.write(c);
        Udp.endPacket();
        Particle.publish("echoed packet!!");
    }   */
} 
