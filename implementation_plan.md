# Nifty 7 EMA Options Trading Algo Implementation Plan

This document outlines the implementation plan for the NIFTY 7 EMA trading algorithm. The strategy trades NIFTY ATM options based on a 1-hour bias and 15-minute entry/exit conditions using a 7-period Exponential Moving Average (EMA).

## Problem Description
We need to build an automated trading algorithm using the Zerodha KiteConnect API. The algorithm must:
1. Determine bias using the 1-hour timeframe (Bullish/Bearish).
2. Execute trades on the 15-minute timeframe using 7 EMA crossovers and pullbacks.
3. Manage a maximum of 3 trades per day.
4. Execute trades in Nifty ATM Call or Put options.
5. Exit trades based on 15-minute candle closing relative to the 7 EMA.

## Proposed Phases

### Phase 1: Setup, Configuration & Auth
- **`src/config.py`**: Create a configuration module to store constants, file paths (`CREDENTIALS_FILE`, `TOKEN_FILE`), trading parameters (max trades = 3, lot size = 1), and logging settings.
- **`auth/auth.py`**: Integrate the provided authentication file.
- **Logging**: Implement centralized logging for trade tracking and debugging.

### Phase 2: Data Fetching and Indicator Calculation
- **`src/data.py`**:
    - Implement a function to fetch historical candle data (1-hour and 15-minute) for Nifty 50.
    - Implement EMA calculation using `talib` with >2000 candles to match broker precisely.
    - Implement a function to determine the day's bias based on the 1-hour chart.

### Phase 3: Instrument & Option Chain Utilities
- **`src/instruments.py`**:
    - Implement a utility to fetch the daily instrument list from Kite.
    - Implement a function to determine the ATM strike for Nifty.
    - Implement a function to find the exact trading symbol for the ATM Call/Put option for the current weekly expiry.

### Phase 4: Strategy & Trading Logic
- **`src/strategy.py`**:
    - **Bias determination**: Check if the 1-hour timeframe is positive or negative.
    - **Entry Conditions**:
        - Evaluate the 15-minute candle closes relative to the 7 EMA.
        - Handle the 4 specific entry cases (Call breakout, Call pullback, Put breakout, Put pullback).
    - **Exit Conditions (SL)**: Check if the 15-minute candle closes opposite to the trade direction relative to the 7 EMA.
    - State tracking for max trades (3 per day).

### Phase 5: Order Execution & Main Loop
- **`src/execution.py`**: Wrappers for placing Market Buy orders for entry and Market Sell orders for exit.
- **`main.py`**: The main orchestrator.
    - Run an event loop or schedule tasks.
    - At every 15-minute interval, update data, check for SL, and evaluate entry conditions.

## Implementation Details & Assumptions
Based on your feedback, here are the confirmed implementation details:
- **Data Fetching:** We will fetch at least 2000 historical candles to "warm up" the TA-Lib EMA calculation, ensuring it closely matches the broker's value.
- **Evaluation:** The logic will run exactly at the close of every 15-minute candle.
- **ATM Selection:** We will use the Nifty spot price rounded to the nearest 50 to find the ATM strike.

I have also made the following assumptions for the logic so we can proceed. Let me know if you want to change any of these:
1. **1hr Bias:** "Positive" means the 1-hour candle is green (Close > Open). "Negative" means red (Close < Open).
2. **Pullback Touch:** A candle "touches" the 7 EMA if its Low <= 7 EMA (for calls) or its High >= 7 EMA (for puts).
3. **Environment:** The script will run locally.

If these look good, we are ready to begin Phase 1 execution!

## Verification Plan

### Automated Tests
- Write simple unit tests for the EMA calculation to ensure it matches TradingView/Zerodha charts.
- Test the ATM strike calculation logic.

### Manual Verification
- Run the bot in "paper trading" or dry-run mode first, where it logs the buy/sell signals without actually firing orders to the Kite API.
- Verify that the 15-minute entry signals trigger exactly when the conditions are met according to the live chart.
