"""Coloured logging"""

import logging

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    
    class DummyFore:
        GREEN = YELLOW = RED = WHITE = CYAN = BLUE = MAGENTA = ""
    
    class DummyStyle:
        BRIGHT = RESET_ALL = ""
    
    Fore = DummyFore()
    Style = DummyStyle()


class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored console logs."""
    
    FORMATS = {
        logging.DEBUG: Fore.BLUE + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.INFO: Fore.WHITE + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.ERROR: Fore.RED + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

