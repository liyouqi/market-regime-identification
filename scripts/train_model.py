"""
Train K-Means model and save it for daily predictions
Run this once to create the model files
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import pickle
import os

def train_and_save_model():
    """Train the regime identification model and save artifacts"""
    
    print("="*70)
    print("Training Market Regime Identification Model")
    print("="*70)
    
    # Load data
    print("\n1. Loading data...")
    df = pd.read_csv('../data/processed/full_market_matrix.csv', parse_dates=['Date'])
    print(f"   Loaded {len(df)} rows from {df['Date'].min()} to {df['Date'].max()}")
    
    # Feature engineering
    print("\n2. Engineering features...")
    
    # Single-asset features
    df['ret_btc'] = np.log(df['BTC'] / df['BTC'].shift(1))
    df['vol_btc_7'] = df['ret_btc'].rolling(7).std() * np.sqrt(365)
    df['fg_norm'] = df['fg_raw'] / 100
    
    # Multi-asset features
    price_cols = [c for c in df.columns if c not in ['Date', 'fg_raw', 'ret_btc', 'vol_btc_7', 'fg_norm']]
    
    # Market breadth: % of coins above 50-day MA
    ma_50_cols = [f'{coin}_ma50' for coin in price_cols]
    for coin in price_cols:
        df[f'{coin}_ma50'] = df[coin].rolling(50).mean()
    
    df['pct_above_ma50'] = df.apply(
        lambda row: sum(row[coin] > row[f'{coin}_ma50'] 
                       for coin in price_cols 
                       if pd.notna(row[f'{coin}_ma50'])) / len(price_cols),
        axis=1
    )
    
    print(f"   Created features: ret_btc, vol_btc_7, fg_norm, pct_above_ma50")
    
    # Select features for clustering
    feature_cols = ['ret_btc', 'vol_btc_7', 'fg_norm', 'pct_above_ma50']
    df_clean = df[['Date'] + feature_cols].dropna()
    
    print(f"   After cleaning: {len(df_clean)} rows")
    
    # Standardize features
    print("\n3. Standardizing features...")
    X = df_clean[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print(f"   Feature means: {scaler.mean_}")
    print(f"   Feature stds:  {scaler.scale_}")
    
    # Train K-Means
    print("\n4. Training K-Means (k=2)...")
    kmeans = KMeans(n_clusters=2, random_state=42, n_init=50, max_iter=500)
    clusters = kmeans.fit_predict(X_scaled)
    
    # Calculate metrics
    silhouette = silhouette_score(X_scaled, clusters)
    print(f"   Silhouette Score: {silhouette:.4f}")
    
    # Interpret clusters
    df_clean['cluster'] = clusters
    cluster_stats = df_clean.groupby('cluster')[feature_cols].mean()
    
    print("\n5. Cluster characteristics:")
    print(cluster_stats)
    
    # Determine which is Fear and which is Greed
    # Fear regime: higher volatility, lower returns
    if cluster_stats.loc[0, 'vol_btc_7'] > cluster_stats.loc[1, 'vol_btc_7']:
        print("\n   Cluster 0 = Fear (higher volatility)")
        print("   Cluster 1 = Greed (lower volatility)")
    else:
        print("\n   Cluster 0 = Greed (lower volatility)")
        print("   Cluster 1 = Fear (higher volatility)")
    
    # Save model and scaler
    print("\n6. Saving model artifacts...")
    
    # Create models directory if it doesn't exist
    os.makedirs('../models', exist_ok=True)
    
    with open('../models/kmeans_model.pkl', 'wb') as f:
        pickle.dump(kmeans, f)
    print("   ✓ Saved kmeans_model.pkl")
    
    with open('../models/scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    print("   ✓ Saved scaler.pkl")
    
    # Save feature names for reference
    with open('../models/feature_names.txt', 'w') as f:
        f.write('\n'.join(feature_cols))
    print("   ✓ Saved feature_names.txt")
    
    # Save regime labels for historical data
    regime_df = df_clean[['Date', 'cluster']].rename(columns={'cluster': 'regime'})
    regime_df.to_csv('../data/processed/regime_labels_new.csv', index=False)
    print(f"   ✓ Saved regime_labels_new.csv ({len(regime_df)} rows)")
    
    print("\n" + "="*70)
    print("✅ Model training complete!")
    print("="*70)
    print("\nYou can now use daily_update.py to make predictions on new data")
    
    return {
        'model': kmeans,
        'scaler': scaler,
        'feature_cols': feature_cols,
        'silhouette': silhouette
    }

if __name__ == '__main__':
    train_and_save_model()
