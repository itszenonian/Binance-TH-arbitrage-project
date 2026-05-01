import requests
import pandas as pd
from datetime import datetime
import time
import math
import os
import msvcrt # Built-in Windows library to detect key presses
import hmac
import hashlib
from urllib.parse import urlencode

# print(">>> PRESS 'q' or 's' ON YOUR KEYBOARD TO STOP <<<")
# 1st check balance amount of THB
# 2nd if THB balance <  (BTCTHB_price * BTCTHB_qty)  just use balance
# 3rd if THB balance >  (BTCTHB_price * BTCTHB_qty)  then just use  (BTCTHB_price * BTCTHB_qty) to trade
# if 1 = BTCUSD > BTCTHB -> market buy BTCUSD (ask price) -> market sell BTCTHB (bid price)
# % Note: Diff 1 = | (BTCUSD ask price x USDTTHB ask price) - BTCTHB bid price |
# if -1 = BTCUSD < BTCTHB -> market buy BTCTHB (ask price) -> market sell BTCUSD (bid price)
# % Note: Diff -1 = | BTCTHB ask price - (BTCUSD bid price x USDTTHB bid price) |

base_url = "https://api.binance.th"
endpoint = "/api/v1/ticker/bookTicker"
# Binance allows requesting multiple symbols at once by passing a JSON array string
symbols_to_request = '["BTCUSDT","BTCTHB","USDTTHB"]'

# Initialize a list to store data history (more efficient than growing a DataFrame inside a loop)
data_history = []

# API credentials
api_key = '341E7465A382B67AF6BD2C0402C30C71C1953ED8DFFFA36B900C38BCAADD2D76'
secret_key = '72B1EA6C67397D6C2B1D4653C09E27028832EDBD65748A2A571F8297969AA539'

headers = {
    'Accept': 'application/json',
    'X-MBX-APIKEY': api_key
}


# ============================================================
# HELPER FUNCTIONS (from API_sequence_order.py)
# ============================================================

def get_server_time():
    """Fetch server time to avoid timestamp errors."""
    server_time_url = base_url + "/api/v1/time"
    return requests.get(server_time_url).json()['serverTime']


def create_signature(params):
    """Generate HMAC-SHA256 signature for authenticated requests."""
    query_string = urlencode(params)
    signature = hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def get_account_data():
    """Call account data and return balances for THB, USDT, and BTC."""
    account_endpoint = "/api/v1/accountV2"
    full_url = base_url + account_endpoint

    params = {
        'timestamp': get_server_time()
    }
    params['signature'] = create_signature(params)

    response = requests.get(full_url, params=params, headers=headers)
    data = response.json()

    # Filter for THB, USDT, and BTC only
    target_assets = ['THB', 'USDT', 'BTC']
    balances = {}
    for balance in data.get('balances', []):
        if balance['asset'] in target_assets:
            balances[balance['asset']] = {
                'free': balance['free'],
                'locked': balance['locked']
            }

    return balances


def get_free_balance(asset_name):
    """Get free balance for a specific asset."""
    balances = get_account_data()
    return float(balances.get(asset_name, {}).get('free', 0))


def market_buy_usdt_with_thb(thb_amount):
    """Place a market BUY order on USDTTHB market using THB (quoteOrderQty)."""
    order_endpoint = "/api/v1/order"
    full_url = base_url + order_endpoint

    params = {
        'symbol': 'USDTTHB',
        'side': 'BUY',
        'type': 'MARKET',
        'quoteOrderQty': str(thb_amount),  # How much THB to spend
        'recvWindow': 10000,
        'timestamp': get_server_time()
    }
    params['signature'] = create_signature(params)

    print(f"\n[!] Placing BUY MARKET order for USDTTHB (quoteQty={thb_amount} THB)...")
    response = requests.post(full_url, params=params, headers=headers)
    resp_json = response.json()
    print(f"Response: {resp_json}")
    return resp_json


