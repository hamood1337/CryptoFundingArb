import ccxt
import pandas as pd
import numpy as np
from tqdm import tqdm
import time
import random
import logging
import argparse
from tabulate import tabulate
import matplotlib.pyplot as plt
import seaborn as sns

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# List of exchanges to scan
EXCHANGES = ["binanceusdm", "kucoinfutures", "okx", "bybit", "krakenfutures", "hyperliquid"]

def fetch_tickers(exchange_id):
    """
    Fetch tickers for a given exchange.
    
    Args:
        exchange_id (str): The ID of the exchange to fetch tickers from.
        
    Returns:
        list: A list of ticker symbols for the given exchange.
    """
    exchange_client = getattr(ccxt, exchange_id)()
    
    if exchange_id == "krakenfutures":
        x = exchange_client.fetchTickers()
        return [y for y in x.keys() if y.split(":")[0][-4:] == "/USD"]
    elif exchange_id == "kucoinfutures":
        x = exchange_client.fetchMarkets()
        return [x['symbol'] for x in x if x['symbol'][-5:] == ":USDT"]
    elif exchange_id in ["okx", "gate"]:
        x = exchange_client.fetchTickers()
        return [y for y in x.keys() if y[-5:] == "/USDT"]
    elif exchange_id in ["bybit", "binanceusdm"]:
        x = exchange_client.fetchTickers()
        return [y for y in x.keys() if y[-5:] == ":USDT"]
    elif exchange_id == "hyperliquid":
        x = exchange_client.fetchMarkets()
        return [market['symbol'] for market in x if market['quote'] == 'USDC']

def fetch_funding_rate_with_retry(client, raw_symbol, exchange_id, max_retries=5, initial_delay=1):
    """
    Fetch funding rate with retry mechanism for rate limiting.
    
    Args:
        client (ccxt.Exchange): The exchange client.
        raw_symbol (str): The raw symbol to fetch funding rate for.
        exchange_id (str): The ID of the exchange.
        max_retries (int): Maximum number of retries.
        initial_delay (float): Initial delay between retries in seconds.
        
    Returns:
        list: A list of funding rate data.
    """
    for attempt in range(max_retries):
        try:
            if exchange_id == "hyperliquid":
                return client.fetchFundingRateHistory(raw_symbol, limit=2)
            else:
                return client.fetch_funding_rate_history(raw_symbol, limit=2)
        except ccxt.RateLimitExceeded as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Rate limit exceeded for {exchange_id}, retrying in {delay:.2f} seconds...")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Error fetching {raw_symbol} on {exchange_id}: {str(e)}")
            return []

def fetch_funding_rates(exchange_id, symbol_map):
    """
    Fetch funding rates for all symbols on a given exchange.
    
    Args:
        exchange_id (str): The ID of the exchange.
        symbol_map (dict): A mapping of normalized symbols to raw symbols for each exchange.
        
    Returns:
        list: A list of funding rate data for all symbols on the exchange.
    """
    client = getattr(ccxt, exchange_id)({"options":{'defaultType': 'swap'}})
    data = []
    
    for symbol, norm_to_raw in symbol_map.items():
        if exchange_id in norm_to_raw:
            raw_symbol = norm_to_raw[exchange_id]
            if exchange_id == "okx":
                raw_symbol = raw_symbol.replace("/", "-") + "-SWAP"
            
            try:
                rates = fetch_funding_rate_with_retry(client, raw_symbol, exchange_id)
                for r in rates:
                    r['exchange'] = exchange_id
                    r['norm_symbol'] = symbol
                    data.append(r)
            except Exception as e:
                logger.error(f"Error fetching {symbol} on {exchange_id}: {str(e)}")
    
    return data

def calculate_arbitrage_opportunities(data):
    """
    Calculate arbitrage opportunities from funding rate data.
    
    Args:
        data (pd.DataFrame): Funding rate data for all exchanges and symbols.
        
    Returns:
        pd.DataFrame: A DataFrame of arbitrage opportunities.
    """
    spreads = []
    for symbol, group in data.groupby('norm_symbol'):
        if len(group) < 2:
            continue
        for i, row1 in group.iterrows():
            for j, row2 in group.iterrows():
                if i < j:
                    spread = abs(row1['pctAnnualFundingRate'] - row2['pctAnnualFundingRate'])
                    spreads.append({
                        'symbol': symbol,
                        'exchange1': row1['exchange'],
                        'exchange2': row2['exchange'],
                        'rate1': row1['pctAnnualFundingRate'],
                        'rate2': row2['pctAnnualFundingRate'],
                        'spread': spread
                    })

    spreads_df = pd.DataFrame(spreads)
    opportunities = spreads_df[spreads_df['spread'] > 1.0]

    opportunities['long_exchange'] = opportunities.apply(lambda row: row['exchange1'] if row['rate1'] < row['rate2'] else row['exchange2'], axis=1)
    opportunities['short_exchange'] = opportunities.apply(lambda row: row['exchange2'] if row['rate1'] < row['rate2'] else row['exchange1'], axis=1)

    return opportunities.sort_values('spread', ascending=False)

