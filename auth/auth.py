# =============================================================================
# auth/kite_auth.py — Kite Connect authentication
# Handles token caching, headless TOTP login, and exports a ready kite instance.
# All other modules import `kite` from here.
# =============================================================================

from __future__ import annotations

import json
import logging
import traceback
from urllib.parse import urlparse, parse_qs

import pyotp
import requests
from kiteconnect import KiteConnect

from src.config import CREDENTIALS_FILE, TOKEN_FILE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load credentials at module level (fail fast if file missing)
# ---------------------------------------------------------------------------
with open(CREDENTIALS_FILE, 'r') as _f:
    _credentials = json.load(_f)

user_id      = _credentials['CLIENT_ID']
_password    = _credentials['PASSWORD']
_totp_secret = _credentials['AUTH_SECRET']
api_key      = _credentials['API_KEY']
_api_secret  = _credentials['API_SECRET']

# KiteConnect instance — shared across the entire application
kite         = KiteConnect(api_key=api_key)
access_token: str | None = None


# ---------------------------------------------------------------------------
# Token file helpers
# ---------------------------------------------------------------------------
def read_token_file() -> str:
    """Read the cached access token from TOKEN_FILE. If missing, create empty and warn."""
    import os
    if not os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'w') as f:
            f.write('')
        import logging
        logging.warning(f"token.txt not found. Created empty file at {TOKEN_FILE}. Please fill in your token.")
    with open(TOKEN_FILE, 'r') as f:
        return f.read().strip()


def write_token_file(token: str) -> None:
    """Persist the access token to TOKEN_FILE."""
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)


# ---------------------------------------------------------------------------
# Fresh login via headless browser session
# ---------------------------------------------------------------------------
def setup_authentication() -> bool:
    """
    Perform a fresh Kite login using stored credentials + TOTP.
    Generates a new access token and caches it to TOKEN_FILE.
    Returns True on success, False on any failure.
    """
    global access_token

    # Generate TOTP fresh at login time (avoids 30-second window expiry)
    otp = pyotp.TOTP(_totp_secret).now()

    try:
        session = requests.Session()

        # Step 1: Password login
        logger.info('Auth Step 1: Password login...')
        resp = session.post(
            'https://kite.zerodha.com/api/login',
            {'user_id': user_id, 'password': _password}
        )
        request_id = resp.json()['data']['request_id']

        # Step 2: TOTP 2FA
        logger.info('Auth Step 2: Submitting TOTP...')
        session.post(
            'https://kite.zerodha.com/api/twofa',
            {'user_id': user_id, 'request_id': request_id, 'twofa_value': otp}
        )

        # Step 3: API session — follows redirect to kite.trade callback URL
        logger.info('Auth Step 3: Fetching API session...')
        api_session = session.get(
            f'https://kite.trade/connect/login?api_key={api_key}'
        )
        parsed      = urlparse(api_session.url)
        query_params = parse_qs(parsed.query)

        if 'request_token' not in query_params:
            logger.error('request_token not found in redirect URL. Check API key/secret.')
            return False

        request_token = query_params['request_token'][0]

        # Step 4: Exchange request_token for access_token
        logger.info('Auth Step 4: Generating access token...')
        session_data = kite.generate_session(request_token, api_secret=_api_secret)
        access_token = session_data['access_token']
        kite.set_access_token(access_token)
        write_token_file(access_token)

        logger.info(f'Authentication successful. Profile: {kite.profile()["user_name"]}')
        return True

    except Exception as e:
        logger.error(f'Authentication failed: {e}')
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# Cache-first authentication entry point
# ---------------------------------------------------------------------------
def authenticate() -> bool:
    """
    Try the cached token first; fall back to a fresh login if invalid.
    Sets the global `access_token` and configures the `kite` instance.
    Returns True if authenticated, False otherwise.
    """
    global access_token

    # Attempt to reuse cached token
    try:
        token = read_token_file()
        kite.set_access_token(token)
        profile = kite.profile()            # Raises exception if token is invalid/expired
        access_token = token
        logger.info(f'Reusing cached token. Welcome, {profile["user_name"]}.')
        return True
    except FileNotFoundError:
        logger.info(f'{TOKEN_FILE} not found — performing fresh login.')
    except Exception:
        logger.info('Cached token invalid or expired — performing fresh login.')

    # Fresh login
    return setup_authentication()