def market_buy_btc_with_usdt(usdt_amount):
    """Place a market BUY order on BTCUSDT market using USDT (quoteOrderQty)."""
    order_endpoint = "/api/v1/order"
    full_url = base_url + order_endpoint

    # Truncate USDT to 2 decimal places (floor, no rounding up)
    usdt_truncated = math.floor(usdt_amount * 100) / 100

    params = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'type': 'MARKET',
        'quoteOrderQty': f"{usdt_truncated:.2f}",  # USDT to spend (2 decimals)
        'recvWindow': 10000,
        'timestamp': get_server_time()
    }
    params['signature'] = create_signature(params)

    print(f"\n[!] Placing BUY MARKET order for BTCUSDT (quoteQty={usdt_truncated:.2f} USDT)...")
    response = requests.post(full_url, params=params, headers=headers)
    resp_json = response.json()
    print(f"Response: {resp_json}")
    return resp_json


def market_sell_btc_for_thb(btc_amount):
    """Place a market SELL order on BTCTHB market using BTC (quantity, 5 decimals)."""
    order_endpoint = "/api/v1/order"
    full_url = base_url + order_endpoint

    # Truncate BTC to 5 decimal places (floor, no rounding up)
    btc_truncated = math.floor(btc_amount * 100000) / 100000

    params = {
        'symbol': 'BTCTHB',
        'side': 'SELL',
        'type': 'MARKET',
        'quantity': f"{btc_truncated:.5f}",  # BTC quantity (5 decimals)
        'recvWindow': 10000,
        'timestamp': get_server_time()
    }
    params['signature'] = create_signature(params)

    print(f"\n[!] Placing SELL MARKET order for BTCTHB (qty={btc_truncated:.5f} BTC)...")
    response = requests.post(full_url, params=params, headers=headers)
    resp_json = response.json()
    print(f"Response: {resp_json}")
    return resp_json


def market_buy_btc_with_thb(thb_amount):
    """Place a market BUY order on BTCTHB market using THB (quoteOrderQty)."""
    order_endpoint = "/api/v1/order"
    full_url = base_url + order_endpoint

    params = {
        'symbol': 'BTCTHB',
        'side': 'BUY',
        'type': 'MARKET',
        'quoteOrderQty': str(int(thb_amount)),  # How much THB to spend
        'recvWindow': 10000,
        'timestamp': get_server_time()
    }
    params['signature'] = create_signature(params)

    print(f"\n[!] Placing BUY MARKET order for BTCTHB (quoteQty={int(thb_amount)} THB)...")
    response = requests.post(full_url, params=params, headers=headers)
    resp_json = response.json()
    print(f"Response: {resp_json}")
    return resp_json


def market_sell_btc_for_usdt(btc_amount):
    """Place a market SELL order on BTCUSDT market using BTC (quantity, 5 decimals)."""
    order_endpoint = "/api/v1/order"
    full_url = base_url + order_endpoint

    # Truncate BTC to 5 decimal places (floor, no rounding up)
    btc_truncated = math.floor(btc_amount * 100000) / 100000

    params = {
        'symbol': 'BTCUSDT',
        'side': 'SELL',
        'type': 'MARKET',
        'quantity': f"{btc_truncated:.5f}",  # BTC quantity (5 decimals)
        'recvWindow': 10000,
        'timestamp': get_server_time()
    }
    params['signature'] = create_signature(params)

    print(f"\n[!] Placing SELL MARKET order for BTCUSDT (qty={btc_truncated:.5f} BTC)...")
    response = requests.post(full_url, params=params, headers=headers)
    resp_json = response.json()
    print(f"Response: {resp_json}")
    return resp_json


