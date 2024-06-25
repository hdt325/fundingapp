import ccxt
import requests
import pandas as pd
from datetime import datetime
from pytz import timezone
import time
import streamlit as st

def get_funding_rates(num_pairs=None):
    hyperliquid = ccxt.hyperliquid({'enableRateLimit': True, 'rateLimit': 1000})
    markets_hyperliquid = hyperliquid.load_markets()
    funding_data = []
    now = hyperliquid.milliseconds()
    one_hour_ago = now - (60 * 60 * 1000)

    def convert_to_pst(dt_str):
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        pst = timezone('US/Pacific')
        dt_pst = dt.replace(tzinfo=timezone('UTC')).astimezone(pst)
        return dt_pst.strftime("%H:%M | %m/%d/%y")

    def format_funding_rate(rate):
        percentage = rate * 100
        return f"{percentage:.6f}%"

    def fetch_meta_data():
        url = "https://api.hyperliquid.xyz/info"
        headers = {"Content-Type": "application/json"}
        body_meta = {"type": "meta"}
        response_meta = requests.post(url, headers=headers, json=body_meta)
        return response_meta.json()

    def parse_meta_data(data_meta):
        market_info = {}
        if 'universe' in data_meta:
            for item in data_meta['universe']:
                market_info[item['name']] = {'maxLeverage': item.get('maxLeverage', 'N/A')}
        return market_info

    def fetch_funding_data(market_info):
        symbols = list(markets_hyperliquid.keys())
        if num_pairs:
            symbols = symbols[:num_pairs]
        progress_text = "Loading Hyperliquid Data"
        my_bar = st.progress(0, text=progress_text)
        total_symbols = len(symbols)
        for i, symbol in enumerate(symbols):
            if symbol == 'PURR/USDC':
                continue
            try:
                funding_history = hyperliquid.fetchFundingRateHistory(symbol, one_hour_ago, None)
                if isinstance(funding_history, list) and len(funding_history) > 0:
                    rate = funding_history[0]
                    if isinstance(rate, dict) and 'fundingRate' in rate:
                        clean_symbol = symbol.split('/')[0]
                        max_leverage = market_info.get(clean_symbol, {}).get('maxLeverage', 'N/A')
                        funding_data.append([
                            clean_symbol,
                            format_funding_rate(rate['fundingRate']),
                            convert_to_pst(rate['datetime']),
                            max_leverage
                        ])
                my_bar.progress((i + 1) / total_symbols, text=progress_text)
                time.sleep(0.05)
            except ccxt.RateLimitExceeded:
                time.sleep(60)
            except Exception as e:
                st.error(f"Error fetching funding rate for {symbol}: {str(e)}")
        my_bar.empty()
        return funding_data

    data_meta = fetch_meta_data()
    market_info = parse_meta_data(data_meta)
    funding_data = fetch_funding_data(market_info)
    funding_data.sort(key=lambda x: x[0])
    return funding_data

def get_mark_prices():
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    body = {"type": "metaAndAssetCtxs"}
    response = requests.post(url, headers=headers, json=body)
    data = response.json()

    universe = data[0]['universe']
    asset_contexts = data[1]

    pdt = timezone('America/Los_Angeles')
    current_time_pdt = datetime.now(pdt).strftime('%H:%M:%S | %m/%d/%y')

    all_assets = []
    for i, asset in enumerate(universe):
        asset_name = asset['name']
        asset_data = asset_contexts[i] if i < len(asset_contexts) else {}
        mark_price = asset_data.get('markPx', 'N/A')
        if mark_price != 'N/A':
            mark_price = f"{float(mark_price):g}"
        all_assets.append({
            'Name': asset_name,
            'Mark Price': mark_price,
            'Time Retrieved (PST)': current_time_pdt
        })

    df_display = pd.DataFrame(all_assets)
    return df_display

def load_hyperliquid_data(num_pairs):
    funding_data = get_funding_rates(num_pairs)
    funding_df = pd.DataFrame(funding_data, columns=['Symbol', 'Funding Rate', 'Funding Time (PST)', 'Max Leverage'])
    mark_prices_df = get_mark_prices()
    merged_df = pd.merge(funding_df, mark_prices_df, left_on='Symbol', right_on='Name', how='left')
    merged_df.drop(columns=['Name'], inplace=True)
    return merged_df