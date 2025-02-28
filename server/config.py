"""
Some configuration values for the system
"""

ENV = {
    "redis_sensors_channel" : 'sensors',  # Topic to publish sensor data over
    "redis_mode_variable" : 'run_mode',  # Variable to dictate run mode
    "redis_uid_variable" : 'operator_uid',  # Variable to dictate current user ID
    "pg_db_name" : 'lume', 
    "pg_db_host" : '127.0.0.1', 
    "pg_db_user" : 'nl621',
    "pg_db_pass" : 'lume123',
    "pg_db_port" : 5432,
}
