"""
Daily update script: Fetch latest data and predict regime
Supports both local testing (historical data) and production (API data)
"""

import numpy as np
import pandas as pd
import pickle
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Get the project root directory
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
MODELS_DIR = PROJECT_ROOT / 'models'
DOCS_DATA_DIR = PROJECT_ROOT / 'docs' / 'data'

def load_model():
    """Load trained model and scaler"""
    with open(MODELS_DIR / 'kmeans_model.pkl', 'rb') as f:
        model = pickle.load(f)
    
    with open(MODELS_DIR / 'scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)
    
    return model, scaler

def fetch_latest_market_data(target_date):
    """
    Fetch latest market data from APIs
    
    Args:
        target_date: datetime object for the date to fetch
    
    Returns:
        dict with coin prices and F&G index, or None if failed
    """
    import requests
    import time
    
    # Coin ID mapping (CoinGecko ID -> Your CSV column name)
    coin_mapping = {
        'aave': 'AAVE',
        'cardano': 'ADA',
        'algorand': 'ALGO',
        'cosmos': 'ATOM',
        'avalanche-2': 'AVAX',
        'binancecoin': 'BNB',
        'bitcoin': 'BTC',
        'dogecoin': 'DOGE',
        'polkadot': 'DOT',
        'ethereum': 'ETH',
        'filecoin': 'FIL',
        'chainlink': 'LINK',
        'litecoin': 'LTC',
        'matic-network': 'MATIC',
        'solana': 'SOL',
        'tron': 'TRX',
        'uniswap': 'UNI',
        'vechain': 'VET',
        'stellar': 'XLM',
        'ripple': 'XRP'
    }
    
    try:
        # 1. Fetch coin prices from CoinGecko
        coins_list = ','.join(coin_mapping.keys())
        url = 'https://api.coingecko.com/api/v3/simple/price'
        params = {
            'ids': coins_list,
            'vs_currencies': 'usd'
        }
        
        print(f"      Fetching prices from CoinGecko...")
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        prices = response.json()
        
        # Validate that we got all coins
        if len(prices) < len(coin_mapping):
            missing = set(coin_mapping.keys()) - set(prices.keys())
            print(f"      ⚠️  Missing prices for: {missing}")
        
        # Delay to avoid rate limiting
        time.sleep(1)
        
        # 2. Fetch Fear & Greed Index
        print(f"      Fetching Fear & Greed Index...")
        fg_url = 'https://api.alternative.me/fng/?limit=1'
        fg_response = requests.get(fg_url, timeout=10)
        fg_response.raise_for_status()
        fg_data = fg_response.json()
        
        # 3. Build result dictionary
        result = {'Date': target_date}
        missing_coins = []
        
        for coin_id, symbol in coin_mapping.items():
            if coin_id in prices and 'usd' in prices[coin_id]:
                result[symbol] = prices[coin_id]['usd']
            else:
                # Use NaN for missing coins - will be handled by dropna() later
                result[symbol] = np.nan
                missing_coins.append(symbol)
        
        # Only fail if F&G index or too many coins are missing
        if len(missing_coins) > 5:
            print(f"      ❌ Too many missing coins ({len(missing_coins)}): {missing_coins}")
            return None
        
        if missing_coins:
            print(f"      ⚠️  Missing coins (will use NaN, cleaned later): {missing_coins}")
        
        result['fg_raw'] = int(fg_data['data'][0]['value'])
        
        print(f"      ✅ Fetched {len(coin_mapping) - len(missing_coins)}/{len(coin_mapping)} coins + F&G index")
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"      ❌ API Request failed: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        print(f"      ❌ Data parsing failed: {e}")
        return None
    except Exception as e:
        print(f"      ❌ Unexpected error: {e}")
        return None

def should_fetch_new_data(df, target_date=None):
    """
    Check if we should fetch new data
    
    Returns:
        (should_fetch: bool, reason: str, target_date: datetime)
    """
    if target_date is None:
        target_date = pd.to_datetime(datetime.now().date())
    else:
        target_date = pd.to_datetime(target_date)
    
    last_date = df['Date'].max()
    
    # Check 1: Data already exists
    if target_date in df['Date'].values:
        return False, f"Data for {target_date.date()} already exists", target_date
    
    # Check 2: Target date is not newer than last date
    if target_date <= last_date:
        return False, f"Target date {target_date.date()} <= last date {last_date.date()}", target_date
    
    # Check 3: Target date is in the future
    today = pd.to_datetime(datetime.now().date())
    if target_date > today:
        return False, f"Cannot fetch future data ({target_date.date()})", target_date
    
    # Check 4: Gap is too large (might indicate a problem)
    days_gap = (target_date - last_date).days
    if days_gap > 7:
        return False, f"Gap too large ({days_gap} days), manual review needed", target_date
    
    # All checks passed
    return True, f"Ready to fetch data for {target_date.date()}", target_date

def append_new_data(df, target_date=None):
    """
    Append new data to the dataframe if needed
    
    Returns:
        (df: DataFrame, appended: bool, message: str)
    """
    # Check if we should fetch
    should_fetch, reason, target_date = should_fetch_new_data(df, target_date)
    
    if not should_fetch:
        return df, False, reason
    
    # Try to fetch new data from API
    print(f"\n   📥 Attempting to fetch data for {target_date.date()}...")
    new_data = fetch_latest_market_data(target_date)
    
    if new_data is None:
        # API not available (local testing mode)
        return df, False, "API not configured (local testing mode)"
    
    # Validate the fetched data
    required_cols = ['Date', 'BTC'] + [c for c in df.columns if c not in ['Date', 'fg_raw']]
    if not all(col in new_data for col in required_cols):
        return df, False, f"Fetched data incomplete, missing columns"
    
    # Create new row as DataFrame
    new_row = pd.DataFrame([new_data])
    new_row['Date'] = pd.to_datetime(new_row['Date'])
    
    # Append to existing data
    df_updated = pd.concat([df, new_row], ignore_index=True)
    df_updated = df_updated.sort_values('Date').reset_index(drop=True)
    
    # Save to CSV
    try:
        df_updated.to_csv('../data/processed/full_market_matrix.csv', index=False)
        return df_updated, True, f"Successfully appended data for {target_date.date()}"
    except Exception as e:
        return df, False, f"Failed to save CSV: {str(e)}"

def calculate_features(df, target_date=None):
    """
    Calculate features for prediction
    If target_date is None, use the last available date
    """
    if target_date is None:
        target_date = df['Date'].max()
    else:
        target_date = pd.to_datetime(target_date)
    
    # Make sure we have enough history for rolling calculations
    start_date = target_date - timedelta(days=100)
    df_window = df[df['Date'] <= target_date].tail(100).copy()
    
    # Calculate features
    df_window['ret_btc'] = np.log(df_window['BTC'] / df_window['BTC'].shift(1))
    df_window['vol_btc_7'] = df_window['ret_btc'].rolling(7).std() * np.sqrt(365)
    df_window['fg_norm'] = df_window['fg_raw'] / 100
    
    # Market breadth
    price_cols = [c for c in df_window.columns if c not in ['Date', 'fg_raw', 'ret_btc', 'vol_btc_7', 'fg_norm']]
    
    for coin in price_cols:
        df_window[f'{coin}_ma50'] = df_window[coin].rolling(50).mean()
    
    df_window['pct_above_ma50'] = df_window.apply(
        lambda row: sum(row[coin] > row[f'{coin}_ma50'] 
                       for coin in price_cols 
                       if pd.notna(row[f'{coin}_ma50'])) / len(price_cols),
        axis=1
    )
    
    # Get the last row (target date)
    latest = df_window[df_window['Date'] == target_date].iloc[-1]
    
    return {
        'date': latest['Date'],
        'ret_btc': latest['ret_btc'],
        'vol_btc_7': latest['vol_btc_7'],
        'fg_norm': latest['fg_norm'],
        'pct_above_ma50': latest['pct_above_ma50'],
        'btc_price': latest['BTC']
    }

def predict_regime(features, model, scaler):
    """Predict regime for given features"""
    X = np.array([[
        features['ret_btc'],
        features['vol_btc_7'],
        features['fg_norm'],
        features['pct_above_ma50']
    ]])
    
    X_scaled = scaler.transform(X)
    regime = model.predict(X_scaled)[0]
    
    # Get distance to cluster centers for confidence
    distances = model.transform(X_scaled)[0]
    confidence = 1 - (distances[regime] / distances.sum())
    
    return int(regime), float(confidence)

def get_recent_history(df, days=30):
    """Get regime history for the past N days"""
    model, scaler = load_model()
    
    end_date = df['Date'].max()
    start_date = end_date - timedelta(days=days)
    
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    history = []
    for date in date_range:
        if date in df['Date'].values:
            try:
                features = calculate_features(df, date)
                regime, confidence = predict_regime(features, model, scaler)
                
                history.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'regime': 'fear' if regime == 0 else 'greed',
                    'regime_id': int(regime),
                    'confidence': round(confidence * 100, 1),
                    'btc_price': round(features['btc_price'], 2)
                })
            except:
                pass
    
    return history

