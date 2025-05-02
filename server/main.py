from sys import implementation
import redis
import sockets
import post_processing
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import argparse
import threading

from hmm import LumeHMM
from training_db import TrainingDatabase
from config import ENV

ORANGE = "\033[38;5;208m"  # 208 is a nice orange
RESET = "\033[0m"  # ANSI reset escape sequence

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
        default=2.0,
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
            deployment mode, < training > for training the model, and < fft > \
            for performing an FFT signal analysis.  Default is 'deploy'."
    )
    return parser.parse_args()


def set_env_vars(redisconn: redis.client.Redis, args, shortcode: str):
    """Set the environmental variables needed to be stored in Redis"""
    # Mode in which the server is started
    redisconn.set(ENV['redis_mode_variable'], args.mode)
    # The current user
    redisconn.set(ENV['redis_uid_variable'], shortcode)


if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()

    # Configure redis instance
    redisconn = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

    # Request the current user's name
    name = input(f"{ORANGE}Please enter your imperial shortcode: {RESET}")
    # testing purposes: TODO remove
    shortcode = 'nl621' if name == "" else name 

    gesture = ""
    if args.mode == "data":
        gesture = input(f"{ORANGE}Please enter the gesture to record: {RESET}")

    # Set the environmental variables in Redis
    set_env_vars(redisconn, args, shortcode)

    # Startup a udp endpoint
    # endpoint = sockets.LumeServer(port=args.port, redisconn=redisconn, fft=(args.mode == "fft"), \
                                 # verbose=args.verbose)

    # Run the server
    # endpoint_thread = threading.Thread(target=endpoint.run, daemon=True, args=(args.ip, args.polling_interval))
    # endpoint_thread.start()

    db = None  # this will become the influx DB when deployed

    # OPTION 1 - Data collection mode
    if args.mode == "data":

        post_proc = post_processing.DataProcessor(redisconn=redisconn, fft=False, verbose=args.verbose)
        post_proc_thread = threading.Thread(target=post_proc.run, daemon=True)
        post_proc_thread.start()

        # Init the database
        db = TrainingDatabase(user=shortcode, redisconn=redisconn, verbose=args.verbose)
        db.run(gesture)

    elif args.mode == "fft":
        post_proc = post_processing.DataProcessor(redisconn=redisconn, fft=True, verbose=args.verbose)
        post_proc.run()

    elif args.mode == "train":
        hmm = LumeHMM(redisconn=redisconn, verbose=args.verbose)
        hmm.load_training_data()
        hmm.train()
        hmm.eval()