def market_sell_usdt_for_thb(usdt_amount):
    """Place a market SELL order on USDTTHB market using USDT (quantity, integer)."""
    order_endpoint = "/api/v1/order"
    full_url = base_url + order_endpoint

    usdt_int = int(usdt_amount)

    params = {
        'symbol': 'USDTTHB',
        'side': 'SELL',
        'type': 'MARKET',
        'quantity': str(usdt_int),  # USDT to sell (integer)
        'recvWindow': 10000,
        'timestamp': get_server_time()
    }
    params['signature'] = create_signature(params)

    print(f"\n[!] Placing SELL MARKET order for USDTTHB (qty={usdt_int} USDT)...")
    response = requests.post(full_url, params=params, headers=headers)
    resp_json = response.json()
    print(f"Response: {resp_json}")
    return resp_json


def print_balances(balances, label=""):
    """Print formatted balances."""
    if label:
        print(f"\n--- {label} ---")
    for asset, info in balances.items():
        print(f"  {asset}: free = {info['free']}, locked = {info['locked']}")


# ============================================================
# SIGNAL 1 ORDER SEQUENCE: THB -> USDT -> BTC -> sell BTC for THB
# ============================================================

def execute_signal_1(trade_amount, usdtthb_ask, btcusdt_ask):
    """Execute the full order sequence for Signal 1.
    Sequence: Buy USDT with THB -> Buy BTC with USDT -> Sell BTC for THB
    """
    print("\n" + "=" * 60)
    print("SIGNAL 1 SEQUENCE: THB -> USDT -> BTC -> THB")
    print("=" * 60)

    # --- Step 1: Account Data (BEFORE) ---
    balances_before = get_account_data()
    print_balances(balances_before, "Step 1: Account Data (BEFORE)")

    # --- Step 2: Market BUY USDT with THB ---
    print(f"\n--- Step 2: Market BUY USDT with {int(trade_amount)} THB ---")
    usdt_resp = market_buy_usdt_with_thb(int(trade_amount))

    if not usdt_resp or 'code' in usdt_resp:
        print("Stopping sequence: BUY USDTTHB failed.")
        return

    # Wait for the order to settle
    time.sleep(3)

    # --- Step 3: Account Data (AFTER USDT buy) ---
    balances_after_usdt = get_account_data()
    print_balances(balances_after_usdt, "Step 3: Account Data (AFTER USDT buy)")

    usdt_free = float(balances_after_usdt.get('USDT', {}).get('free', 0))
    usdt_free = usdt_free - 1  # Reserve 1 USDT for fees
    print(f"  Available USDT to spend (after -1 fee reserve): {usdt_free}")

    if usdt_free < 1:
        print("Stopping sequence: USDT too low after fee reserve.")
        return

    # --- Step 4: Market BUY BTC with USDT (with retry for -2010) ---
    usdt_to_spend = usdt_free
    usdt_truncated = math.floor(usdt_to_spend * 100) / 100
    print(f"\n--- Step 4: Market BUY BTC with {usdt_truncated:.2f} USDT ---")

    btc_resp = None
    for attempt in range(1, 4):  # Up to 3 attempts
        btc_resp = market_buy_btc_with_usdt(usdt_to_spend)
        if btc_resp and btc_resp.get('code') == -2010:
            print(f"  ⚠️ -2010 Insufficient Balance (attempt {attempt}/3), waiting 3s and retrying...")
            time.sleep(3)
        else:
            break  # Success or different error, stop retrying

    if not btc_resp or 'code' in btc_resp:
        print("Stopping sequence: BUY BTCUSDT failed after retries.")
        return

    # Wait for the order to settle
    time.sleep(3)

    # --- Step 5: Account Data (AFTER BTC buy) ---
    balances_after_btc = get_account_data()
    print_balances(balances_after_btc, "Step 5: Account Data (AFTER BTC buy)")

    btc_free = float(balances_after_btc.get('BTC', {}).get('free', 0))
    print(f"  Available BTC to sell: {btc_free}")

    if btc_free <= 0:
        print("Stopping sequence: No BTC available to sell.")
        return

    # --- Step 6: Market SELL BTC for THB (5 decimal places) ---
    btc_truncated = math.floor(btc_free * 100000) / 100000
    print(f"\n--- Step 6: Market SELL {btc_truncated:.5f} BTC for THB ---")
    sell_resp = market_sell_btc_for_thb(btc_truncated)

    if not sell_resp or 'code' in sell_resp:
        print("Stopping sequence: SELL BTCTHB failed.")
        return

    # Wait for the order to settle
    time.sleep(3)

    # --- Step 7: Account Data (AFTER BTC sell) ---
    balances_final = get_account_data()
    print_balances(balances_final, "Step 7: Account Data (AFTER BTC sell)")

    print("\n✅ Signal 1 sequence completed.")


