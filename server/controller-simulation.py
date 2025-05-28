#!/usr/bin/env python3
"""
Simulate the controller connection by sending packets over UDP. Used for
testing the software agnostic of the hardware
"""

import socket
import time
import signal
import sys
import threading

class UDPSender:
    def __init__(self, target_ip="127.0.0.1", target_port=12345, frequency=64):
        self.target_ip = target_ip
        self.target_port = target_port
        self.frequency = frequency
        self.interval = 1.0 / frequency  # Time between packets in seconds
        self.running = False
        
        # Create UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
    
    def create_packet_data(self):
        """
        Create packet data - customize this method with your own data
        Currently returns arbitrary bytes that you can replace
        """
        # Example arbitrary data - replace with your own
        packet_data = b'0123456789012345678901234567890123456789012345678'  # "Hello!" in hex
        return packet_data
    
    def send_packet(self):
        """Send a single UDP packet"""
        try:
            data = self.create_packet_data()
            bytes_sent = self.sock.sendto(data, (self.target_ip, self.target_port))
            return bytes_sent
        except Exception as e:
            print(f"Error sending packet: {e}")
            return False
    
    def start(self):
        """Start sending packets at the specified frequency"""
        self.running = True
        packet_count = 0
        start_time = time.time()
        
        print(f"Starting UDP packet transmission:")
        print(f"Target: {self.target_ip}:{self.target_port}")
        print(f"Frequency: {self.frequency} Hz")
        print(f"Interval: {self.interval:.3f} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Send packet
                bytes_sent = self.send_packet()
                if bytes_sent:
                    packet_count += 1
                
                # Calculate sleep time to maintain frequency
                loop_duration = time.time() - loop_start
                sleep_time = self.interval - loop_duration
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                elif sleep_time < -0.001:  # More than 1ms behind
                    print(f"Warning: Running behind schedule by {-sleep_time*1000:.1f}ms")
        
        except KeyboardInterrupt:
            self.stop()
            pass
        finally:
            self.stop()
            
        # Final statistics
        elapsed = time.time() - start_time
        actual_rate = packet_count / elapsed if elapsed > 0 else 0
        print(f"\nTransmission complete:")
        print(f"Total packets sent: {packet_count}")
        print(f"Total time: {elapsed:.2f} seconds")
        print(f"Actual rate: {actual_rate:.2f} Hz")

    def send_control_commands(self):
        print("0 - ESTOP \n1 - MANUAL MODE \n2 - GESTURE MODE \n3 - HARDWARE ERROR\n")
        
        while self.running:
            try:
                command_number = input("Please enter a number corresponding to a command to send: ")
                # Do not validate - allow sending invalid control commands to test the backend. 

                # So assume that the command is valid
                command = f"LUME{command_number}"
                try:
                    bytes_sent = self.sock.sendto(command.encode('utf-8'), (self.target_ip, self.target_port))
                    if bytes_sent:
                        print(f"Sent command: {command}")
                except Exception as e:
                    print(f"Error sending packet: {e}")
            except KeyboardInterrupt:
                self.stop()
                break
    
    def stop(self):
        """Stop packet transmission"""
        self.running = False
        if self.sock:
            self.sock.close()
            print("Socket closed")

def main():
    # Configuration - modify these values as needed
    TARGET_IP = "127.0.0.1"      # Correct for your Docker port mapping
    TARGET_PORT = 8888           # Updated to match your tcpdump
    FREQUENCY = 64               # Packets per second
    
    print("Docker UDP Communication:")
    print(f"Your container mapping: 0.0.0.0:8888->8888/udp")
    print(f"Sending to: {TARGET_IP}:{TARGET_PORT}")
    print()
    
    # Create and start sender to send arbitrary packets in the background in
    # order to keep the UDPServer happy on the server side
    sender = UDPSender(TARGET_IP, TARGET_PORT, FREQUENCY)
    sender_thread = threading.Thread(target=sender.start, daemon=True)
    sender_thread.start()

    time.sleep(1)

    # Now allow the user to test using the control commands
    sender.send_control_commands()

if __name__ == "__main__":
    main()
