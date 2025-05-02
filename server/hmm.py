#!/usr/bin/env python3
"""
Definitions for the hidden markov model (HMM) to be used in gesture recognition
"""

import psycopg2
import redis
import sys
import numpy as np
import json
from hmmlearn import hmm

from lume_logger import *
from config import ENV

class LumeHMM:
    def __init__(self, redisconn: redis.client.Redis, verbose: bool = False) -> None:
        
        self.redisconn = redisconn
        self._setup_colored_logging(verbose)


        # Variables that may or may not be initialised depending on the system mode
        self.training_data = {}
        self.conn = None
        self.cursor = None
    
    def load_training_data(self) -> None: 
        # Establish the connection to the postgres database - note this is
        # only done if we are loading training data, since we don't want to
        # call this every time the system is being deployed. 
        self.conn = psycopg2.connect(
            database=ENV["pg_db_name"],
            host=ENV["pg_db_host"],
            user=ENV["pg_db_user"],
            password=ENV["pg_db_pass"],
            port=ENV["pg_db_port"]
        )

        self.cursor = self.conn.cursor()

        # Data needs to be loaded into the form: 
        # training_data = {
            # 'takeoff': [sequence_1, sequence_2, ..., sequence_N],
            # 'land': [sequence_1, ..., sequence_N],
            # 'action_1': [sequence_1, ..., sequence_N],
            # 'action_2': [sequence_1, ..., sequence_N],
            # 'action_3': [sequence_1, ..., sequence_N],
        # }

        training_data = {}
        training_data['takeoff'] = self.get_gesture('takeoff')
        training_data['land'] = self.get_gesture('land')
        training_data['action_1'] = self.get_gesture('action_1')
        training_data['action_2'] = self.get_gesture('action_2')
        training_data['action_3'] = self.get_gesture('action_3')

        # Now convert the data such that each sequence = np.ndarray of shape
        # (~200, num_features). The sequence length may vary, this is a
        # strength of HMMs.
        keys = ['pitch', 'roll', 'yaw',
            'd_pitch', 'd_roll', 'd_yaw',
            'acc_x', 'acc_y', 'acc_z',
            'acc_x_mean', 'acc_y_mean', 'acc_z_mean', 
            'acc_x_var', 'acc_y_var', 'acc_z_var', 
            'gy_x', 'gy_y', 'gy_z',
            'gy_x_mean', 'gy_y_mean', 'gy_z_mean',
            'gy_x_var', 'gy_y_var', 'gy_z_var', 
            'acc_energy', 'gy_energy',
            'flex0', 'flex1', 'flex2'
        ]

        for gesture in training_data:
            # Unpack the tuples
            unpacked_data = training_data.copy()
            unpacked_data[gesture] = [frame[0] for frame in training_data[gesture]]
            training_data = unpacked_data

            np_sequences = []
            for sequence in training_data[gesture]:
                if sequence:
                    feature_vectors = [[frame[k] for k in keys] for frame in sequence]
                    np_sequences.append(np.array(feature_vectors))

            self.training_data[gesture] = np_sequences

        self.training_data['takeoff'] = self.training_data['land']
        self.training_data['action_1'] = self.training_data['land']
        self.training_data['action_2'] = self.training_data['land']
        self.training_data['action_3'] = self.training_data['land']
        

    def train(self): 
        # First check that the training data has been initialised
        if not bool(self.training_data):
            self.logger.error("No training data has been loaded!")
            return

        self.models = {}
        for gesture, sequences in self.training_data.items():
            X = np.vstack(sequences)
            lengths = [len(seq) for seq in sequences]  # needed for training

            # Define a Gaussian HMM
            model = hmm.GaussianHMM(n_components=5, covariance_type='diag', n_iter=1000)
            model.fit(X, lengths)
            self.models[gesture] = model

    def eval(self):
        sequence = self.training_data['land'][0]
        scores = {label: model.score(sequence) for label, model in self.models.items()}
        print(scores)


    def get_gesture(self, gesture : str):
        """Retrieve all the gesture samples for a specific gesture"""
        if self.cursor is not None:
            self.cursor.execute(f"""SELECT data FROM gestures
                                    WHERE gesture = '{gesture}'""")
            return self.cursor.fetchall() 
        else: 
            self.logger.error("pSQL cursor does not exist, operation failed")

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
