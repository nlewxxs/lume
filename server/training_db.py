"""Database for storing training data"""

import psycopg2
import sys
import redis

from lume_logger import *
from config import ENV

USERS_TABLE = "users"

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
    
        # Check if the table exists: 
        if not self.table_exists(USERS_TABLE):
            # Warn if not
            self.logger.info(f"{Fore.CYAN}USERS TABLE HAS NOT BEEN FOUND - CREATING NEW ONE." \
                    f" If you did not expect this then ensure the database is accessible.{Style.RESET_ALL}")

            # Create the table
            self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {USERS_TABLE}(
                id TEXT PRIMARY KEY
            )
            """)

        # Check if the user exists in the table. If they do not, create. 
        if not self.user_exists(user):
            self.logger.info(f"{Fore.CYAN}USER {user} DOES NOT EXIST. Creating new entry.{Style.RESET_ALL}")
            self.insert_user(user)

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