def calculate_period_stats(history):
    """Calculate regime statistics for different periods"""
    if not history:
        return {}
    
    df_hist = pd.DataFrame(history)
    
    def get_stats(days):
        recent = df_hist.tail(days)
        fear_count = (recent['regime'] == 'fear').sum()
        greed_count = (recent['regime'] == 'greed').sum()
        total = len(recent)
        
        return {
            'fear_pct': round(fear_count / total * 100, 1) if total > 0 else 0,
            'greed_pct': round(greed_count / total * 100, 1) if total > 0 else 0,
            'switches': int((recent['regime'] != recent['regime'].shift()).sum() - 1)
        }
    
    return {
        'week': get_stats(7),
        'month': get_stats(30),
        'quarter': get_stats(90) if len(df_hist) >= 90 else get_stats(len(df_hist))
    }

def calculate_regime_statistics(history):
    """Calculate regime duration and switching statistics"""
    if not history or len(history) < 2:
        return {
            'avg_fear_duration': 0,
            'avg_greed_duration': 0,
            'total_switches': 0,
            'current_duration': 0
        }
    
    # Track regime periods
    fear_durations = []
    greed_durations = []
    switches = 0
    
    current_regime = history[0]['regime']
    current_duration = 1
    
    for i in range(1, len(history)):
        if history[i]['regime'] == current_regime:
            current_duration += 1
        else:
            # Regime switched
            if current_regime == 'fear':
                fear_durations.append(current_duration)
            else:
                greed_durations.append(current_duration)
            
            switches += 1
            current_regime = history[i]['regime']
            current_duration = 1
    
    # Add the last period (still ongoing)
    if current_regime == 'fear':
        fear_durations.append(current_duration)
    else:
        greed_durations.append(current_duration)
    
    return {
        'avg_fear_duration': sum(fear_durations) / len(fear_durations) if fear_durations else 0,
        'avg_greed_duration': sum(greed_durations) / len(greed_durations) if greed_durations else 0,
        'total_switches': switches,
        'current_duration': current_duration
    }

