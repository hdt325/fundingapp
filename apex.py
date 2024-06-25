import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from pytz import timezone
import time
import streamlit as st

def get_all_symbols():
    url = "https://pro.apex.exchange/api/v2/symbols"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        all_symbols = []
        symbol_details = {}
        if 'data' in data:
            for config in ['usdcConfig', 'usdtConfig']:
                if config in data['data'] and 'perpetualContract' in data['data'][config]:
                    contracts = data['data'][config]['perpetualContract']
                    for contract in contracts:
                        if 'symbol' in contract:
                            all_symbols.append(contract['symbol'])
                            symbol_details[contract['symbol']] = {
                                'maxLeverage': contract.get('displayMaxLeverage', 'N/A')
                            }
        return sorted(set(all_symbols)), symbol_details
    except requests.exceptions.RequestException as e:
        print(f"Error fetching symbols: {e}")
        return [], {}

def get_ticker_data(symbol):
    ticker_symbol = symbol.replace('-', '')
    url = f"https://pro.apex.exchange/api/v1/ticker?symbol={ticker_symbol}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['data'][0] if data['data'] else None
    except requests.exceptions.RequestException as e:
        print(f"\nError fetching ticker data for {symbol}: {e}")
        return None

def get_apex_funding_rates():
    all_symbols, symbol_details = get_all_symbols()
    data = []
    total_symbols = len(all_symbols)
    
    pdt = timezone('America/Los_Angeles')
    current_time_pdt = datetime.now(pdt).strftime('%H:%M:%S | %m/%d/%y')

    # Create a progress bar
    progress_text = "Loading Apex Data"
    progress_bar = st.progress(0, text=progress_text)

    for i, symbol in enumerate(all_symbols, 1):
        ticker_data = get_ticker_data(symbol)
        if ticker_data:
            funding_rate = ticker_data.get('fundingRate')
            last_price = ticker_data.get('lastPrice', 'N/A')
            
            next_funding_time_str = ticker_data.get('nextFundingTime')
            if next_funding_time_str:
                next_funding_time_utc = datetime.strptime(next_funding_time_str, "%Y-%m-%dT%H:%M:%SZ")
                next_funding_time_pst = next_funding_time_utc.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('US/Pacific'))
                current_funding_time_pst = next_funding_time_pst - timedelta(hours=1)
            else:
                current_funding_time_pst = None

            max_leverage = symbol_details.get(symbol, {}).get('maxLeverage', 'N/A')

            data.append({
                'Symbol': symbol,
                'Funding Rate': f"{float(funding_rate) * 100:.6f}%" if funding_rate else 'N/A',
                'Funding Time (PST)': current_funding_time_pst.strftime('%H:%M | %m-%d-%y') if current_funding_time_pst else 'N/A',
                'Max Leverage': max_leverage,
                'Last Price': last_price,
                'Time Retrieved (PST)': current_time_pdt
            })
        else:
            data.append({
                'Symbol': symbol,
                'Funding Rate': 'N/A',
                'Funding Time (PST)': 'N/A',
                'Max Leverage': symbol_details.get(symbol, {}).get('maxLeverage', 'N/A'),
                'Last Price': 'N/A',
                'Time Retrieved (PST)': current_time_pdt
            })
        # Update progress bar
        progress_bar.progress((i) / total_symbols, text=progress_text)
           
        time.sleep(0.1)  # Add a small delay to avoid overwhelming the API
    
    # Clear the progress bar
    progress_bar.empty()
        
    df = pd.DataFrame(data)
    df = df.sort_values('Symbol')
    return df