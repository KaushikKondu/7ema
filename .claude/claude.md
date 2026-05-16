# 7 EMA Nifty Options Trading Algo

## Project Context
This is an automated trading algorithm designed to trade Nifty options based on a 7-period Exponential Moving Average (EMA).

## Stack
- Python 3
- KiteConnect API (Zerodha)
- TA-Lib
- Pandas

## Architecture
- `main.py`: The entry point and main loop for the application.
- `src/config.py`: Configuration and global parameters.
- `src/data.py`: Fetches historical data and calculates indicators.
- `src/instruments.py`: Caches option chain and resolves ATM options.
- `src/strategy.py`: Defines the entry and exit logic, manages state.
- `src/execution.py`: Handles live MIS order execution, polling, and retry logic.
- `auth/auth.py`: Handles KiteConnect authentication.

## AI Assistant Instructions
1. Always review the code before finalizing.
2. Check for any edge cases and alert the user beforehand as the user might not be aware.
3. If you feel the user is overpositioned or taking too much risk in the algo, alert them with an example on why you feel the risk is too much.

