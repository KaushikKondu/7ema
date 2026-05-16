import pandas as pd
import logging
from auth.auth import kite

logger = logging.getLogger(__name__)

# Cache instruments globally to avoid fetching multiple times per day
_instruments_df = None

def get_instruments() -> pd.DataFrame:
    """Fetch and cache NFO instruments from Kite."""
    global _instruments_df
    if _instruments_df is None:
        logger.info("Fetching NFO instruments from Kite...")
        try:
            instruments = kite.instruments('NFO')
            _instruments_df = pd.DataFrame(instruments)
            # Ensure expiry is a datetime date object for sorting
            _instruments_df['expiry'] = pd.to_datetime(_instruments_df['expiry']).dt.date
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            return pd.DataFrame()
    return _instruments_df

def get_atm_strike(spot_price: float) -> int:
    """Calculate ATM strike by rounding Nifty spot price to nearest 50."""
    return int(round(spot_price / 50.0) * 50)

def get_option_symbol(spot_price: float, option_type: str) -> str:
    """
    Get the trading symbol for the current weekly expiry ATM option.
    option_type: 'CE' or 'PE'
    """
    atm_strike = get_atm_strike(spot_price)
    df = get_instruments()
    
    if df.empty:
        logger.error("Instruments data is empty.")
        return ""
        
    # Filter for NIFTY options at the ATM strike and matching type
    filtered = df[(df['name'] == 'NIFTY') & 
                  (df['strike'] == atm_strike) & 
                  (df['instrument_type'] == option_type)]
                  
    if filtered.empty:
        logger.error(f"No instruments found for NIFTY {atm_strike} {option_type}")
        return ""
        
    # Sort by expiry to get the closest (weekly) expiry
    filtered = filtered.sort_values(by='expiry')
    
    symbol = filtered.iloc[0]['tradingsymbol']
    logger.info(f"Resolved ATM {option_type} (Spot: {spot_price}, Strike: {atm_strike}) -> {symbol}")
    return symbol