# ============================================================
# SIGNAL -1 ORDER SEQUENCE: THB -> BTC (BTCTHB) -> sell BTC for USDT -> sell USDT for THB
# ============================================================

def execute_signal_minus1(trade_amount, btcthb_ask):
    """Execute the full order sequence for Signal -1.
    Sequence: Buy BTC with THB (BTCTHB) -> Sell BTC for USDT -> Sell USDT for THB
    """
    print("\n" + "=" * 60)
    print("SIGNAL -1 SEQUENCE: THB -> BTC (BTCTHB) -> USDT -> THB")
    print("=" * 60)

    # --- Step 1: Account Data (BEFORE) ---
    balances_before = get_account_data()
    print_balances(balances_before, "Step 1: Account Data (BEFORE)")

    # --- Step 2: Market BUY BTC with THB (BTCTHB market) ---
    print(f"\n--- Step 2: Market BUY BTC with {int(trade_amount)} THB (BTCTHB market) ---")
    btc_buy_resp = market_buy_btc_with_thb(trade_amount)

    if not btc_buy_resp or 'code' in btc_buy_resp:
        print("Stopping sequence: BUY BTCTHB failed.")
        return

    # Wait for the order to settle
    time.sleep(3)

    # --- Step 3: Account Data (AFTER BTC buy) ---
    balances_after_btc = get_account_data()
    print_balances(balances_after_btc, "Step 3: Account Data (AFTER BTC buy)")

    btc_free = float(balances_after_btc.get('BTC', {}).get('free', 0))
    print(f"  Available BTC to sell: {btc_free}")

    if btc_free <= 0:
        print("Stopping sequence: No BTC available to sell.")
        return

    # --- Step 4: Market SELL BTC for USDT (5 decimal places) ---
    btc_truncated = math.floor(btc_free * 100000) / 100000
    print(f"\n--- Step 4: Market SELL {btc_truncated:.5f} BTC for USDT ---")
    btc_sell_resp = market_sell_btc_for_usdt(btc_truncated)

    if not btc_sell_resp or 'code' in btc_sell_resp:
        print("Stopping sequence: SELL BTCUSDT failed.")
        return

    # Wait for the order to settle
    time.sleep(3)

    # --- Step 5: Account Data (AFTER BTC sell) ---
    balances_after_sell = get_account_data()
    print_balances(balances_after_sell, "Step 5: Account Data (AFTER BTC sell)")

    usdt_free = float(balances_after_sell.get('USDT', {}).get('free', 0))
    usdt_free = usdt_free - 1  # Reserve 1 USDT for fees
    print(f"  Available USDT to sell (after -1 fee reserve): {usdt_free}")

    if usdt_free < 1:
        print("Stopping sequence: USDT too low after fee reserve.")
        return

    # --- Step 6: Market SELL USDT for THB (with retry for -2010) ---
    usdt_int = int(usdt_free)
    print(f"\n--- Step 6: Market SELL {usdt_int} USDT for THB ---")

    usdt_sell_resp = None
    for attempt in range(1, 4):  # Up to 3 attempts
        usdt_sell_resp = market_sell_usdt_for_thb(usdt_free)
        if usdt_sell_resp and usdt_sell_resp.get('code') == -2010:
            print(f"  ⚠️ -2010 Insufficient Balance (attempt {attempt}/3), waiting 3s and retrying...")
            time.sleep(3)
        else:
            break  # Success or different error, stop retrying

    if not usdt_sell_resp or 'code' in usdt_sell_resp:
        print("Stopping sequence: SELL USDTTHB failed after retries.")
        return

    # Wait for the order to settle
    time.sleep(3)

    # --- Step 7: Account Data (AFTER USDT sell) ---
    balances_final = get_account_data()
    print_balances(balances_final, "Step 7: Account Data (AFTER USDT sell)")

    print("\n✅ Signal -1 sequence completed.")


