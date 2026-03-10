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

    # --- Volatility estimation for realistic price-action-like predictions ---
    # Compute historical log-return volatility (std of daily returns)
    returns = np.diff(np.log(y_hist[y_hist > 0]))  # log returns
    hist_vol = np.std(returns) if len(returns) > 1 else 0.01
    last_close = float(y_hist[-1])
    rng = np.random.RandomState(42)  # seeded for reproducibility

    def _apply_realistic_noise(trend_values, vol_scale=1.0):
        """
        Convert a smooth trend into a realistic price-action-like path.
        Uses a cumulative random walk anchored to the trend so the overall
        direction is preserved but the path wiggles like real prices.
        """
        n = len(trend_values)
        # Generate per-step returns scaled to historical volatility
        noise_returns = rng.normal(0, hist_vol * vol_scale, n)
        # Build a cumulative noise path in price-space
        cumulative_noise = np.cumsum(noise_returns) * last_close
        # Blend: trend provides direction, noise provides texture
        result = trend_values + cumulative_noise
        # Ensure we don't get negative prices
        result = np.maximum(result, trend_values * 0.5)
        return result

    # Basic Linear Regression Model
    if 'linear' in models:
        lr = LinearRegression()
        lr.fit(X_hist, y_hist)
        lr_trend = lr.predict(X_future)
        predictions['LR_Predict'] = _apply_realistic_noise(lr_trend, vol_scale=0.8)
        
    # Simple Moving Average Extrapolation Model — random walk with SMA drift
    if 'sma_extrapolate' in models:
        sma_val = y_hist[-20:].mean() if len(y_hist) >= 20 else y_hist.mean()
        # Random walk seeded at last close, with mean-reversion toward SMA
        sma_path = np.zeros(15)
        sma_path[0] = last_close
        for i in range(1, 15):
            drift = (sma_val - sma_path[i - 1]) * 0.05  # gentle pull toward SMA
            step = drift + rng.normal(0, hist_vol * last_close * 0.8)
            sma_path[i] = max(sma_path[i - 1] + step, sma_val * 0.5)
        predictions['SMA_Predict'] = sma_path
        
    # Polynomial Regression (Degree 2) to capture curves
    if 'poly' in models:
        coefs = np.polyfit(X_hist.flatten(), y_hist, 2)
        poly_fn = np.poly1d(coefs)
        poly_trend = poly_fn(X_future.flatten())
        predictions['Poly_Predict'] = _apply_realistic_noise(poly_trend, vol_scale=0.9)

    # ARIMA Forecast (advanced, non-flat series behavior over horizons)
    if 'arima' in models and len(y_hist) >= 20:
        try:
            best_arima = _fit_best_arima(y_hist)
            arima_trend = best_arima.forecast(steps=15)
            # ARIMA already has some variance, add lighter noise
            predictions['ARIMA_Predict'] = _apply_realistic_noise(
                np.array(arima_trend), vol_scale=0.5
            )
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
