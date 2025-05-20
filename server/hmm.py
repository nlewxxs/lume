#!/usr/bin/env python3
"""
Enhanced definitions for the hidden markov model (HMM) to be used in gesture recognition
with improved feature selection, preprocessing, and model selection
"""

import psycopg2
import redis
import sys
import numpy as np
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.feature_selection import SelectKBest, mutual_info_regression
import joblib
from collections import Counter

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
        
        # Model configuration parameters - these can be tuned
        self.n_components = 7  # Increased from 5
        self.covariance_type = 'full'  # Changed from 'diag' to capture correlations
        self.n_iter = 2000  # Increased from 1000
        self.use_pca = True
        self.pca_components = 15  # Reduce to this many dimensions
        self.feature_selection = True
        self.k_best_features = 20  # Select top k features
        
        # Preprocessing options
        self.apply_smoothing = True
        self.smoothing_window = 5
    
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

        training_data = {}
        self.test_data = {}

        training_data['takeoff'] = self.get_gesture('takeoff')
        training_data['land'] = self.get_gesture('land')
        training_data['action_1'] = self.get_gesture('action_1')
        # training_data['action_2'] = self.get_gesture('action_2')
        training_data['action_3'] = self.get_gesture('action_3')
        
        # Feature keys
        keys = [
            'pitch', 'roll', 'yaw',
            'd_pitch', 'd_roll', 'd_yaw',
            'acc_x', 'acc_y', 'acc_z',
            'acc_x_mean', 'acc_y_mean', 'acc_z_mean', 
            'acc_x_var', 'acc_y_var', 'acc_z_var', 
            'gy_x', 'gy_y', 'gy_z',
            'gy_x_mean', 'gy_y_mean', 'gy_z_mean',
            'gy_x_var', 'gy_y_var', 'gy_z_var', 
            'acc_energy', 'gy_energy',
            # 'flex0', 'flex1', 'flex2'
        ]
        self.feature_keys = keys

        for gesture in training_data:
            # Unpack the tuples
            unpacked_data = training_data.copy()
            unpacked_data[gesture] = [frame[0] for frame in training_data[gesture]]
            training_data = unpacked_data

            np_sequences = []
            for sequence in training_data[gesture]:
                if sequence:
                    feature_vectors = [[frame[k] for k in keys] for frame in sequence]
                    np_sequence = np.array(feature_vectors)
                    
                    # Apply smoothing if enabled
                    if self.apply_smoothing:
                        np_sequence = self._apply_smoothing(np_sequence)
                    
                    np_sequences.append(np_sequence)

            self.training_data[gesture] = np_sequences

        # Use proper train/test split with stratification
        # Create a list of all sequences and their labels
        all_sequences = []
        all_labels = []
        for gesture, sequences in self.training_data.items():
            all_sequences.extend(sequences)
            all_labels.extend([gesture] * len(sequences))
            
        # Split into train and test sets
        train_sequences, test_sequences, train_labels, test_labels = train_test_split(
            all_sequences, all_labels, test_size=0.2, random_state=42, stratify=all_labels
        )
        
        # Reconstruct training and test data dictionaries
        self.training_data = {gesture: [] for gesture in set(all_labels)}
        self.test_data = {gesture: [] for gesture in set(all_labels)}
        
        for seq, label in zip(train_sequences, train_labels):
            self.training_data[label].append(seq)
            
        for seq, label in zip(test_sequences, test_labels):
            self.test_data[label].append(seq)
        
        # Log data distribution
        train_counts = {k: len(v) for k, v in self.training_data.items()}
        test_counts = {k: len(v) for k, v in self.test_data.items()}
        self.logger.info(f"Training data distribution: {train_counts}")
        self.logger.info(f"Test data distribution: {test_counts}")

    def _apply_smoothing(self, sequence):
        """Apply moving average smoothing to the sequence"""
        smoothed = np.zeros_like(sequence)
        window = self.smoothing_window
        half_window = window // 2
        
        # For each feature dimension
        for i in range(sequence.shape[1]):
            # Apply moving average
            for j in range(sequence.shape[0]):
                start = max(0, j - half_window)
                end = min(sequence.shape[0], j + half_window + 1)
                smoothed[j, i] = np.mean(sequence[start:end, i])
                
        return smoothed

    def train(self): 
        # First check that the training data has been initialised
        if not bool(self.training_data):
            self.logger.error("No training data has been loaded!")
            return

        self.models = {}
        self.scalers = {}
        self.feature_selectors = {}
        self.pca_transformers = {}
        
        # Identify the most important features across all gestures
        if self.feature_selection:
            self._perform_feature_selection()
        
        for gesture, sequences in self.training_data.items():
            self.logger.info(f"Training model for gesture: {gesture}")
            
            # Stack all sequences for this gesture
            X = np.vstack(sequences)
            lengths = [len(seq) for seq in sequences]
            
            # Scale the data
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            self.scalers[gesture] = scaler
            
            # Apply feature selection if enabled
            if self.feature_selection:
                X_scaled = self.feature_selectors[gesture].transform(X_scaled)
                self.logger.info(f"Selected {self.k_best_features} best features for {gesture}")
            
            # Apply PCA if enabled
            if self.use_pca:
                pca = PCA(n_components=min(self.pca_components, X_scaled.shape[1]))
                X_scaled = pca.fit_transform(X_scaled)
                self.pca_transformers[gesture] = pca
                explained_var = sum(pca.explained_variance_ratio_) * 100
                self.logger.info(f"PCA: {explained_var:.2f}% variance explained with {self.pca_components} components")

            # Define and train HMM
            model = hmm.GaussianHMM(
                n_components=self.n_components, 
                covariance_type=self.covariance_type,
                min_covar=1e-5,  # Lowered to allow more flexibility
                n_iter=self.n_iter,
                random_state=42
            )

            try:
                model.fit(X_scaled, lengths)
                self.models[gesture] = model
                self.logger.info(f"Successfully trained model for {gesture} with score: {model.score(X_scaled) / sum(lengths):.2f}")
            except Exception as e:
                self.logger.error(f"Failed to train model for {gesture}: {str(e)}")
    
    def _perform_feature_selection(self):
        """Identify the most important features for each gesture type"""
        for gesture, sequences in self.training_data.items():
            # Stack all sequences and create target variable
            # For feature selection, we'll use a simple approach: 
            # for each frame, the target is the time index normalized to [0,1]
            X = np.vstack(sequences)
            
            # Create target: normalized position in sequence
            y = []
            for seq_len in [len(seq) for seq in sequences]:
                y.extend(np.linspace(0, 1, seq_len))
            y = np.array(y)
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Select K best features
            selector = SelectKBest(mutual_info_regression, k=self.k_best_features)
            selector.fit(X_scaled, y)
            
            # Store the selector
            self.feature_selectors[gesture] = selector
            
            # Log selected features
            selected_indices = selector.get_support(indices=True)
            selected_features = [self.feature_keys[i] for i in selected_indices]
            self.logger.info(f"Selected features for {gesture}: {selected_features}")

    def eval(self):
        if not self.models:
            self.logger.error("No models have been trained!")
            return
            
        results = {gesture: {"correct": 0, "total": 0} for gesture in self.models}
        predictions = []
        actuals = []
        
        for test_label, sequences in self.test_data.items():
            for sequence in sequences:
                # Preprocess in the same way as during training
                X = sequence
                
                # Scale
                scaler = self.scalers[test_label]  # Use the same scaler for consistency
                X_scaled = scaler.transform(X)
                
                # Apply feature selection if enabled
                if self.feature_selection:
                    for gesture in self.models:
                        if gesture not in self.feature_selectors:
                            self.logger.error(f"No feature selector for {gesture}")
                            continue
                
                # Calculate score for each model
                scores = {}
                for label, model in self.models.items():
                    # Prepare data for this model (feature selection + PCA)
                    X_model = X_scaled.copy()
                    
                    if self.feature_selection:
                        X_model = self.feature_selectors[label].transform(X_model)
                    
                    if self.use_pca:
                        X_model = self.pca_transformers[label].transform(X_model)
                    
                    # Calculate score
                    scores[label] = model.score(X_model) / len(X_model)
                
                # Determine predicted label
                winner = max(scores, key=scores.get)
                
                # Update results
                results[test_label]["total"] += 1
                if winner == test_label:
                    results[test_label]["correct"] += 1
                
                predictions.append(winner)
                actuals.append(test_label)
        
        # Calculate overall accuracy
        total_correct = sum(results[g]["correct"] for g in results)
        total_samples = sum(results[g]["total"] for g in results)
        accuracy = (total_correct / total_samples) * 100 if total_samples > 0 else 0
        
        # Print detailed results
        self.logger.info(f"Overall accuracy: {accuracy:.2f}%")
        for gesture, result in results.items():
            if result["total"] > 0:
                gesture_accuracy = (result["correct"] / result["total"]) * 100
                self.logger.info(f"{gesture}: {gesture_accuracy:.2f}% ({result['correct']}/{result['total']})")
        
        # Confusion matrix (simplified)
        self.logger.info("Confusion matrix:")
        labels = sorted(list(self.models.keys()))
        confusion = {}
        for true_label in labels:
            confusion[true_label] = {}
            for pred_label in labels:
                confusion[true_label][pred_label] = 0
        
        for actual, pred in zip(actuals, predictions):
            confusion[actual][pred] += 1
        
        # Print confusion matrix
        header = "True\\Pred | " + " | ".join(labels)
        self.logger.info(header)
        for true_label in labels:
            row = f"{true_label:10s} | " + " | ".join(f"{confusion[true_label][pred]:6d}" for pred in labels)
            self.logger.info(row)
        
        return accuracy, confusion

    def save_models(self, path="models"):
        """Save the trained models and preprocessors"""
        import os
        if not os.path.exists(path):
            os.makedirs(path)
            
        for gesture, model in self.models.items():
            model_path = f"{path}/{gesture}_model.pkl"
            scaler_path = f"{path}/{gesture}_scaler.pkl"
            
            joblib.dump(model, model_path)
            joblib.dump(self.scalers[gesture], scaler_path)
            
            if self.feature_selection:
                selector_path = f"{path}/{gesture}_selector.pkl"
                joblib.dump(self.feature_selectors[gesture], selector_path)
                
            if self.use_pca:
                pca_path = f"{path}/{gesture}_pca.pkl"
                joblib.dump(self.pca_transformers[gesture], pca_path)
                
        self.logger.info(f"Models and preprocessors saved to {path}")
        
    def load_models(self, path="models"):
        """Load trained models and preprocessors"""
        import os
        if not os.path.exists(path):
            self.logger.error(f"Model path {path} does not exist")
            return False
            
        self.models = {}
        self.scalers = {}
        self.feature_selectors = {}
        self.pca_transformers = {}
        
        for gesture in ['takeoff', 'land', 'action_1', 'action_3']:
            model_path = f"{path}/{gesture}_model.pkl"
            scaler_path = f"{path}/{gesture}_scaler.pkl"
            
            if not os.path.exists(model_path) or not os.path.exists(scaler_path):
                self.logger.warning(f"Model or scaler for {gesture} not found")
                continue
                
            self.models[gesture] = joblib.load(model_path)
            self.scalers[gesture] = joblib.load(scaler_path)
            
            if self.feature_selection:
                selector_path = f"{path}/{gesture}_selector.pkl"
                if os.path.exists(selector_path):
                    self.feature_selectors[gesture] = joblib.load(selector_path)
                    
            if self.use_pca:
                pca_path = f"{path}/{gesture}_pca.pkl"
                if os.path.exists(pca_path):
                    self.pca_transformers[gesture] = joblib.load(pca_path)
                    
        self.logger.info(f"Loaded models for gestures: {list(self.models.keys())}")
        return len(self.models) > 0
        
    def predict(self, sequence):
        """Predict the gesture for a new sequence"""
        if not self.models:
            self.logger.error("No models have been trained!")
            return None
            
        # Preprocess
        if self.apply_smoothing:
            sequence = self._apply_smoothing(sequence)
            
        # Calculate score for each model
        scores = {}
        for label, model in self.models.items():
            # Scale with the model's scaler
            X_scaled = self.scalers[label].transform(sequence)
            
            # Apply feature selection if enabled
            if self.feature_selection:
                X_scaled = self.feature_selectors[label].transform(X_scaled)
            
            # Apply PCA if enabled
            if self.use_pca:
                X_scaled = self.pca_transformers[label].transform(X_scaled)
            
            # Calculate score
            scores[label] = model.score(X_scaled) / len(X_scaled)
        
        # Return prediction and confidence scores
        winner = max(scores, key=scores.get)
        return winner, scores

    def grid_search(self):
        """Perform grid search to find optimal hyperparameters"""
        if not self.training_data:
            self.logger.error("No training data loaded for grid search")
            return
            
        # Define parameter grid
        param_grid = {
            'n_components': [3, 5, 7, 9],
            'covariance_type': ['diag', 'full'],
            'use_pca': [True, False],
            'pca_components': [10, 15, 20] if self.use_pca else [None],
            'feature_selection': [True, False],
            'k_best_features': [15, 20, 25] if self.feature_selection else [None],
            'apply_smoothing': [True, False],
            'smoothing_window': [3, 5, 7] if self.apply_smoothing else [None]
        }
        
        best_accuracy = 0
        best_params = {}
        
        # Simplified grid search (not full cartesian product to save time)
        # We'll vary one parameter at a time
        base_params = {
            'n_components': 5,
            'covariance_type': 'diag',
            'use_pca': False,
            'pca_components': None,
            'feature_selection': True,
            'k_best_features': 20,
            'apply_smoothing': True,
            'smoothing_window': 5
        }
        
        for param_name, param_values in param_grid.items():
            self.logger.info(f"Grid searching parameter: {param_name}")
            
            for value in param_values:
                # Skip incompatible combinations
                if param_name == 'pca_components' and not base_params['use_pca']:
                    continue
                if param_name == 'k_best_features' and not base_params['feature_selection']:
                    continue
                if param_name == 'smoothing_window' and not base_params['apply_smoothing']:
                    continue
                
                # Set current parameter
                params = base_params.copy()
                params[param_name] = value
                
                # Configure model with these parameters
                self._configure_with_params(params)
                
                # Train and evaluate
                self.train()
                accuracy, _ = self.eval()
                
                self.logger.info(f"Parameter {param_name}={value}: Accuracy={accuracy:.2f}%")
                
                # Check if this is the best so far
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_params = params.copy()
        
        # Final training with best parameters
        self.logger.info(f"Best parameters found: {best_params} with accuracy {best_accuracy:.2f}%")
        self._configure_with_params(best_params)
        self.train()
        return best_params, best_accuracy
        
    def _configure_with_params(self, params):
        """Configure the model with given parameters"""
        for param, value in params.items():
            setattr(self, param, value)

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