# ============================================================
# PRICE DATA FETCH
# ============================================================

def fetch_book_ticker():
    """Fetch best bid/ask for BTCUSDT, BTCTHB, USDTTHB."""
    response = requests.get(f"{base_url}{endpoint}", params={'symbols': symbols_to_request})
    return response.json()


def extract_prices(data):
    """Extract prices from bookTicker data into a dictionary."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_data = {'Time': current_time}

    for item in data:
        sym = item['symbol']
        if sym in ["BTCUSDT", "BTCTHB", "USDTTHB"]:
            row_data[f"{sym} Ask"] = float(item['askPrice'])
            row_data[f"{sym} Bid"] = float(item['bidPrice'])
            if sym == "BTCTHB":
                row_data[f"{sym} Ask Qty"] = float(item['askQty'])
                row_data[f"{sym} Bid Qty"] = float(item['bidQty'])

    return row_data


def calculate_signal(row_data):
    """Calculate arbitrage signal and diffs."""
    usdtthb_ask = row_data.get('USDTTHB Ask', 1)
    btcusdt_ask = row_data.get('BTCUSDT Ask', 0)
    btcthb_bid = row_data.get('BTCTHB Bid', 0)
    btcthb_ask = row_data.get('BTCTHB Ask', 0)
    btcusdt_bid = row_data.get('BTCUSDT Bid', 0)
    usdtthb_bid = row_data.get('USDTTHB Bid', 0)

    if usdtthb_ask > 0:
        btcusdt_in_thb = btcusdt_ask * usdtthb_ask
        diff_thb = btcusdt_in_thb - btcthb_bid
        row_data['Diff 1'] = abs(round(diff_thb, 2))

        diff_minus1 = btcthb_ask - (btcusdt_bid * usdtthb_bid)
        row_data['Diff -1'] = abs(round(diff_minus1, 2))

        if diff_thb > 0:
            row_data['Signal'] = 1
        elif diff_minus1 > 0:
            row_data['Signal'] = -1
        else:
            row_data['Signal'] = 0
    else:
        row_data['Signal'] = 0
        row_data['Diff 1'] = 0.0
        row_data['Diff -1'] = 0.0

    return row_data


def calculate_trade_params(row_data, thb_balance):
    """Calculate trade amount, fees, and related params."""
    btcthb_ask = row_data.get('BTCTHB Ask', 0)
    btcthb_ask_qty = row_data.get('BTCTHB Ask Qty', 0)
    btcthb_bid = row_data.get('BTCTHB Bid', 0)
    btcthb_bid_qty = row_data.get('BTCTHB Bid Qty', 0)

    row_data['THB Balance'] = thb_balance
    row_data['Buy amount for -1'] = btcthb_ask * btcthb_ask_qty
    row_data['Buy amount for 1'] = btcthb_bid * btcthb_bid_qty

    signal = row_data['Signal']
    buy_amount_1 = row_data.get('Buy amount for 1', 0)
    buy_amount_minus1 = row_data.get('Buy amount for -1', 0)

    # Logic for Trade Amount (using 99% of balance to avoid "Insufficient Balance" errors)
    trade_amount = 0.0
    safe_balance = thb_balance * 0.99

    if signal == 1:
        trade_amount = min(safe_balance, buy_amount_1)
    elif signal == -1:
        trade_amount = min(safe_balance, buy_amount_minus1)

    row_data['Trade Amount'] = int(trade_amount)
    row_data['Fees'] = round(trade_amount * 0.006, 2)

    # Scale per-BTC diff to actual trade size
    diff_1 = row_data.get('Diff 1', 0)
    diff_minus1 = row_data.get('Diff -1', 0)
    if btcthb_bid > 0:
        row_data['Actual Profit 1'] = round(diff_1 * (trade_amount / btcthb_bid), 2)
    else:
        row_data['Actual Profit 1'] = 0.0
    if btcthb_ask > 0:
        row_data['Actual Profit -1'] = round(diff_minus1 * (trade_amount / btcthb_ask), 2)
    else:
        row_data['Actual Profit -1'] = 0.0

    return row_data


def display_status(data_history, current_time):
    """Display current status with formatted DataFrame."""
    print(f"\n--- Status Update ({current_time}) | Total Records: {len(data_history)} ---")

    # Format a temporary DataFrame for clean printing of the last 15 rows
    temp_df = pd.DataFrame(data_history[-15:])

    # Hide specific columns from the display to make it cleaner
    cols_to_hide = [
        'BTCTHB Ask Qty', 'BTCTHB Bid Qty',
        'BTCUSDT Ask', 'BTCUSDT Bid',
        'USDTTHB Ask', 'USDTTHB Bid'
    ]
    temp_df_display = temp_df.drop(columns=[col for col in cols_to_hide if col in temp_df.columns])

    cols_to_format = [col for col in temp_df_display.columns if col not in ['Time', 'Trade Amount', 'Signal']]
    formatters = {col: '{:.2f}'.format for col in cols_to_format}
    print(temp_df_display.to_string(index=False, formatters=formatters))


# ============================================================
# MAIN LOOP
# ============================================================

try:
    while True:
        # Check if user pressed 'q' or 's' to stop
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
            if key in ['q', 's']:
                print("\n🛑 Stop button pressed! Exiting loop...")
                break

        # 1. Request the best bid and ask for multiple symbols
        data = fetch_book_ticker()

        # 2. Extract prices into a dictionary
        row_data = extract_prices(data)

        # 3. Get THB balance
        try:
            thb_balance = get_free_balance('THB')
        except Exception as e:
            print(f"Error fetching account data: {e}")
            thb_balance = 0.0

        # 4. Calculate Arbitrage Signal
        row_data = calculate_signal(row_data)

        # 5. Calculate trade parameters
        row_data = calculate_trade_params(row_data, thb_balance)

        # 6. Execute trades based on signal
        signal = row_data['Signal']
        trade_amount = row_data['Trade Amount']
        fees = row_data['Fees']
        diff_1 = row_data['Diff 1']
        diff_minus1 = row_data['Diff -1']

        btcusdt_ask = row_data.get('BTCUSDT Ask', 0)
        btcthb_ask = row_data.get('BTCTHB Ask', 0)
        usdtthb_ask = row_data.get('USDTTHB Ask', 1)

        actual_profit_1 = row_data.get('Actual Profit 1', 0)
        actual_profit_minus1 = row_data.get('Actual Profit -1', 0)

        if signal == 1:
            if actual_profit_1 > fees:
                if trade_amount >= 300:
                    if btcusdt_ask > 0 and usdtthb_ask > 0:
                        execute_signal_1(trade_amount, usdtthb_ask, btcusdt_ask)

        elif signal == -1:
            if actual_profit_minus1 > fees:
                if trade_amount >= 300:
                    if btcthb_ask > 0:
                        execute_signal_minus1(trade_amount, btcthb_ask)

        # 7. Save the row
        data_history.append(row_data)

        # 8. Display current status
        display_status(data_history, row_data['Time'])

        # 9. Wait for 10 seconds
        time.sleep(10)

except KeyboardInterrupt:
    print("\n🛑 Monitoring stopped by user.")
    df = pd.DataFrame(data_history)
    print(f"Final DataFrame created. Total rows: {len(df)}")
    # You can now access 'df' in your environment if running in a REPL/Notebook
