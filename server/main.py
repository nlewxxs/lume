#!/usr/bin/env python3
"""
Minimal UDP Server for efficiently transferring 6 floats with Particle Photon 2.
No protocol header, just raw binary float data.
"""
import socket
import time
import argparse
import logging
import sys
import struct
from typing import Tuple, Optional, List

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    
    class DummyFore:
        GREEN = YELLOW = RED = WHITE = CYAN = BLUE = MAGENTA = ""
    
    class DummyStyle:
        BRIGHT = RESET_ALL = ""
    
    Fore = DummyFore()
    Style = DummyStyle()


class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored console logs."""
    
    FORMATS = {
        logging.DEBUG: Fore.BLUE + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.INFO: Fore.WHITE + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.ERROR: Fore.RED + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class UDPServer:
    """UDP Server that receives binary float data from a microcontroller."""
    
    def __init__(self, port: int = 8888, verbose: bool = False):
        """Initialize the UDP server.
        
        Args:
            port: UDP port number to use (default: 8888)
            verbose: Enable debug-level logging if True
        """
        self.port = port
        
        # Setup logging with color
        self._setup_colored_logging(verbose)
        
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
    
    def decode_floats(self, data: bytes) -> List[float]:
        """Decode binary data into a list of floats.
        
        Args:
            data: Binary data received from the device
            
        Returns:
            List of float values
        """
        # Check if we have exactly 6 floats (4 bytes each)
        expected_size = 6 * 4  # 6 floats, 4 bytes each
        
        if len(data) == expected_size:
            # Unpack 6 floats (IEEE 754 format, network byte order)
            return list(struct.unpack('<6f', data))
        elif len(data) > expected_size:
            self.logger.warning(f"Received more data than expected: {len(data)} bytes")
            # Still try to parse the first 6 floats
            return list(struct.unpack('<6f', data[:expected_size]))
        else:
            self.logger.warning(f"Incomplete data received: {len(data)} bytes, expected {expected_size}")
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
            if len(data) >= 24:  # At least 6 floats
                values = self.decode_floats(data)
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
            values = self.decode_floats(data)
            
            if values:
                return values, addr
            else:
                return None
                
        except (socket.timeout, TimeoutError):
            self.logger.warning("Receive operation timed out")
            return None
    
    def run(self, device_ip: str, polling_interval: float = 5.0):
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
                while True:
                    result = self.receive_data()
                    if result is None:
                        self.logger.warning("Connection lost, returning to polling mode")
                        break
                    
                    values, addr = result
                    self.logger.debug(f"Received values {values} from {addr}")
                    
                    # Process the 6 float values here as needed
                    # This is where you would add your application logic
                        
        except KeyboardInterrupt:
            self.logger.warning("Received keyboard interrupt, shutting down...")
        finally:
            if hasattr(self, 'sock') and self.sock:
                self.sock.close()
                self.logger.info("Socket closed")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Minimal UDP Server for binary float data exchange with Particle Photon 2"
    )
    parser.add_argument(
        "--ip", 
        required=True,
        help="IP address of the Particle Photon 2 device on WLAN"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8888,
        help="UDP port to use (default: 8888)"
    )
    parser.add_argument(
        "--polling-interval", 
        type=float, 
        default=5.0,
        help="Time in seconds between polling attempts (default: 5.0)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (debug) logging"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    server = UDPServer(port=args.port, verbose=args.verbose)
    server.run(args.ip, args.polling_interval)
