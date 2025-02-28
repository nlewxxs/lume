"""
Some configuration values for the system
"""

ENV = {
    "redis_sensors_channel" : 'sensors',  # Topic to publish sensor data over
    "redis_mode_variable" : 'run_mode',  # Variable to dictate run mode
    "redis_uid_variable" : 'operator_uid',  # Variable to dictate current user ID
}