def update_dashboard_data():
    """
    Main function: update the JSON data for the dashboard
    Supports both local testing and production with data appending
    """
    print("="*70)
    print("🔄 Updating Dashboard Data")
    print("="*70)
    
    # Load historical data
    print("\n1. Loading historical data...")
    df = pd.read_csv(DATA_DIR / 'full_market_matrix.csv', parse_dates=['Date'])
    last_date = df['Date'].max()
    today = datetime.now().date()
    print(f"   Data range: {df['Date'].min().date()} to {last_date.date()}")
    print(f"   Today's date: {today}")
    
    # Check if we need to append new data
    print("\n2. Checking for new data...")
    should_fetch, reason, target_date = should_fetch_new_data(df)
    print(f"   {reason}")
    
    if should_fetch:
        print("   📥 Attempting to fetch new data...")
        df, appended, message = append_new_data(df)
        if appended:
            print(f"   ✅ {message}")
        else:
            print(f"   ℹ️  {message}")
    else:
        print("   ℹ️  Using existing data")
    
    # Load model
    print("\n3. Loading model...")
    model, scaler = load_model()
    print("   ✓ Model loaded")
    
    # Calculate features for latest date
    print("\n4. Calculating features for latest date...")
    latest_features = calculate_features(df)
    print(f"   Date: {latest_features['date'].strftime('%Y-%m-%d')}")
    print(f"   BTC Price: ${latest_features['btc_price']:,.2f}")
    print(f"   Volatility: {latest_features['vol_btc_7']:.4f}")
    print(f"   F&G Index: {latest_features['fg_norm']:.2f}")
    
    # Predict regime
    print("\n5. Predicting regime...")
    regime, confidence = predict_regime(latest_features, model, scaler)
    regime_name = 'Fear' if regime == 0 else 'Greed'
    regime_icon = '🔴' if regime == 0 else '🟢'
    print(f"   {regime_icon} Regime: {regime_name}")
    print(f"   📊 Confidence: {confidence*100:.1f}%")
    
    # Get recent history
    print("\n6. Getting recent history...")
    history_7d = get_recent_history(df, days=7)
    history_30d = get_recent_history(df, days=30)
    history_100d = get_recent_history(df, days=100)
    history_365d = get_recent_history(df, days=365)
    print(f"   ✓ Loaded {len(history_7d)} days (7d window)")
    print(f"   ✓ Loaded {len(history_30d)} days (30d window)")
    print(f"   ✓ Loaded {len(history_100d)} days (100d window)")
    print(f"   ✓ Loaded {len(history_365d)} days (365d window)")
    
    # 8. Define historical events
    historical_events = [
        {'name': 'COVID-19 Crash', 'date': '2020-03-12', 'type': 'fear', 'description': 'Global pandemic market crash'},
        {'name': '2021 Bull Peak', 'date': '2021-04-14', 'type': 'greed', 'description': 'Bitcoin reached $64k'},
        {'name': 'May 2021 Crash', 'date': '2021-05-19', 'type': 'fear', 'description': 'China mining ban announcement'},
        {'name': 'November 2021 Peak', 'date': '2021-11-10', 'type': 'greed', 'description': 'Bitcoin ATH $69k'},
        {'name': 'Terra/Luna Collapse', 'date': '2022-05-09', 'type': 'fear', 'description': 'UST stablecoin depegged'},
        {'name': 'FTX Collapse', 'date': '2022-11-08', 'type': 'fear', 'description': 'Major exchange bankruptcy'},
        {'name': 'ETF Approval Rally', 'date': '2024-01-11', 'type': 'greed', 'description': 'Bitcoin spot ETF approved'},
        {'name': '2024 Halving Rally', 'date': '2024-04-20', 'type': 'greed', 'description': 'Bitcoin halving event'}
    ]
    
    # Validate events with actual regime predictions
    events_with_predictions = []
    for event in historical_events:
        event_date = pd.to_datetime(event['date'])
        # Find regime on that date
        event_data = df[df['Date'] == event_date]
        if not event_data.empty:
            features = calculate_features(df, event_date)
            if features is not None:
                regime_id, confidence = predict_regime(features, model, scaler)
                regime_name = 'fear' if regime_id == 0 else 'greed'
                events_with_predictions.append({
                    'name': event['name'],
                    'date': event['date'],
                    'type': event['type'],
                    'description': event['description'],
                    'predicted_regime': regime_name,
                    'predicted_id': regime_id,
                    'confidence': round(confidence * 100, 1),
                    'is_match': (event['type'] == 'fear' and regime_id == 0) or (event['type'] == 'greed' and regime_id == 1)
                })
    
    print(f"\n7. Validating {len(events_with_predictions)} historical events...")
    matches = sum(1 for e in events_with_predictions if e['is_match'])
    print(f"   ✓ Accuracy: {matches}/{len(events_with_predictions)} ({100*matches/len(events_with_predictions):.1f}%)")
    
    # 9. Calculate period statistics
    print("\n8. Calculating period statistics...")
    period_stats = calculate_period_stats(history_30d)
    print(f"   Week:  Fear {period_stats['week']['fear_pct']}% | Greed {period_stats['week']['greed_pct']}%")
    print(f"   Month: Fear {period_stats['month']['fear_pct']}% | Greed {period_stats['month']['greed_pct']}%")
    
    # 10. Generate full calendar data (last 2 years)
    print("\n9. Generating calendar heatmap data...")
    calendar_data = get_recent_history(df, days=730)  # 2 years
    print(f"   ✓ Loaded {len(calendar_data)} days for calendar view")
    
    # 11. Calculate regime duration statistics
    print("\n10. Calculating regime duration statistics...")
    regime_stats = calculate_regime_statistics(calendar_data)
    print(f"   ✓ Avg Fear duration: {regime_stats['avg_fear_duration']:.1f} days")
    print(f"   ✓ Avg Greed duration: {regime_stats['avg_greed_duration']:.1f} days")
    print(f"   ✓ Total switches in 2 years: {regime_stats['total_switches']}")
    
    # Find last regime switch and current duration
    if len(history_30d) > 1:
        for i in range(len(history_30d)-1, 0, -1):
            if history_30d[i]['regime'] != history_30d[i-1]['regime']:
                last_switch = history_30d[i]['date']
                days_since = (datetime.strptime(history_30d[-1]['date'], '%Y-%m-%d') - 
                             datetime.strptime(last_switch, '%Y-%m-%d')).days
                break
        else:
            last_switch = None
            days_since = None
    else:
        last_switch = None
        days_since = None
    
    # Prepare output data
    output_data = {
        'meta': {
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'data_date': latest_features['date'].strftime('%Y-%m-%d'),
            'mode': 'production' if should_fetch else 'local_test',
            'data_freshness': 'up-to-date' if latest_features['date'].date() >= today else 'historical'
        },
        'current': {
            'regime': regime_name.lower(),
            'regime_id': int(regime),
            'confidence': round(confidence * 100, 1),
            'btc_price': round(latest_features['btc_price'], 2),
            'fg_index': round(latest_features['fg_norm'] * 100, 0),
            'volatility_7d': round(latest_features['vol_btc_7'], 4),
            'market_breadth': round(latest_features['pct_above_ma50'] * 100, 1)
        },
        'period_stats': period_stats,
        'regime_stats': regime_stats,
        'last_switch': {
            'date': last_switch,
            'days_ago': days_since
        } if last_switch else None,
        'history': {
            '7d': history_7d,
            '30d': history_30d,
            '100d': history_100d,
            '365d': history_365d
        },
        'calendar': calendar_data,
        'historical_events': events_with_predictions
    }
    
    # Save to JSON
    print("\n11. Saving to JSON...")
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(DOCS_DATA_DIR / 'regime_data.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"   ✓ Saved to {DOCS_DATA_DIR / 'regime_data.json'}")
    
    print("\n" + "="*70)
    print("✅ Dashboard data updated successfully!")
    print("="*70)
    print(f"\nCurrent Regime: {regime_icon} {regime_name} ({confidence*100:.1f}% confidence)")
    print("\n" + "="*70)
    print("✅ Dashboard data updated successfully!")
    print("="*70)
    print(f"\nCurrent Regime: {regime_icon} {regime_name} ({confidence*100:.1f}% confidence)")
    print(f"BTC Price: ${latest_features['btc_price']:,.2f}")
    print(f"Data Date: {latest_features['date'].strftime('%Y-%m-%d')}")
    
    # Display data freshness warning
    days_old = (today - latest_features['date'].date()).days
    if days_old > 0:
        print(f"\n⚠️  Data is {days_old} day(s) old (waiting for API implementation)")
    else:
        print(f"\n✅ Data is up-to-date")
    
    print(f"\nYou can now open docs/index.html in your browser")
    
    return output_data

if __name__ == '__main__':
    update_dashboard_data()
