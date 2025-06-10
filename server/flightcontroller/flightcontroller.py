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
        """Connect to the DJI Tello Edu"""
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
        ...
        

    def run(self): 
        """
        Control the drone

        This will happen differently based on the 4 different control states.

        GESTURE_CONTROL: Recognise gestures and send pre-defined commands to the drone.
        MANUAL_CONTROL: Control the drone based on the pitch, roll and yaw difference of the controller
        REMOTE_OVERRIDE: Control the drone using the arrow keys on the arrow keys and C / V / SPACE
        ESTOP: Land immediately as soon as this is triggered. 
        """

        self.logger.info("Spinning up Flight Controller run loop...")

        while True:
            # If emergency stop, land immediately
            if self.estop:
                if self.connected:
                    self.logger.warning("ESTOP triggered - landing drone")
                    self.drone.land()
                else:
                    self.logger.warning("ESTOP triggered but drone is not connected. Program will continue to attempt connection and land immediately.")

            # Attempt connection if not connected 
            if not self.connected:
                self.connect()
                time.sleep(3)  # Retry every 3 seconds
                continue

            # Update the flight mode by reading the redis variable. Also store
            # the old flight mode so we can trigger events on switching between
            # different modes
            old_flight_mode = self.flight_mode
            self.flight_mode = self.redisconn.get("flight_mode")

            if self.flight_mode == "gesture":
                ...

            elif self.flight_mode == "manual":
                # If we have just entered manual mode, then we need to calibrate the current position of the controller
                if old_flight_mode != "manual": 
                    self.set_ypr_thresholds()
                ...


            elif self.flight_mode == "remote_override":
                ...

            else:
                self.logger.error("Undefined control state encountered! Escalating to ESTOP to prevent undefined behaviour")
                self.estop = True


if __name__ == "__main__":
    redisconn = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0, decode_responses=False)
    fc = FlightController(redisconn=redisconn, verbose=config.LUME_VERBOSE)
    fc.run()
