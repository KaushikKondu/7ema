import time
import logging
import datetime
import sys

from src.config import setup_logging
from auth.auth import authenticate
from src.strategy import TradingStrategy
from src.execution import place_entry_order, place_exit_order, AlgoStoppedException

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

def sleep_until_next_15m_close():
    """Calculate time until next 15m interval + 2 seconds and sleep."""
    now = datetime.datetime.now()
    
    # Calculate minutes to next 15m mark
    minutes_to_next = 15 - (now.minute % 15)
    
    next_run_time = now + datetime.timedelta(minutes=minutes_to_next)
    
    # If exactly at the mark, it might have calculated 15. We want 0 if it's already past the seconds
    if minutes_to_next == 15 and now.second > 2:
         # It's past the mark for this interval, wait 15 mins
         pass
    elif minutes_to_next == 15:
        # We are exactly at the mark, but haven't slept the 2 seconds
        next_run_time = now

    # Set seconds and microseconds to 0, then add 2 seconds delay to allow candle to close
    next_run_time = next_run_time.replace(second=2, microsecond=0)
    
    sleep_seconds = (next_run_time - now).total_seconds()
    
    # Edge case: if sleep_seconds is negative (e.g. we started at 09:15:05), wait for next interval
    if sleep_seconds < 0:
        next_run_time = next_run_time + datetime.timedelta(minutes=15)
        sleep_seconds = (next_run_time - now).total_seconds()
    
    logger.info(f"Sleeping for {sleep_seconds:.1f} seconds. Next evaluation at {next_run_time.strftime('%H:%M:%S')}")
    time.sleep(sleep_seconds)

def main():
    logger.info("Starting NIFTY 7 EMA Options Algo...")
    
    # 1. Authenticate
    if not authenticate():
        logger.error("Failed to authenticate with Kite. Exiting.")
        sys.exit(1)
        
    strategy = TradingStrategy()
    
    # 2. Main Loop
    while True:
        try:
            # Check if market is open (roughly 09:15 to 15:30 IST)
            # You might want to refine this for exact market hours or holiday checks
            now = datetime.datetime.now()
            current_time = now.time()
            market_start = datetime.time(9, 15)
            market_end = datetime.time(15, 30)
            
            # Simple weekend check (0 = Monday, 5 = Saturday, 6 = Sunday)
            if now.weekday() > 4:
                logger.info("Weekend. Market is closed. Come back on Monday.")
                sys.exit(0)
            
            if current_time < market_start or current_time > market_end:
                logger.info("Market is closed. Sleeping for 1 minute.")
                time.sleep(60)
                continue
            
            # Wait for the next 15m candle close
            sleep_until_next_15m_close()
            
            # Check for 3:15 PM Square Off
            now_after_sleep = datetime.datetime.now()
            if now_after_sleep.time() >= datetime.time(15, 15):
                logger.info("Time is 3:15 PM or later. Squaring off and stopping for the day.")
                if strategy.active_trade:
                    symbol = strategy.active_trade['symbol']
                    qty = strategy.active_trade['qty']
                    logger.info(f"Auto Square-Off active trade: {symbol}")
                    success = place_exit_order(symbol, qty)
                    if success:
                        strategy.record_trade_exit()
                
                # Sleep to avoid looping constantly at EOD
                time.sleep(60)
                continue

            # Evaluate strategy
            logger.info("Evaluating strategy...")
            signal = strategy.evaluate()
            
            if signal:
                action = signal['action']
                symbol = signal['symbol']
                
                if action == 'ENTRY':
                    qty = place_entry_order(symbol)
                    if qty > 0:
                        strategy.record_trade_entry(symbol, signal['type'], qty)
                        
                elif action == 'EXIT':
                    if strategy.active_trade:
                        success = place_exit_order(symbol, strategy.active_trade['qty'])
                        if success:
                            strategy.record_trade_exit()
            else:
                logger.info("No signal generated.")
                
        except AlgoStoppedException as e:
            logger.error(f"ALGO STOPPED: {e}")
            logger.info("Exiting the script.")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            # Sleep briefly to avoid tight error loops
            time.sleep(10)

if __name__ == "__main__":
    main()
