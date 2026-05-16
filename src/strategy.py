import logging
import datetime
from typing import Dict, Any, Optional

from src.config import MAX_TRADES_PER_DAY, NIFTY_50_TOKEN, WARMUP_CANDLES
from src.data import fetch_historical_data, calculate_ema, get_1hr_bias
from src.instruments import get_option_symbol

logger = logging.getLogger(__name__)

class TradingStrategy:
    def __init__(self):
        self.trades_today = 0
        self.last_trade_date = None
        self.active_trade: Optional[Dict[str, Any]] = None

    def reset_daily_counts(self):
        """Reset trade count on a new day."""
        today = datetime.datetime.now().date()
        if self.last_trade_date != today:
            self.trades_today = 0
            self.last_trade_date = today

    def evaluate(self) -> Optional[Dict[str, Any]]:
        """
        Evaluate market conditions to generate entry or exit signals.
        Returns a dictionary with signal details or None.
        """
        self.reset_daily_counts()
        
        # 1. Fetch 15min data and calculate EMA
        df_15m = fetch_historical_data(NIFTY_50_TOKEN, '15minute', WARMUP_CANDLES)
        if df_15m.empty:
            logger.error("Could not fetch 15m data for evaluation.")
            return None
            
        df_15m = calculate_ema(df_15m)
        
        if len(df_15m) < 2:
            logger.warning("Not enough 15m data to evaluate.")
            return None
            
        prev_candle = df_15m.iloc[-2]
        curr_candle = df_15m.iloc[-1] # The one that just closed
        
        # 2. Check Stop Loss if we have an active trade
        if self.active_trade:
            trade_type = self.active_trade['type']
            if trade_type == 'CE' and curr_candle['close'] < curr_candle['ema']:
                logger.info(f"[EXIT - SL HIT] Call Option! Time: {curr_candle.name}, Close: {curr_candle['close']:.2f} < EMA: {curr_candle['ema']:.2f}")
                return self._generate_exit_signal()
                
            elif trade_type == 'PE' and curr_candle['close'] > curr_candle['ema']:
                logger.info(f"[EXIT - SL HIT] Put Option! Time: {curr_candle.name}, Close: {curr_candle['close']:.2f} > EMA: {curr_candle['ema']:.2f}")
                return self._generate_exit_signal()
                
            # If SL not hit, we continue holding
            return None
            
        # 3. Check for Entry if we don't have an active trade
        if self.trades_today >= MAX_TRADES_PER_DAY:
            logger.info("Max trades per day reached. Not taking new entries.")
            return None
            
        bias = get_1hr_bias()
        
        signal = None
        if bias == 'BULLISH':
            # Case 1: Call side breakout
            if prev_candle['close'] < prev_candle['ema'] and curr_candle['close'] > curr_candle['ema']:
                logger.info(f"[ENTRY - Call Breakout] Time: {curr_candle.name}, Close: {curr_candle['close']:.2f} > EMA: {curr_candle['ema']:.2f}")
                signal = 'CE'
                
            # Case 2: Call side pullback
            elif prev_candle['close'] > prev_candle['ema']:
                # Touches EMA and closes positive
                if curr_candle['low'] <= curr_candle['ema'] and curr_candle['close'] > curr_candle['open']:
                    # Optional: ensure it still closes above EMA
                    if curr_candle['close'] > curr_candle['ema']:
                        logger.info(f"[ENTRY - Call Pullback] Time: {curr_candle.name}, Low: {curr_candle['low']:.2f} <= EMA: {curr_candle['ema']:.2f}, Close: {curr_candle['close']:.2f} > Open: {curr_candle['open']:.2f}")
                        signal = 'CE'
                    
        elif bias == 'BEARISH':
            # Case 3: Put side breakout
            if prev_candle['close'] > prev_candle['ema'] and curr_candle['close'] < curr_candle['ema']:
                logger.info(f"[ENTRY - Put Breakout] Time: {curr_candle.name}, Close: {curr_candle['close']:.2f} < EMA: {curr_candle['ema']:.2f}")
                signal = 'PE'
                
            # Case 4: Put side pullback
            elif prev_candle['close'] < prev_candle['ema']:
                # Touches EMA and closes negative
                if curr_candle['high'] >= curr_candle['ema'] and curr_candle['close'] < curr_candle['open']:
                    # Optional: ensure it still closes below EMA
                    if curr_candle['close'] < curr_candle['ema']:
                        logger.info(f"[ENTRY - Put Pullback] Time: {curr_candle.name}, High: {curr_candle['high']:.2f} >= EMA: {curr_candle['ema']:.2f}, Close: {curr_candle['close']:.2f} < Open: {curr_candle['open']:.2f}")
                        signal = 'PE'
                    
        if signal:
            # We need the current spot price to find ATM
            spot_price = curr_candle['close']
            symbol = get_option_symbol(spot_price, signal)
            if symbol:
                logger.info(f"Generated ENTRY signal for {symbol} ({signal})")
                return {
                    'action': 'ENTRY',
                    'type': signal,
                    'symbol': symbol,
                    'spot': spot_price
                }
                
        return None
        
    def _generate_exit_signal(self) -> Dict[str, Any]:
        signal = {
            'action': 'EXIT',
            'type': self.active_trade['type'],
            'symbol': self.active_trade['symbol']
        }
        return signal

    def record_trade_entry(self, symbol: str, option_type: str, qty: int):
        """Called by execution logic once the order is successfully placed."""
        self.active_trade = {
            'symbol': symbol,
            'type': option_type,
            'qty': qty
        }
        self.trades_today += 1
        logger.info(f"Recorded new trade. Total trades today: {self.trades_today}")
        
    def record_trade_exit(self):
        """Called by execution logic once the exit order is successfully placed."""
        if self.active_trade:
            logger.info(f"Recorded trade exit for {self.active_trade['symbol']}")
            self.active_trade = None