def visualize_opportunities(opportunities, top_n=10):
    """
    Visualize top arbitrage opportunities.
    
    Args:
        opportunities (pd.DataFrame): DataFrame of arbitrage opportunities.
        top_n (int): Number of top opportunities to visualize.
    """
    top_opportunities = opportunities.head(top_n)
    
    plt.figure(figsize=(12, 6))
    sns.barplot(x='symbol', y='spread', data=top_opportunities)
    plt.title(f'Top {top_n} Arbitrage Opportunities')
    plt.xlabel('Symbol')
    plt.ylabel('Spread (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('arbitrage_opportunities.png')
    logger.info("Visualization saved as 'arbitrage_opportunities.png'")

def main(min_spread=1.0, top_n=10):
    logger.info("Starting Crypto Arbitrage Scanner")
    
    # Fetch tickers sequentially
    all_tickers = {}
    for exchange_id in tqdm(EXCHANGES, desc="Fetching tickers"):
        all_tickers[exchange_id] = fetch_tickers(exchange_id)
        time.sleep(1)  # Add a small delay between exchanges

    # Process tickers
    unique_tickers = {}
    for tickers in all_tickers.values():
        for ticker in tickers:
            ticker = ticker.split("/")[0]
            unique_tickers[ticker] = unique_tickers.get(ticker, 0) + 1

    symbols = [ticker for ticker, count in unique_tickers.items() if count == len(EXCHANGES)]

    # Create symbol map
    symbol_map = {symbol: {exchange_id: next((tick for tick in all_tickers[exchange_id] if tick.split("/")[0] == symbol), None) 
                           for exchange_id in EXCHANGES} 
                  for symbol in symbols}

    logger.info(f'Assets found: {len(symbols)}')

    # Fetch funding rates sequentially
    all_data = []
    for exchange_id in tqdm(EXCHANGES, desc="Fetching funding rates"):
        all_data.extend(fetch_funding_rates(exchange_id, symbol_map))
        time.sleep(1)  # Add a small delay between exchanges

    # Process data
    data = pd.DataFrame(all_data)
    data = data.drop('info', axis=1, errors='ignore')
    data = data.sort_values(['exchange', 'norm_symbol', 'timestamp'])

    # Calculate intervals
    data['interval_hours'] = data.groupby(['exchange', 'norm_symbol'])['timestamp'].diff() / (1000 * 60 * 60)
    data['interval_hours'] = data['interval_hours'].fillna(0).round()

    # Keep only the latest data for each exchange and symbol
    data = data.groupby(['exchange', 'norm_symbol']).last().reset_index()

    # Calculate rates
    data['annual_adj_mult'] = 365 * 24 / data['interval_hours'].replace(0, 24)
    data['annualFundingRate'] = data['fundingRate'] * data['annual_adj_mult']
    data['pctAnnualFundingRate'] = data['annualFundingRate'] * 100

    # Calculate arbitrage opportunities
    opportunities = calculate_arbitrage_opportunities(data)
    
    # Filter opportunities based on minimum spread
    filtered_opportunities = opportunities[opportunities['spread'] >= min_spread]
    
    # Display top opportunities
    top_opportunities = filtered_opportunities.head(top_n)
    print("\nTop Arbitrage Opportunities:")
    print(tabulate(top_opportunities[['symbol', 'long_exchange', 'short_exchange', 'spread']], 
                   headers='keys', tablefmt='pretty', floatfmt='.2f'))

    # Visualize opportunities
    visualize_opportunities(filtered_opportunities, top_n)

    logger.info("Crypto Arbitrage Scanner completed successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crypto Arbitrage Scanner")
    parser.add_argument("--min_spread", type=float, default=1.0, help="Minimum spread to consider (default: 1.0)")
    parser.add_argument("--top_n", type=int, default=10, help="Number of top opportunities to display (default: 10)")
    args = parser.parse_args()

    main(args.min_spread, args.top_n)