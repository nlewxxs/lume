"""Database for storing training data"""

import psycopg2
import sys
import redis
import json
import time

from lume_logger import *
from config import ENV
from packer import unpack_binary

# define constants
USERS_TABLE = "users"
GESTURES_TABLE = "gestures"

# define globals
running = True


class TrainingDatabase:

    def __init__(self, user: str, redisconn: redis.client.Redis, verbose: bool = False) -> None:
        # Establish connection
        self.conn = psycopg2.connect(
            database=ENV["pg_db_name"],
            host=ENV["pg_db_host"],
            user=ENV["pg_db_user"],
            password=ENV["pg_db_pass"],
            port=ENV["pg_db_port"]
        )

        # Init cursor
        self.cursor = self.conn.cursor()

        # Initialise redis connection
        self.redisconn = redisconn

        # Setup coloured logging
        self._setup_colored_logging(verbose)
    
        # Check if the USERS table exists: 
        if not self.table_exists(USERS_TABLE):

            # Warn if not
            self.logger.info(f"{Fore.CYAN}USERS TABLE HAS NOT BEEN FOUND - CREATING NEW ONE.{Style.RESET_ALL}")

            # Create the table if not
            self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {USERS_TABLE}(
                id TEXT PRIMARY KEY
            )
            """)

        # Check if the user exists in the table. If they do not, create. 
        if not self.user_exists(user):
            self.logger.info(f"{Fore.CYAN}USER {user} DOES NOT EXIST. Creating new entry.{Style.RESET_ALL}")
            self.insert_user(user)

        # Check if the GESTURES table exists:
        if not self.table_exists(GESTURES_TABLE):
            # Warn if not
            self.logger.info(f"{Fore.CYAN}GESTURES TABLE HAS NOT BEEN FOUND - CREATING NEW ONE.{Style.RESET_ALL}")

            # Define the gestures enum type if it does not already exist
            self.cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'gesture_type') THEN
                    CREATE TYPE gesture_type AS ENUM ('takeoff', 'land', 'action_1', 'action_2', 'action_3');
                END IF;
            END $$
            """)

            # Create the table if not found
            self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {GESTURES_TABLE}(
                id SERIAL PRIMARY KEY,
                gesture gesture_type,
                user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                data JSONB
            )
            """)
        

    def table_exists(self, table_name: str) -> bool: 
        """Check if a table exists in the LUME database"""
        self.cursor.execute(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = '{table_name}'
        )
        """)
        return self.cursor.fetchone()[0]

    def user_exists(self, id: str) -> bool: 
        """Check if a user exists in the users table"""
        self.cursor.execute(f"SELECT 1 FROM {USERS_TABLE} WHERE id = '{id}' LIMIT 1")
        return self.cursor.fetchone() is not None

    def insert_user(self, id: str):
        """Insert a new user into the users table"""
        self.cursor.execute(f"INSERT INTO {USERS_TABLE} (id) VALUES ('{id}')")
        self.conn.commit()

    def insert_gesture(self, gesture: str, user_id: str, data):
        """Insert a new gesture into the gestures table"""
        try:
            self.cursor.execute(f"""
            INSERT INTO {GESTURES_TABLE} (gesture, user_id, data)
            VALUES ('{gesture}', '{user_id}', '{json.dumps(data)}') 
            """)
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Postgres error: {e}")
            self.conn.rollback()

    def flush_gesture(self, buffer, gesture):
        """Flush the current gesture stored into the training DB"""
        try:
            # Get the current user
            user = self.redisconn.get(ENV["redis_uid_variable"])
            user = user.decode('utf-8') if isinstance(user, bytes) else user
            self.insert_gesture(gesture, str(user), buffer)
            self.logger.info(f"Recorded {Fore.CYAN}{len(buffer)}{Style.RESET_ALL}" \
                            f" readings as gesture {Fore.CYAN}{gesture.upper()}{Style.RESET_ALL}" \
                            f" to database for user {Fore.CYAN}{user}{Style.RESET_ALL}")
        except Exception:
            self.logger.error("Failed to write gesture to training database")


    def run(self, gesture: str) -> None:
        # Listen on the sensors topic for data
        global running
        channel = 'sensors'
        sensors_subscription = self.redisconn.pubsub()
        sensors_subscription.subscribe(channel)

        self.logger.info(f"Listening for gestures on {channel}")

        buffer = []
        # Controlled by redis!!
        record_gesture = False

        try:
            while running:
                # Check if time to record a gesture (controlled by sockets.py)
                rg = self.redisconn.get(ENV['redis_record_variable'])
                record_gesture = (rg.decode('utf-8') if isinstance(rg, bytes) else rg) == '1'
                recording = False  # Used to only flush gesture once after finishing recording

                while record_gesture:
                    recording = True
                    # Update redis-held control variable
                    rg = self.redisconn.get(ENV['redis_record_variable'])
                    record_gesture = (rg.decode('utf-8') if isinstance(rg, bytes) else rg) == '1'

                    msg = sensors_subscription.get_message(ignore_subscribe_messages=True, timeout=0.1)

                    if msg:
                        data = unpack_binary(msg['data'])
                        buffer.append(data)

                if recording:
                    # Flush the data to the db when finished
                    self.flush_gesture(buffer, gesture)
                    buffer.clear()
                    recording = False

                time.sleep(0.05)

        except KeyboardInterrupt:
            logging.info("Shutting down gracefully...")
            running = False
        except redis.ConnectionError as e:
            logging.error(f"Redis conn error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
        finally:
            if buffer:
                self.flush_gesture(buffer, gesture)
    
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


    def __del__(self) -> None:
        # Close the database
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
