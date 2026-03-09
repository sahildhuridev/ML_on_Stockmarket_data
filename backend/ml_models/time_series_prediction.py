import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta
from statsmodels.tsa.arima.model import ARIMA
import warnings
from statsmodels.tools.sm_exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def _fit_best_arima(y_hist):
    """
    Fit a small ARIMA grid and return the best fitted model by AIC.
    Falls back to ARIMA(1,1,1) if selection fails.
    """
    # Candidate orders kept intentionally small for API responsiveness.
    candidate_orders = [
        (1, 1, 1),
        (2, 1, 1),
        (1, 1, 2),
        (2, 1, 2),
        (3, 1, 1),
        (1, 0, 1),
        (2, 0, 1),
    ]

    best_model = None
    best_aic = np.inf

    for order in candidate_orders:
        try:
            fitted = ARIMA(y_hist, order=order).fit()
            if np.isfinite(fitted.aic) and fitted.aic < best_aic:
                best_aic = fitted.aic
                best_model = fitted
        except Exception:
            continue

    if best_model is None:
        best_model = ARIMA(y_hist, order=(1, 1, 1)).fit()

    return best_model

def analyze_time_series(symbol, interval, period, models):
    """
    Fetches real-time stock data and extrapolates 15 periods into the future
    based on the selected time series models.
    """
    symbol = symbol.upper()
    
    # 1. Fetch historical data
    try:
        data = yf.download(symbol, period=period, interval=interval)
        if data.empty:
            return {"error": f"No data found for symbol: {symbol}"}
    except Exception as e:
        return {"error": f"Error fetching data: {str(e)}"}

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
        
    data.reset_index(inplace=True)
    
    date_col = 'Datetime' if 'Datetime' in data.columns else 'Date'
    data.rename(columns={date_col: 'Date'}, inplace=True)

    # Ensure dates are proper datetime objects for delta math
    data['Date'] = pd.to_datetime(data['Date'])

    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')

    # Drop any NaNs in historical close
    data = data.dropna(subset=['Close'])
    
    # Prepare historical output
    hist_records = data.copy()
    
    # We will compute the time delta to construct 15 future dates
    time_deltas = data['Date'].diff().dropna()
    if len(time_deltas) > 0:
        # Get the most common interval step
        step = time_deltas.mode()[0]
    else:
        # Fallback if there's only 1 point or less
        step = pd.Timedelta(days=1)
        
    last_date = data['Date'].iloc[-1]
    
    future_dates = [last_date + (step * i) for i in range(1, 16)]
    
    # 2. Time Series Forecasting (Next 15 periods)
    # We will use the historical 'Close' price as our signal

    X_hist = np.arange(len(data)).reshape(-1, 1)
    y_hist = data['Close'].values
    
    X_future = np.arange(len(data), len(data) + 15).reshape(-1, 1)

    predictions = {'Date': future_dates}
    
    # Basic Linear Regression Model
    if 'linear' in models:
        lr = LinearRegression()
        lr.fit(X_hist, y_hist)
        predictions['LR_Predict'] = lr.predict(X_future)
        
        # Also plot it slightly backwards to connect properly to the last historical point if desired
        # But for clean datasets we just append it
        
    # Simple Moving Average Extrapolation Model (Last N periods average projected forward flatly)
    if 'sma_extrapolate' in models:
        sma_val = y_hist[-20:].mean() if len(y_hist) >= 20 else y_hist.mean()
        # Project flatly as a conservative baseline
        predictions['SMA_Predict'] = np.full(15, sma_val)
        
    # Polynomial Regression (Degree 2) to capture curves
    if 'poly' in models:
        # Simple math polyfit instead of sklearn pipeline for brevity
        coefs = np.polyfit(X_hist.flatten(), y_hist, 2)
        poly_fn = np.poly1d(coefs)
        predictions['Poly_Predict'] = poly_fn(X_future.flatten())

    # ARIMA Forecast (advanced, non-flat series behavior over horizons)
    if 'arima' in models and len(y_hist) >= 20:
        try:
            best_arima = _fit_best_arima(y_hist)
            predictions['ARIMA_Predict'] = best_arima.forecast(steps=15)
        except Exception:
            # Silent fallback if ARIMA fails for edge symbols/windows
            pass

    # Format JSON
    # Historical
    hist_records['Date'] = hist_records['Date'].astype(str)
    hist_json = hist_records.replace({np.nan: None}).to_dict(orient='records')
    
    # Future
    future_df = pd.DataFrame(predictions)
    future_df['Date'] = future_df['Date'].astype(str)
    
    # For future records, ensure historical candlestick fields exist but are None
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        future_df[col] = None
        
    future_json = future_df.replace({np.nan: None}).to_dict(orient='records')
    
    # Combine
    combined = hist_json + future_json

    return {
        "symbol": symbol,
        "interval": interval,
        "period": period,
        "models_applied": [m for m in ['linear', 'sma_extrapolate', 'poly', 'arima'] if m in models],
        "data": combined
    }
