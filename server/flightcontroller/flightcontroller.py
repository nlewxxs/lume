#!/usr/bin/env python3
"""
Python code for interfacing with the DJI Tello Edu drone
"""

import time
import redis
import sys
from threading import Thread
from djitellopy import Tello

from shared.lume_logger import *
from shared.config import config
from shared.packer import unpack_binary

PITCH_SIGNIFICANT_DELTA = 2.0
ROLL_SIGNIFICANT_DELTA = 2.0
YAW_SIGNIFICANT_DELTA = 2.0

class FlightController:
    def __init__(self, redisconn: redis.client.Redis, verbose: bool = False) -> None:
        self.redisconn = redisconn
        self.drone = Tello()
        self.connected = False
        self._setup_colored_logging(verbose)
        self.estop = False

        # Flight mode can be set to any of: "gesture", "manual", or "remote_override"
        self.flight_mode = "gesture"
    
    def connect(self):
        """Connect to the DJI Tello"""
        try:
            self.drone.connect()
            self.logger.warning("Connected to DJI tello drone")
            self.connected = True
        except Exception as e: 
            self.logger.warning(f"Failed to connect to drone: {e}")
            self.connected = False

    def _setup_colored_logging(self, verbose: bool):
        """Set up colored logging for the application."""
        self.logger = logging.getLogger(__name__)
        
        # Set log level
        log_level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(log_level)
        
        # Create console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(log_level)
        
        # Create and attach formatter
        formatter = ColoredFormatter() if COLORS_AVAILABLE else logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        
        # Add handler to logger if not already added
        if not self.logger.handlers:
            self.logger.addHandler(console)
        
        if not COLORS_AVAILABLE:
            self.logger.warning("colorama not installed. For colored logs, install with: pip install colorama")

    def set_ypr_thresholds(self):
        """Update the pitch, roll and yaw thresholds for manual mode"""
        self.logger.info("Setting YPR thresholds for manual control")

        try:
            base_readings = self.sensors_sub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if base_readings:
                unpacked = unpack_binary(base_readings['data'])
                base_pitch = unpacked['pitch']
                base_roll = unpacked['roll']
                base_yaw = unpacked['yaw']

                self.pitch_thresholds = (base_pitch - PITCH_SIGNIFICANT_DELTA, base_pitch + PITCH_SIGNIFICANT_DELTA)
                self.roll_thresholds = (base_roll - ROLL_SIGNIFICANT_DELTA, base_roll + ROLL_SIGNIFICANT_DELTA)
                self.yaw_thresholds = (base_yaw - YAW_SIGNIFICANT_DELTA, base_yaw + YAW_SIGNIFICANT_DELTA)

                self.logger.info(f"YPR thresholds set to: {self.pitch_thresholds}, {self.roll_thresholds}, {self.yaw_thresholds}")
            else:
                self.logger.error("No sensor readings found to set YPR thresholds")
        except Exception as e:
            self.logger.error(f"Error calibrating YPR readings for manual mode: {e}")

    def run(self): 
        """
        Control the drone

        This will happen differently based on the 4 different control states.

        GESTURE_CONTROL: Recognise gestures and send pre-defined commands to the drone.
        MANUAL_CONTROL: Control the drone based on the pitch, roll and yaw difference of the controller
        REMOTE_OVERRIDE: Control the drone using the arrow keys on the arrow keys and ] / # / T / L 
        ESTOP: Land immediately as soon as this is triggered. 
        """

        self.logger.info("Spinning up Flight Controller run loop...")
        self.redisconn.set('flight_mode', 'gesture')  # init flight mode
        
        # Create a subscription to the takeoff / land channel that is published to 
        takeoff_land_sub = self.redisconn.pubsub()
        takeoff_land_sub.subscribe("remote_takeoff_land")

        # Grab one batch of sensor readings
        self.sensors_sub = self.redisconn.pubsub()
        self.sensors_sub.subscribe('sensors')


        while True:
            # If emergency stop, land immediately
            if self.estop:
                if self.connected:
                    self.logger.warning("ESTOP triggered - landing drone")
                    self.drone.land()
                else:
                    self.logger.warning("ESTOP triggered but drone is not connected. Program will continue to attempt connection and land immediately.")

            # TODO: put back in when drone fixed
            # Attempt connection if not connected 
            # if not self.connected:
                # self.connect()
                # time.sleep(3)  # Retry every 3 seconds
                # continue

            # Update the flight mode by reading the redis variable. Also store
            # the old flight mode so we can trigger events on switching between
            # different modes
            old_flight_mode = self.flight_mode
            self.flight_mode = self.redisconn.get("flight_mode")

            self.flight_mode = self.flight_mode.decode('utf-8') if isinstance(self.flight_mode, bytes) else self.flight_mode
            
            # Log any changes
            if old_flight_mode != self.flight_mode:
                self.logger.info(f"Flight mode has been changed to: {self.flight_mode}")

            if self.flight_mode == "gesture":
                ...

            elif self.flight_mode == "manual":
                # If we have just entered manual mode, then we need to
                # calibrate the current position of the controller
                if old_flight_mode != "manual": 
                    self.set_ypr_thresholds()

                # Otherwise, just regularly read the sensor data and send the
                # corresponding commands based on YPR thresholds
                sensors = self.sensors_sub.get_message(ignore_subscribe_messages=True, timeout=0.1)

                if sensors:
                    unpacked = unpack_binary(sensors['data'])

                    if unpacked['pitch'] < self.pitch_thresholds[0]:
                        self.logger.info("left")
                    elif unpacked['pitch'] > self.pitch_thresholds[1]:
                        self.logger.info("right")
                

                    if unpacked['roll'] < self.roll_thresholds[0]:
                        self.logger.info("forward")
                    elif unpacked['roll'] > self.roll_thresholds[1]:
                        self.logger.info("back")


                    if unpacked['yaw'] < self.yaw_thresholds[0]:
                        self.logger.info("pan left")
                    elif unpacked['yaw'] > self.yaw_thresholds[1]:
                        self.logger.info("pan right")


            elif self.flight_mode == "remote_override":
                # First check for any commands on the takeoff / land channel
                takeoff_cmd = takeoff_land_sub.get_message(ignore_subscribe_messages=True, timeout=0.01)
                if takeoff_cmd:
                    print(takeoff_cmd)

                # Then, get the current command from the remote_command variable
                move_cmd = self.redisconn.get("remote_command")
                move_cmd = move_cmd.decode('utf-8') if isinstance(move_cmd, bytes) else move_cmd

                if move_cmd:
                    print(move_cmd)

            else:
                self.logger.error(f"Undefined control state {self.flight_mode} encountered! Escalating to ESTOP to prevent undefined behaviour")
                self.estop = True
            
            old_flight_mode = self.flight_mode


if __name__ == "__main__":
    redisconn = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0, decode_responses=False)
    fc = FlightController(redisconn=redisconn, verbose=config.LUME_VERBOSE)
    fc.run()
