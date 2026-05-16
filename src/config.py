import os
import logging

# Directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_DIR = os.path.join(BASE_DIR, 'auth')

# Paths for auth files
CREDENTIALS_FILE = os.path.join(AUTH_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(AUTH_DIR, 'token.txt')

# Trading parameters
MAX_TRADES_PER_DAY = 3
LOT_SIZE = 1 # Nifty option lot size (1 lot = 25 qty usually, but here we specify lot count)
EMA_PERIOD = 7
WARMUP_CANDLES = 2000 # Number of candles to fetch for EMA warmup
NIFTY_50_TOKEN = 256265 # Zerodha Instrument Token for NIFTY 50 Spot

# Logging configuration
LOG_FILE = os.path.join(BASE_DIR, 'trading.log')

def setup_logging():
    """Setup centralized logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
