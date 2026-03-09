import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def analyze_crypto(symbol, interval, period, models):
    """
    Fetches real-time crypto data and computes requested time series models natively.
    Returns a unified list of JSON dictionaries for charting.
    
    Models supported: 'sma', 'ema', 'trend'
    """
    symbol = symbol.upper()
    
    # 1. Fetch raw data from yfinance
    try:
        data = yf.download(symbol, period=period, interval=interval)
        if data.empty:
            return {"error": f"No data found for symbol: {symbol}"}
    except Exception as e:
        return {"error": f"Error fetching data: {str(e)}"}

    # Fix yfinance multi-index columns if present
    if isinstance(data.columns, pd.MultiIndex):
        # We assume the second level is the ticker symbol, we just want the 'Price' metrics
        data.columns = data.columns.droplevel(1)
        
    # Reset index to get 'Date' or 'Datetime' as a column
    data.reset_index(inplace=True)
    
    # Rename 'Datetime' to 'Date' for consistency if using intraday
    if 'Datetime' in data.columns:
        data.rename(columns={'Datetime': 'Date'}, inplace=True)
        
    # Convert dates to string format for JSON serialization
    data['Date'] = data['Date'].astype(str)

    # Convert prices to numeric
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')


    # 2. Time Series Modeling
    
    if 'sma' in models:
        # Simple Moving Average (20 periods)
        data['SMA'] = data['Close'].rolling(window=20, min_periods=1).mean()
        
    if 'ema' in models:
        # Exponential Moving Average (20 periods)
        data['EMA'] = data['Close'].ewm(span=20, adjust=False).mean()
        
    if 'trend' in models:
        # Linear Regression Trendline fit over the entire provided period
        # We need numerical X values (indices) for sklearn
        X = np.arange(len(data)).reshape(-1, 1)
        y = data['Close'].values
        
        # Handle NaN values inside 'Close' just in case before fitting
        valid_idx = ~np.isnan(y)
        if valid_idx.sum() > 1: # Need at least 2 points to draw a line
            lr = LinearRegression()
            lr.fit(X[valid_idx], y[valid_idx])
            
            # Predict the trend across all X
            data['Trend'] = lr.predict(X)
        else:
             data['Trend'] = np.nan
             

    # 3. Format into a JSON-friendly array of dictionaries
    # Convert NaN to None for proper JSON translation
    data = data.replace({np.nan: None})
    
    # Select columns to output
    cols_to_keep = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    for m in ['SMA', 'EMA', 'Trend']:
        if m in data.columns:
            cols_to_keep.append(m)
            
    # Keep only the columns that actually exist
    final_cols = [c for c in cols_to_keep if c in data.columns]
    
    records = data[final_cols].to_dict(orient='records')
    
    # Optional metadata
    return {
        "symbol": symbol,
        "interval": interval,
        "period": period,
        "models_applied": [m for m in ['sma', 'ema', 'trend'] if m in models],
        "data": records
    }
