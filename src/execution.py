import logging
import time
from auth.auth import kite
from src.config import LOT_SIZE

logger = logging.getLogger(__name__)

# Nifty Lot size is 65, so we multiply our LOT_SIZE parameter by 65
NIFTY_LOT_MULTIPLIER = 65

class AlgoStoppedException(Exception):
    """Exception raised to stop the entire algorithm for the day."""
    pass

def check_margin_sufficient(symbol: str, transaction_type: str, qty: int) -> bool:
    """Check if we have enough margin to place the order."""
    try:
        order_params = [{
            "exchange": kite.EXCHANGE_NFO,
            "tradingsymbol": symbol,
            "transaction_type": transaction_type,
            "variety": kite.VARIETY_REGULAR,
            "product": kite.PRODUCT_MIS,
            "order_type": kite.ORDER_TYPE_MARKET,
            "quantity": qty
        }]
        
        # Get required margin
        margin_details = kite.order_margins(order_params)
        required_margin = margin_details[0]['total']
        
        # Get available margin
        account_margins = kite.margins()
        # Use total cash available (live balance)
        available_margin = account_margins['equity']['available']['live_balance']
        
        logger.info(f"Margin Check - Required: {required_margin}, Available: {available_margin}")
        
        if available_margin >= required_margin:
            return True
        else:
            logger.error("Order not placed due to insufficient margin")
            return False
    except Exception as e:
        logger.error(f"Failed to check margin: {e}")
        # If margin check fails due to API issue, we might want to return False to be safe
        return False

def place_market_order(symbol: str, transaction_type: str, qty: int) -> bool:
    """Place a regular market order with margin check and retry logic."""
    if not check_margin_sufficient(symbol, transaction_type, qty):
        return False

    max_retries = 2
    attempts = 0

    while attempts <= max_retries:
        try:
            logger.info(f"Attempt {attempts + 1}: Placing {transaction_type} MARKET order for {qty} qty of {symbol}")
            
            order_id = kite.place_order(
                tradingsymbol=symbol,
                exchange=kite.EXCHANGE_NFO,
                transaction_type=transaction_type,
                quantity=qty,
                variety=kite.VARIETY_REGULAR,
                order_type=kite.ORDER_TYPE_MARKET,
                product=kite.PRODUCT_MIS,
                validity=kite.VALIDITY_DAY,
                market_protection="2"
            )
            logger.info(f"Order sent to broker! Order ID: {order_id}")
            
            # Wait 2 seconds before checking status
            time.sleep(2)
            
            # Check order status
            history = kite.order_history(order_id)
            latest_status = history[-1]['status']
            
            logger.info(f"Order Status after 2s: {latest_status}")
            
            if latest_status == 'COMPLETE':
                return True
            elif latest_status == 'REJECTED':
                logger.warning(f"Order was REJECTED by broker. Reason: {history[-1].get('status_message', 'Unknown')}")
                attempts += 1
                if attempts <= max_retries:
                    logger.info("Retrying...")
                    time.sleep(2) # Brief wait before retry
                else:
                    logger.error("Max Retry reached")
                    raise AlgoStoppedException("Stopping algo for the day due to max retries on rejected order.")
            else:
                logger.warning(f"Order status is {latest_status}. Not complete after 2 seconds.")
                return False
                
        except AlgoStoppedException:
            raise # Re-raise to be caught in main.py
        except Exception as e:
            logger.error(f"Error placing/checking order: {e}")
            attempts += 1
            if attempts > max_retries:
                logger.error("Max Retry reached due to exceptions")
                raise AlgoStoppedException("Stopping algo for the day due to API exceptions during order placement.")
            time.sleep(2)
            
    return False

def place_entry_order(symbol: str) -> int:
    """Place an entry BUY order. Returns the filled quantity."""
    qty = LOT_SIZE * NIFTY_LOT_MULTIPLIER
    success = place_market_order(symbol, kite.TRANSACTION_TYPE_BUY, qty)
    return qty if success else 0

def place_exit_order(symbol: str, qty: int) -> bool:
    """Place an exit SELL order."""
    return place_market_order(symbol, kite.TRANSACTION_TYPE_SELL, qty)
