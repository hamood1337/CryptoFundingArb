# Crypto Arbitrage Scanner
Scans Hyperliquid, Binance, Bybit, KuCoin, Kraken, and OKX for funding rate arbitrage opportunities. Returns potential arbitrage opportunities and visualizes the results.

## Features

- Sequential data fetching from multiple exchanges to avoid rate limiting issues
- Automatic handling of rate limiting and retries
- Calculation of annualized funding rates and arbitrage opportunities
- Visualization of top arbitrage opportunities
- Command-line interface for easy customization

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/hamood1337/CryptoFundingArb.git
   cd CryptoFundingArb
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script with default parameters:

```
python main.py
```

Customize the minimum spread and number of top opportunities:

```
python main.py --min_spread 2.0 --top_n 15
```

## Sample Output

```
Top Arbitrage Opportunities:
+--------+-----------------+------------------+--------+
| symbol | long_exchange   | short_exchange   | spread |
+--------+-----------------+------------------+--------+
| BTC    | binanceusdm     | krakenfutures    |   2.35 |
| ETH    | okx             | bybit            |   1.98 |
| ...    | ...             | ...              |   ...  |
+--------+-----------------+------------------+--------+
```

## How It Works

1. The script fetches ticker data from each supported exchange sequentially.
2. It then fetches funding rate data for each symbol from each exchange.
3. The funding rates are used to calculate potential arbitrage opportunities between exchanges.
4. The top opportunities are displayed in the console and visualized in a bar chart.

## Supported Exchanges

- Binance USDM Futures
- KuCoin Futures
- OKX
- Bybit
- Kraken Futures
- Hyperliquid

## Notes

- This script uses sequential data fetching to avoid rate limiting issues, particularly with exchanges like Hyperliquid.
- There's a small delay between requests to different exchanges to further mitigate rate limiting problems.
- The script may take longer to run compared to concurrent implementations, but it should be more reliable in terms of not exceeding rate limits.


## To Do List
- Filter out low volume tickers
- Take into account maker/taker fees on different exchanges
- SPEED
- Backtesting
- Enter/exit strategy based on bollinger bands

## Credits
Huge credits goes to [TheQuantStack](https://www.algos.org/) and [HangukQuant](https://hangukquant.com/) for invaluable information, tips, tricks, code snippets, and advice. Highly recommend their resources for anything looking to gain a better understanding of the quant world.


## Disclaimer

This tool is for educational and informational purposes only. It is not financial advice. Always do your own research before making any investment decisions. The authors are not responsible for any financial losses incurred from using this tool.