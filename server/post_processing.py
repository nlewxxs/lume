#!/usr/bin/env python3
"""
Post processing to be done server-side for sensor data being received. This
includes calculating means, variances and energies. There is also an option to
do an FFT, as this was required for choosing the appropriate corner frequency
for the LPFs on the controller side. 
"""
import logging
import sys
import redis
import struct
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from typing import Tuple, List
import zlib

from config import ENV
from lume_logger import *


class DataProcessor:
    def __init__(self, redisconn: redis.client.Redis, fft: bool = False, verbose: bool = False):
        """Initialise the sensor data post-processor.
        
        Args:
            verbose: Enable debug-level logging if True
        """
        self.redisconn = redisconn 
        self.config = ENV
        self.do_fft = fft
        self.mode = redisconn.get(ENV["redis_mode_variable"])
        self._setup_colored_logging(verbose)

        if fft:
            self.sampling_rate = self.config["sampling_rate"]
            self.T = 1 / self.sampling_rate
            self.N = self.config["data_window_size"]

            self.signal_keys = ['acc_x', 'acc_y', 'acc_z', 'gy_x', 'gy_y', 'gy_z', 'pitch', 'roll', 'yaw']
            self.signal_names = ['Accel X', 'Accel Y', 'Accel Z', 'Gyro X', 'Gyro Y', 'Gyro Z', 'Pitch', 'Roll', 'Yaw']

            # Set up figure and axes
            plt.ion()
            self.fig, self.axes = plt.subplots(3, 3, figsize=(18, 12))
            self.axes = self.axes.flatten()

            self.lines = []
            for ax, name in zip(self.axes, self.signal_names):
                line, = ax.plot([], [])
                ax.set_title(f'FFT of {name}')
                ax.set_xlabel('Frequency (Hz)')
                ax.set_ylabel('Amplitude')
                ax.grid(True)
                self.lines.append(line)

            # Hide extra axes
            if len(self.signal_names) < len(self.axes):
                for idx in range(len(self.signal_names), len(self.axes)):
                    self.fig.delaxes(self.axes[idx])

            plt.tight_layout()

        self.last_seen = None
        self.last_hash = None

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

    def fft(self, frame):
        """Perform an FFT of the filtered accelerometer, gyro, and attitude
        readings. This is displayed in a live window, updating roughly every
        ~16 seconds (for a batch of 1024 readings per window)"""

        current_version = self.redisconn.get(self.config['redis_data_version_channel'])
        if current_version == self.last_seen or current_version == None:
            return self.lines

        # Read all signals
        signals = []
        for key in self.signal_keys:
            raw = self.redisconn.lrange(key, 0, -1)
            if not raw or len(raw) < self.config['data_window_size']:
                return self.lines  # wait until Redis has data
            signals.append(np.array([float(x) for x in raw]))

        for idx, (signal, line) in enumerate(zip(signals, self.lines)):
            # Compute FFT
            fft_vals = np.fft.fft(signal)
            fft_freqs = np.fft.fftfreq(self.N, self.T)

            # Trim in the case where it has read the values after socket.py has
            # pushed the 51st element but not yet trimmed it. There is no need
            # for a mutex here, it will not make a huge difference to add
            # atomic reads
            window_size = self.config['data_window_size']
            fft_vals, fft_freqs = fft_vals[:window_size], fft_freqs[:window_size]

            # Only positive freqs
            pos_mask = fft_freqs >= 0
            fft_vals = fft_vals[pos_mask]
            fft_freqs = fft_freqs[pos_mask]

            # Update line
            line.set_data(fft_freqs, np.abs(fft_vals))
            self.axes[idx].set_xlim(0, np.max(fft_freqs))
            self.axes[idx].set_ylim(0, np.max(np.abs(fft_vals)) * 1.1)

        # Update last seen version
        self.last_seen = current_version

        return self.lines

    def calculate_mean_and_variance(self, data) -> Tuple[float, float]:
        """Calculate both the mean and the variance of a set of data, using
        Welford's algorithm"""
        n = 0
        mean = 0.0
        m2 = 0.0

        for x in data: 
            n += 1
            delta = x - mean
            mean += delta / n
            delta2 = x - mean
            m2 += delta * delta2

        return mean, m2 / (n - 1)

    def calculate_energy(self):
        """Calculate the energy of a signal over a specified window"""
        pass

    def pack(self, data : List[float]) -> bytes:
        """Pack the filtered and post-processed sensor data in to a""" 

        # First pack the values of flex0, flex1 and flex2 into a boolean (these
        # are passed as 0.0, or 1.0 into the function)
        flex_byte = 0x0
        flex_byte |= (0b10000000 if data[:-3] == 1.0 else 0b0)
        flex_byte |= (0b01000000 if data[:-2] == 1.0 else 0b0)
        flex_byte |= (0b00100000 if data[:-1] == 1.0 else 0b0)

        data = data[:-3]
        data.append(flex_byte)

        packed_data = struct.pack('<26fB', *data)
        return packed_data

    def process(self) -> None:
        """
        Calculate the energy, means and variances of the incoming data. This
        function is also responsible for periodically publshing a syncronised
        data packet to a Redis channel, in the form: 

            pitch, roll, yaw,
            d_pitch, d_roll, d_yaw,
            acc_x, acc_y, acc_z,
            acc_x_mean, acc_y_mean, acc_z_mean, 
            acc_x_var, acc_y_var, acc_z_var, 
            gy_x, gy_y, gy_z,
            gy_x_mean, gy_y_mean, gy_z_mean, 
            gy_x_var, gy_y_var, gy_z_var, 
            acc_energy, gy_energy,
            flex0, flex1, flex2

        This is what will be used by the ML algorithm to identify gestures. 
        """

        self.logger.info("Post processor active")

        # Loop indefinitely
        while True:
            # But only update when the hash of the data has changed. This
            # prevents duplicate updates. Check using first signal queue,
            # synchronisation is not a problem as we have only one publisher
            data = self.redisconn.lrange('pitch', 0, -1)
            data_bytes = b''.join(x.encode() if isinstance(x, str) else x for x in data)
            hash = zlib.crc32(data_bytes)

            if hash == self.last_hash:
                continue  # loop until new data
        
            signals = {}
            for key in self.config["redis_sensors_channels"]:
                raw = self.redisconn.lrange(key, 0, -1)
                if not raw or len(raw) < self.config['data_window_size']:
                    continue  # wait until required amount
                signals[key] = np.array([float(x) for x in raw])

            # To preserve order, we keep the indexing as per the docstring at
            # the top of this function
            sensor_data_packet = [0.0 for _ in range(29)]
            
            # Calculate the means and variance of every set that we need
            acc_x_mean, acc_x_var = self.calculate_mean_and_variance(signals['acc_x'])
            acc_y_mean, acc_y_var = self.calculate_mean_and_variance(signals['acc_y'])
            acc_z_mean, acc_z_var = self.calculate_mean_and_variance(signals['acc_z'])
            gy_x_mean, gy_x_var = self.calculate_mean_and_variance(signals['gy_x'])
            gy_y_mean, gy_y_var = self.calculate_mean_and_variance(signals['gy_y'])
            gy_z_mean, gy_z_var = self.calculate_mean_and_variance(signals['gy_z'])

            # add in the data according to the order
            sensor_data_packet[0] = signals['pitch'][0]
            sensor_data_packet[1] = signals['roll'][0]
            sensor_data_packet[2] = signals['yaw'][0]
            sensor_data_packet[3] = signals['d_pitch'][0]
            sensor_data_packet[4] = signals['d_roll'][0]
            sensor_data_packet[5] = signals['d_yaw'][0]
            sensor_data_packet[6] = signals['acc_x'][0]
            sensor_data_packet[7] = signals['acc_y'][0]
            sensor_data_packet[8] = signals['acc_z'][0]

            sensor_data_packet[9] = acc_x_mean
            sensor_data_packet[10] = acc_y_mean
            sensor_data_packet[11] = acc_z_mean
            sensor_data_packet[12] = acc_x_var
            sensor_data_packet[13] = acc_y_var
            sensor_data_packet[14] = acc_z_var

            sensor_data_packet[15] = signals['gy_x'][0]
            sensor_data_packet[16] = signals['gy_y'][0]
            sensor_data_packet[17] = signals['gy_z'][0]
            
            sensor_data_packet[18] = gy_x_mean
            sensor_data_packet[19] = gy_y_mean
            sensor_data_packet[20] = gy_z_mean
            sensor_data_packet[21] = gy_x_var
            sensor_data_packet[22] = gy_y_var
            sensor_data_packet[23] = gy_z_var

            # ... energies inserted later
            sensor_data_packet[26] = signals['flex0'][0]
            sensor_data_packet[27] = signals['flex1'][0]
            sensor_data_packet[28] = signals['flex2'][0]

            self.logger.debug(sensor_data_packet)
            packed = self.pack(sensor_data_packet)

            # Publish data window onto sensors channel
            self.redisconn.publish('sensors', packed)

            # Update hash to signify that we have processed this batch
            self.last_hash = hash  

    def run(self):
        """Run the sensor data post-processor"""
        self.logger.info(f"Starting data post-processing client")
        try:
            if self.do_fft:
                self.ani = animation.FuncAnimation(self.fig, self.fft, interval=100, blit=True)
                plt.show(block=True)
            else: 
                self.process()
                

        except KeyboardInterrupt:
            # Warning is already given by other modules, no point repeating
            pass


