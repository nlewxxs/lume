#!/usr/bin/env python3
"""
Minimal UDP Server for efficiently transferring 6 floats with Particle Photon 2.
No protocol header, just raw binary float data.
"""
import socket
import time
import logging
import sys
import struct
import keyboard
import redis

from shared.lume_logger import *
from shared.config import config
from typing import Tuple, Optional, List

REDIS_SENSORS_CHANNELS = ['pitch', 'roll', 'yaw', 'd_pitch', 'd_roll', 'd_yaw',
                          'acc_x', 'acc_y', 'acc_z', 'gy_x', 'gy_y', 'gy_z',
                          'flex0', 'flex1', 'flex2']

class LumeServer:
    """UDP Server that receives binary float data from a microcontroller."""
    
    def __init__(self, redisconn: redis.client.Redis, port: int = 8888, verbose: bool = False):
        """Initialise the UDP server.
        
        Args:
            port: UDP port number to use (default: 8888)
            verbose: Enable debug-level logging if True
        """
        self.port = port
        self.redisconn = redisconn

        # Extract the run mode straight away
        self.mode = redisconn.get(config.LUME_RUN_MODE)
        self.window_size = config.LUME_FFT_DATA_WINDOW_SIZE if self.mode == 'fft' else config.LUME_DEPLOY_DATA_WINDOW_SIZE
        
        # Setup logging with color
        self._setup_colored_logging(verbose)

        # Set the variable to record gestures as false
        self.redisconn.set(config.REDIS_RECORD_VARIABLE, 0)
        
        # Initialize socket
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(3)  # 3 second timeout
            self.sock.bind(("0.0.0.0", self.port))
            self.logger.info(f"UDP server initialized on port {self.port}")
        except socket.error as e:
            self.logger.error(f"Socket initialization failed: {e}")
            sys.exit(1)
    
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
    
    def unpack(self, data: bytes) -> List[float]:
        """Decode bitpacked binary data into a list of floats.
        
        Args:
            data: Binary data received from the device
            
        Returns:
            List of float values, plus 3 booleans at the end
        """
        payload_size = config.LUME_SENSOR_PAYLOAD_SIZE

        if len(data) == payload_size:
            # Unpack 12 floats (IEEE 754 format, network byte order)
            *floats, control = struct.unpack('<12fB', data)

            # Extract the booleans for flex sensors from the last byte
            flex0 = bool(control & 0b10000000)
            flex1 = bool(control & 0b01000000)
            flex2 = bool(control & 0b00100000)

            # append them onto the floats array and return it
            floats.append(flex0)
            floats.append(flex1)
            floats.append(flex2)
            return floats
            
        elif len(data) > payload_size:
            self.logger.warning(f"Received more data than expected: {len(data)} bytes")
            # Still try to parse the first 12 floats
            return list(struct.unpack('<12f', data[:payload_size]))
        else:
            self.logger.warning(f"Incomplete data received: {len(data)} bytes, expected {payload_size}")
            return []
    
    def poll_device(self, device_ip: str) -> bool:
        """Poll the receiver device to establish connection.
        
        Args:
            device_ip: IP address of the receiver device
            
        Returns:
            True if connection established, False otherwise
        """
        self.logger.info(f"Polling device at {device_ip}...")
        try:
            # Send a simple ping (1 byte)
            self.sock.sendto(b"P", (device_ip, self.port))
            
            # Wait for any response
            data, addr = self.sock.recvfrom(1024)
            self.logger.info(f"Connection established with {addr}")
            
            # Try to decode as floats if it looks like float data
            if len(data) >= config.LUME_SENSOR_PAYLOAD_SIZE:  # At least payload size
                values = self.unpack(data)
                if values:
                    self.logger.info(f"Received initial values: {values}")
            
            return True
                
        except (socket.timeout, TimeoutError):
            self.logger.warning("Connection timed out during polling")
            return False
    
    def receive_data(self) -> Optional[Tuple[List[float], Tuple[str, int]]]:
        """Receive a UDP packet with float data.
        
        Returns:
            Tuple of (float_values, address) if successful, None otherwise
        """
        try:
            data, addr = self.sock.recvfrom(1024)
            values = self.unpack(data)
            
            if values:
                return values, addr
            else:
                return None
                
        except (socket.timeout, TimeoutError):
            self.logger.warning("Receive operation timed out")
            return None

    def publish_sensor_data(self, data): 
        """Publish the filtered sensor data onto the respective Redis channels
        so that it can be post-processed"""

        for i in range(len(data)):
            queue = REDIS_SENSORS_CHANNELS[i]
            content = (float(data[i] == 1.0) if (queue in ["flex0","flex1","flex2"]) else data[i])
            
            self.logger.debug(f"Publishing {content} to {queue}")
            self.redisconn.lpush(queue, content)
            self.redisconn.ltrim(queue, 0, self.window_size - 1)

    def run(self, device_ip: str, polling_interval: float = 2.0):
        """Run the UDP server main loop.
        
        Args:
            device_ip: IP address of the receiver device
            polling_interval: Time in seconds between polling attempts when disconnected
        """
        self.logger.info(f"Starting UDP server, connecting to {device_ip}")
        
        try:
            while True:
                # Try to establish/re-establish connection
                connected = False
                while not connected:
                    connected = self.poll_device(device_ip)
                    if not connected:
                        self.logger.info(f"Retrying in {polling_interval} seconds...")
                        time.sleep(polling_interval)
                
                # Process incoming data until connection is lost
                self.logger.debug("Entering data reception mode")
                old_recording = False
                pub_counter = 0

                while True:
                    result = self.receive_data()

                    if result is None:
                        self.logger.warning("Connection lost, returning to polling mode")
                        break

                    recording = keyboard.is_pressed("shift")
                    log_colour = Fore.MAGENTA if recording else Fore.WHITE

                    # Print 'recording' only if we just started recording
                    if recording and not old_recording:
                        self.logger.info("Recording gesture...")
                        # Enable recording
                        self.redisconn.set(config.REDIS_RECORD_VARIABLE, 1)
                    if not recording and old_recording:
                        self.logger.info("Processing gesture...")
                        # Disable recording
                        self.redisconn.set(config.REDIS_RECORD_VARIABLE, 0)

                    old_recording = recording
                    values, _ = result
                    
                    if recording: 
                        self.publish_sensor_data(values)

                    self.logger.debug(f"{log_colour}Received values {values} {Style.RESET_ALL}")

                    # Publish values and update the version counter if new full window of data
                    pub_counter += 1
                    if (pub_counter % self.window_size == 0):
                        self.redisconn.incr(config.REDIS_DATA_VERSION_CHANNEL)
                        
        except KeyboardInterrupt:
            self.logger.warning("Received keyboard interrupt, shutting down...")
        finally:
            if hasattr(self, 'sock') and self.sock:
                self.sock.close()
                self.logger.info("Socket closed")

if __name__ == "__main__":
    
    redisconn = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0, decode_responses=False)

    endpoint = LumeServer(port=config.LUME_UDP_PORT, redisconn=redisconn,
                          verbose=config.LUME_VERBOSE)

    endpoint.run(device_ip=config.LUME_CONTROLLER_IP)

