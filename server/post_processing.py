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
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation

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
        """Perform an FFT of the filtered accelerometer, gyro, and attitude readings"""

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

    def run(self):
        """Run the sensor data post-processor"""
        self.logger.info(f"Starting data post-processing client")
        try:
            if self.do_fft:
                self.ani = animation.FuncAnimation(self.fig, self.fft, interval=100, blit=True)
                plt.show(block=True)

        except KeyboardInterrupt:
            # Warning is already given by other modules, no point repeating
            pass


