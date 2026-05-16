import datetime
import pandas as pd
import talib
import logging
from auth.auth import kite
from src.config import EMA_PERIOD, WARMUP_CANDLES, NIFTY_50_TOKEN

logger = logging.getLogger(__name__)

def fetch_historical_data(instrument_token: int, interval: str, candles: int) -> pd.DataFrame:
    """
    Fetch historical data from Kite API for a given interval.
    Intervals: 'minute', '3minute', '5minute', '10minute', '15minute', '30minute', '60minute', 'day'
    """
    # Calculate how many days we need based on interval
    if interval == '15minute':
        days_needed = (candles // 25) + 10  # 25 candles per day approx
    elif interval == '60minute':
        days_needed = (candles // 7) + 20   # 7 candles per day approx
    else:
        days_needed = candles
        
    to_date = datetime.datetime.now()
    from_date = to_date - datetime.timedelta(days=int(days_needed * 1.5)) # x1.5 to account for weekends/holidays

    logger.info(f"Fetching {interval} data for token {instrument_token} from {from_date.date()} to {to_date.date()}")
    try:
        records = kite.historical_data(instrument_token, from_date, to_date, interval)
        if not records:
            logger.error("No historical data fetched.")
            return pd.DataFrame()
            
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Keep only the requested number of candles from the end
        return df.tail(candles)
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

def calculate_ema(df: pd.DataFrame, period: int = EMA_PERIOD) -> pd.DataFrame:
    """Calculate EMA using TA-Lib and append to DataFrame."""
    if len(df) < period:
        logger.warning("Not enough data to calculate EMA")
        df['ema'] = None
        return df
        
    df['ema'] = talib.EMA(df['close'], timeperiod=period)
    return df

def get_1hr_bias() -> str:
    """
    Determine the bias from the 1-hour timeframe.
    Returns 'BULLISH' if the latest 1hr candle is green (close > open).
    Returns 'BEARISH' if the latest 1hr candle is red (close < open).
    Returns 'NEUTRAL' otherwise.
    """
    df_1h = fetch_historical_data(NIFTY_50_TOKEN, '60minute', WARMUP_CANDLES)
    if df_1h.empty:
        return 'NEUTRAL'
        
    # Calculate EMA (even if not strictly used for bias based on user clarification, 
    # it's good to have it on the 1hr df for logging or future changes)
    df_1h = calculate_ema(df_1h, EMA_PERIOD)
    
    # We use the most recently closed 1hr candle
    # If running at exactly e.g. 10:15, the 09:15 candle might still be the last full candle
    latest_candle = df_1h.iloc[-1]
    
    timestamp = latest_candle.name
    open_price = latest_candle['open']
    high_price = latest_candle['high']
    low_price = latest_candle['low']
    close_price = latest_candle['close']
    
    logger.info(f"[1HR Candle] Timestamp: {timestamp}, O: {open_price}, H: {high_price}, L: {low_price}, C: {close_price}")
    
    if close_price > open_price:
        logger.info("1hr Bias is BULLISH")
        return 'BULLISH'
    elif close_price < open_price:
        logger.info("1hr Bias is BEARISH")
        return 'BEARISH'
    else:
        logger.info("1hr Bias is NEUTRAL")
        return 'NEUTRAL'
