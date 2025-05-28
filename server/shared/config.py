import os

class Config:
    # Load the configuration options from the .env file - note that the values
    # provided are FALLBACK values, i.e. so that some value is set if the env
    # variable has for some reason been missed.

    # Redis Configuration
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_UID_VARIABLE: str = os.getenv('REDIS_UID_VARIABLE', 'operator_uid')
    REDIS_RECORD_VARIABLE: str = os.getenv('REDIS_RECORD_VARIABLE', 'record_gesture')
    REDIS_DATA_VERSION_CHANNEL: str = os.getenv('REDIS_DATA_VERSION_CHANNEL', 'window_version')
    
    # Lume System Configuration
    LUME_RUN_MODE: str = os.getenv('LUME_RUN_MODE', 'deploy')  # default to deployment mode
    LUME_VERBOSE: bool = os.getenv('LUME_VERBOSE', 'false').lower() == 'true'
    LUME_UDP_PORT: int = int(os.getenv('LUME_UDP_PORT', '8888'))
    LUME_CONTROLLER_IP: str = os.getenv('LUME_CONTROLLER_IP', 'localhost')
    LUME_SENSOR_PAYLOAD_SIZE: int = int(os.getenv('LUME_SENSOR_PAYLOAD_SIZE', '49'))
    LUME_FFT_DATA_WINDOW_SIZE: int = int(os.getenv('LUME_FFT_DATA_WINDOW_SIZE', '1024'))
    LUME_DEPLOY_DATA_WINDOW_SIZE: int = int(os.getenv('LUME_DEPLOY_DATA_WINDOW_SIZE', '48'))
    LUME_SAMPLING_RATE: int = int(os.getenv('LUME_SAMPLING_RATE', '64'))
    
    # PostgreSQL Configuration
    PG_DB_NAME: str = os.getenv('PG_DB_NAME', 'defaultdb')
    PG_DB_HOST: str = os.getenv('PG_DB_HOST', 'localhost')
    PG_DB_USER: str = os.getenv('PG_DB_USER', 'postgres')
    PG_DB_PASS: str = os.getenv('PG_DB_PASS', 'password')
    PG_DB_PORT: int = int(os.getenv('PG_DB_PORT', '5432'))
    
    # Computed Properties using @property decorator
    @property
    def postgres_conn_string(self) -> str:
        """Generate PostgreSQL connection string"""
        return f"postgresql://{self.PG_DB_USER}:{self.PG_DB_PASS}@{self.PG_DB_HOST}:{self.PG_DB_PORT}/{self.PG_DB_NAME}"
    
    def get_redis_key(self, suffix: str) -> str:
        """Helper method to generate Redis keys with consistent naming"""
        return f"lume:{suffix}"
    
    def validate_config(self) -> bool:
        """Validate configuration values"""
        validations = [
            (self.LUME_SENSOR_PAYLOAD_SIZE > 0, "Sensor payload size must be positive"),
            (self.LUME_FFT_DATA_WINDOW_SIZE > 0, "FFT window size must be positive"),
            (self.LUME_DEPLOY_DATA_WINDOW_SIZE > 0, "Deploy window size must be positive"),
            (self.LUME_SAMPLING_RATE > 0, "Sampling rate must be positive"),
            (self.PG_DB_PORT > 0, "Database port must be positive"),
            (len(self.PG_DB_NAME.strip()) > 0, "Database name cannot be empty"),
            (len(self.PG_DB_USER.strip()) > 0, "Database user cannot be empty"),
        ]
        
        for is_valid, error_message in validations:
            if not is_valid:
                raise ValueError(f"Configuration error: {error_message}")
        
        return True

# Create a global config instance
config = Config()

# Validate configuration on import
config.validate_config()
