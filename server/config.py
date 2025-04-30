"""
Some configuration values for the system
"""

ENV = {
    "redis_sensors_channels" : ['pitch', 'roll', 'yaw', 'd_pitch', 'd_roll',
                                'd_yaw', 'acc_x', 'acc_y', 'acc_z', 'gy_x',
                                'gy_y', 'gy_z', 'flex0', 'flex1', 'flex2'],
    "redis_mode_variable" : 'run_mode',  # Variable to dictate run mode
    "redis_uid_variable" : 'operator_uid',  # Variable to dictate current user ID
    "redis_record_variable" : 'record_gesture', 
    "redis_data_version_channel" : "window_version",
    "gesture_dict" : {'takeoff' : 0, 'land' : 1, 'action_1' : 2, 'action_2' : 3, 'action_3' : 4}, 
    "payload_size" : 49,  # sensor payload size in bytes
# Number of data points in one 'window' of data (used for sliding-window data proc)
    "fft_data_window_size" : 1024,
    "normal_data_window_size" : 48,
    "sampling_rate" : 64, 
    "pg_db_name" : 'lume', 
    "pg_db_host" : '127.0.0.1', 
    "pg_db_user" : 'nl621',
    "pg_db_pass" : 'lume123',
    "pg_db_port" : 5432,
}
