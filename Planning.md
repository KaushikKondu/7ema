Planning:

PHASE 1: 

1. What are building?
-- We are building a trading algo that is an ema based algo. The algo will be used to trade in NIFTY options.

2. What is the logic for the Algo?
-- The algo is simple and short. We observe the price on a 1hr TF to get the bias.
    If the 1hr is positive then we trade on the bullish side that is calls. 
    If the 1hr is negative then we trade on the bearish side that is puts.
    Now once the bias is determined the algo will make entries on a 15min TF. 
    
    Case 1: Call side trading
        Now if the current 15min candle is trading below 7ema then 
        we wait for a 15min candle closing above the 7 ema. Once the candle closes
        above 7 ema. We buy the ATM call option in Nifty with 1 lot. SL will be the 
        closing of any 15min candle below the 7 ema. 

    Case 2: Call side trading
        Now if the current 15min candle is trading above 7ema then we wait for a 
        pullback and if a 15min candle touches the 7ema and then closes positive 
        we make an entry after the closing of the candle. SL will be the 
        closing of any 15min candle below the 7 ema.

    Case 3: Put side trading
        Now if the current 15min candle is trading above 7ema then 
        we wait for a 15min candle closing below the 7 ema. Once the candle closes
        below 7 ema. We buy the ATM put option in Nifty with 1 lot. 
        SL will be the closing of any 15min candle above the 7 ema.

    Case 4: Put side trading
        Now if the current 15min candle is trading below 7ema then we wait for a 
        pullback and if a 15min candle touches the 7ema and then closes negative 
        we make an entry after the closing of the candle. SL will be the 
        closing of any 15min candle above the 7 ema.

3. How many trades per day? 
-- We will make a max of 3 trades per day. 

4. What broker will we be using?
-- We will be using Kite(zerodha) broker. 

5. How will we authenticate the broker?
-- We will be using the KiteConnect API for authentication along with totp. I've already
   added a auth.py to automate the login. Use that file to work with authentication.

6. How to calculate the ema. 
-- USE "talib" to calculate the ema. Use the max available data to calculate the ema and match the ema pricing to be accurate with the broker. I think more than 2000 candles should be sufficient?

7. Order should be MIS and be squared off at 3:15pm. 


PHASE 2:

1. create a venv to run the python code. 
2. Install the required libraries.
3. Add detailed logging for price calculations like 1HR candle OHLC when determining the bias, ema prices when entering and exiting a trade so that I can compare it with the broker. Include the timestamps of the candles.

PHASE 3:
1. Add a margin requirment check. If the margin is insufficient then don't place an order and log it as "Order not placed due to insufficient margin". Use the inbuilt KITE function. 
2. Whenever an order is placed, check the order status after 5 seconds and if the status is complete then it means the order has been placed successfully and we can proceed to the next step. If the status is rejected, then that means the order is rejected. Retry twice. If it is still rejected then Log "Max Retry reached" and stop the algo. 
3. For any failed order max retry is 2. If it fails after 2 times. Stop the entire algo for the day. 

PHASE 4:
1. Create a github workflow file for deploying the algo to aws instance. 
   Use my reference file. Make sure you change the instance timezone to IST through
   command line.
   