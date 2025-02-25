import redis
import sockets
import argparse

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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    redisconn = redis.Redis(host='localhost', port=6379, db=0)
    channel = 'sensors'
    print(type(redisconn))
    endpoint = sockets.UDPServer(port=args.port, redisconn=redisconn, \
                                 redis_channel=channel, verbose=args.verbose)
    endpoint.run(args.ip, args.polling_interval)
