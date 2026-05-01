# Gulf Binance Arbitrage Bot: Technical Report

This report documents the implementation and operational flow of the arbitrage script logic.

## 1. Strategy Overview
The bot executes a **Triangular Arbitrage** strategy between three assets: **THB**, **USDT**, and **BTC**. It monitors price discrepancies between the direct `BTCTHB` market and the synthetic `BTCUSDT` + `USDTTHB` path.

### Signal 1: The "USDT-First" Path
**Logic:** BTC is cheaper via USDT than directly in THB.
**Sequence:**
1.  **THB → USDT**: Market Buy `USDTTHB` using THB.
2.  **USDT → BTC**: Market Buy `BTCUSDT` using the acquired USDT.
3.  **BTC → THB**: Market Sell `BTCTHB` to return to the base currency (THB).

### Signal -1: The "BTC-First" Path
**Logic:** BTC is cheaper directly in THB than via the USDT path.
**Sequence:**
1.  **THB → BTC**: Market Buy `BTCTHB` using THB.
2.  **BTC → USDT**: Market Sell `BTCUSDT` to acquire USDT.
3.  **USDT → THB**: Market Sell `USDTTHB` to return to the base currency (THB).

---

## 2. Core Logic & Calculations

### Trade Amount Identification
To prevent "Insufficient Balance" errors, the bot identifies the `Trade Amount` as follows:
*   **Safety Buffer**: It only uses **99%** of your available THB.
*   **Liquidity Matching**: It compares your safe balance against the available volume (Qty) on the order book and picks the **Minimum** of the two.
*   **Final Guard**: The trade only proceeds if the amount is at least **300 THB**.

### Signal Determination
The bot treats Signal 1 and Signal -1 independently:
*   **Signal 1**: Active if `(BTCUSDT Ask * USDTTHB Ask) - BTCTHB Bid > 0`.
*   **Signal -1**: Active if `BTCTHB Ask - (BTCUSDT Bid * USDTTHB Bid) > 0`.

### Profitability Gating (The "Actual Profit" Rule)
The bot calculates the **Actual Profit** based on the specific trade size rather than a whole BTC. 
*   **Formula**: `(Price Diff per BTC) * (Trade Amount / BTC Price)`
*   **Execution Rule**: A trade is only triggered if `Actual Profit > Estimated Fees` (currently set at 0.6% of trade volume).

---

## 3. Safety & Precision Mechanisms

### Fee Management
*   **1 USDT Reserve**: The bot consistently subtracts **1 USDT** from the available balance before any USDT-based trade. This ensures there is always enough USDT left over to cover the exchange's trading fees.
*   **Lot Size Rules**: Different markets have different precision requirements:
    *   **BTCUSDT (Buy)**: Uses 2 decimals for `quoteOrderQty`.
    *   **BTCTHB (Sell)**: Truncated to 5 decimals for `quantity`.
    *   **USDTTHB (Sell)**: Truncated to an **Integer** for `quantity`.

### Error Recovery
*   **Retry Logic**: If the API returns a `-2010 (Insufficient Balance)` error, the bot waits 3 seconds and retries the order up to 3 times.
*   **Early Exit**: If any step in a 3-part sequence fails, the bot immediately `returns` and stops the sequence to prevent "orphaned" balances in the wrong asset.

---

## 4. Live Dashboard (Display Status)
The script provides a real-time status update every 10 seconds:
*   **Filtering**: It hides raw API data (Quantities, Mid-prices) to show only actionable metrics.
*   **Formatting**: All monetary values are formatted to 2 decimal places for easy scanning.
*   **History**: It maintains a scrolling view of the last 15 attempts to track trends.

---

## 5. Summary of Recent Improvements
1.  **Redundancy Removal**: Removed double-deduction of fees by relying on the 1 USDT fixed reserve.
2.  **Signal Independence**: Linked Signal -1 to its own price difference calculation.
3.  **Truncation Consistency**: Standardized variable usage so console logs exactly match API payloads.

---

## 6. Project Challenges & Conclusion

### The Latency Problem
A critical issue was identified regarding the Gulf Binance execution flow: after buying **USDT** with **THB**, the exchange does not recognize the updated balance in real-time. There is a synchronization delay (approximately 1 second) before the received amount is available in the account. In high-frequency arbitrage where order book prices move every sub-second, waiting for this balance update makes the strategy unprofitable.

### Proposed Mitigation: Synchronous Execution
To address this, the plan was to maintain three assets (**THB**, **USDT**, and **BTC**) simultaneously. This would allow the bot to place market buy/sell orders synchronously across different pairs based on the calculated signal, rather than waiting for the output of one trade to fund the next.

### Final Status
After consideration, development of this bot has been paused. The potential profit after executing these strategies is not prominent when compared to other trading strategies, making further investment in this specific approach less favorable.
