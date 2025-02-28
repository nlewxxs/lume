import redis
import sockets
import argparse

from config import ENV

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Minimal UDP Server for binary float data exchange with Particle Photon 2"
    )
    parser.add_argument(
        "--ip", 
        required=True,
        help="IP address of the Particle Photon 2 device on WLAN"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8888,
        help="UDP port to use (default: 8888)"
    )
    parser.add_argument(
        "--polling-interval", 
        type=float, 
        default=5.0,
        help="Time in seconds between polling attempts (default: 5.0)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (debug) logging"
    )
    parser.add_argument(
        "--mode", 
        type=str, 
        required=True,
        default="deploy",
        help="Define the server runtime mode.  \
            Choose between < data > (for data collection) and < deploy > for \
            deployment mode. Default is 'deploy'."
    )
    parser.add_argument(
        "--user",
        type=int,
        default=0,
        help="Unique UID corresponding to the current user. Defaults to 0."
    )
    return parser.parse_args()


def set_env_vars(redisconn: redis.client.Redis, args):
    """Set the environmental variables needed to be stored in Redis"""
    # Mode in which the server is started
    redisconn.set(ENV['redis_mode_variable'], args.mode)
    # The current user
    redisconn.set(ENV['redis_uid_variable'], args.user)


if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()

    # Configure redis instance
    redisconn = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # Set the environmental variables in Redis
    set_env_vars(redisconn, args)

    # Startup an endpoint
    server = sockets.LumeServer(port=args.port, redisconn=redisconn, \
                                 config=ENV, verbose=args.verbose)
    # Run the server
    server.run(args.ip, args.polling_interval)
