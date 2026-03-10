"""
Model Accuracy Engine
Runs 6 ML models (Linear Regression, Logistic Regression, LSTM, RNN, CNN, ARIMA)
on hourly stock data and evaluates prediction accuracy.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

logger = logging.getLogger(__name__)

# Suppress TF logs
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


def fetch_hourly_data(ticker, target_date_str, target_hour_str, days=30):
    """Fetch last 30 days of hourly stock data using yfinance."""
    try:
        target_dt = datetime.strptime(f"{target_date_str} {target_hour_str}", "%Y-%m-%d %H:%M")
        start_date = target_dt - timedelta(days=days)
        
        # yfinance max for hourly is 730 days, and requires period <= 60 days per chunk
        # We fetch with start/end dates
        data = yf.download(
            ticker,
            start=start_date.strftime("%Y-%m-%d"),
            end=(target_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1h",
            progress=False,
            auto_adjust=True
        )
        
        if data is None or data.empty:
            return None, None, target_dt
        
        # Flatten multi-level columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        # Ensure datetime index is timezone-naive for comparison
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)
        
        return data, data['Close'].values, target_dt
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None, None, None


def prepare_features(close_prices, lookback=10):
    """Create feature matrix with lagged values and technical indicators."""
    if len(close_prices) < lookback + 5:
        return None, None
    
    df = pd.DataFrame({'close': close_prices})
    
    # Lagged features
    for i in range(1, lookback + 1):
        df[f'lag_{i}'] = df['close'].shift(i)
    
    # Moving averages
    df['ma_5'] = df['close'].rolling(5).mean()
    df['ma_10'] = df['close'].rolling(10).mean()
    
    # Returns
    df['return_1'] = df['close'].pct_change(1)
    df['return_3'] = df['close'].pct_change(3)
    
    # Volatility
    df['volatility'] = df['close'].rolling(5).std()
    
    # Target: next close price
    df['target'] = df['close'].shift(-1)
    
    df = df.dropna()
    
    if len(df) < 20:
        return None, None
    
    feature_cols = [c for c in df.columns if c not in ['close', 'target']]
    X = df[feature_cols].values
    y = df['target'].values
    
    return X, y


def run_linear_regression(X_train, y_train, X_test):
    """Linear Regression prediction."""
    try:
        model = LinearRegression()
        model.fit(X_train, y_train)
        prediction = model.predict(X_test.reshape(1, -1))[0]
        return float(prediction)
    except Exception as e:
        logger.error(f"Linear Regression error: {e}")
        return None


def run_logistic_regression(X_train, y_train, X_test, current_price):
    """
    Logistic Regression: classifies price direction (up/down).
    Predicted price = current_price * (1 + avg_return) or (1 - avg_return).
    """
    try:
        # Create binary target: 1 if price went up, 0 if down
        y_binary = (y_train[1:] > y_train[:-1]).astype(int)
        X_binary = X_train[:-1]
        
        if len(np.unique(y_binary)) < 2:
            # Only one class – default to current price
            return float(current_price)
        
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X_binary)
        X_test_scaled = scaler.transform(X_test.reshape(1, -1))
        
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_scaled, y_binary)
        
        prob = model.predict_proba(X_test_scaled)[0]
        direction = model.predict(X_test_scaled)[0]
        
        # Calculate average absolute return for magnitude estimation
        returns = np.abs(np.diff(y_train) / y_train[:-1])
        avg_return = float(np.mean(returns))
        
        if direction == 1:
            prediction = current_price * (1 + avg_return * prob[1])
        else:
            prediction = current_price * (1 - avg_return * prob[0])
        
        return float(prediction)
    except Exception as e:
        logger.error(f"Logistic Regression error: {e}")
        return None


def _build_sequences(X, y, seq_length=10):
    """Build 3D sequences for LSTM/RNN/CNN."""
    X_seq, y_seq = [], []
    for i in range(len(X) - seq_length):
        X_seq.append(X[i:i + seq_length])
        y_seq.append(y[i + seq_length])
    return np.array(X_seq), np.array(y_seq)


def run_lstm(X_train, y_train, X_test, seq_length=10):
    """LSTM prediction using TensorFlow."""
    try:
        import tensorflow as tf
        tf.get_logger().setLevel('ERROR')
        
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        
        X_scaled = scaler_X.fit_transform(X_train)
        y_scaled = scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()
        
        X_seq, y_seq = _build_sequences(X_scaled, y_scaled, seq_length)
        
        if len(X_seq) < 5:
            return None
        
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(32, input_shape=(seq_length, X_seq.shape[2]), return_sequences=False),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        model.fit(X_seq, y_seq, epochs=20, batch_size=16, verbose=0)
        
        # Prepare test sequence
        last_seq = scaler_X.transform(X_train[-seq_length:])
        last_seq = last_seq.reshape(1, seq_length, -1)
        
        pred_scaled = model.predict(last_seq, verbose=0)[0][0]
        prediction = scaler_y.inverse_transform([[pred_scaled]])[0][0]
        
        tf.keras.backend.clear_session()
        return float(prediction)
    except Exception as e:
        logger.error(f"LSTM error: {e}")
        return None


def run_rnn(X_train, y_train, X_test, seq_length=10):
    """Simple RNN prediction using TensorFlow."""
    try:
        import tensorflow as tf
        tf.get_logger().setLevel('ERROR')
        
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        
        X_scaled = scaler_X.fit_transform(X_train)
        y_scaled = scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()
        
        X_seq, y_seq = _build_sequences(X_scaled, y_scaled, seq_length)
        
        if len(X_seq) < 5:
            return None
        
        model = tf.keras.Sequential([
            tf.keras.layers.SimpleRNN(32, input_shape=(seq_length, X_seq.shape[2]), return_sequences=False),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        model.fit(X_seq, y_seq, epochs=20, batch_size=16, verbose=0)
        
        last_seq = scaler_X.transform(X_train[-seq_length:])
        last_seq = last_seq.reshape(1, seq_length, -1)
        
        pred_scaled = model.predict(last_seq, verbose=0)[0][0]
        prediction = scaler_y.inverse_transform([[pred_scaled]])[0][0]
        
        tf.keras.backend.clear_session()
        return float(prediction)
    except Exception as e:
        logger.error(f"RNN error: {e}")
        return None


def run_cnn(X_train, y_train, X_test, seq_length=10):
    """1D CNN prediction using TensorFlow."""
    try:
        import tensorflow as tf
        tf.get_logger().setLevel('ERROR')
        
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        
        X_scaled = scaler_X.fit_transform(X_train)
        y_scaled = scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()
        
        X_seq, y_seq = _build_sequences(X_scaled, y_scaled, seq_length)
        
        if len(X_seq) < 5:
            return None
        
        model = tf.keras.Sequential([
            tf.keras.layers.Conv1D(32, kernel_size=3, activation='relu',
                                   input_shape=(seq_length, X_seq.shape[2])),
            tf.keras.layers.GlobalAveragePooling1D(),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        model.fit(X_seq, y_seq, epochs=20, batch_size=16, verbose=0)
        
        last_seq = scaler_X.transform(X_train[-seq_length:])
        last_seq = last_seq.reshape(1, seq_length, -1)
        
        pred_scaled = model.predict(last_seq, verbose=0)[0][0]
        prediction = scaler_y.inverse_transform([[pred_scaled]])[0][0]
        
        tf.keras.backend.clear_session()
        return float(prediction)
    except Exception as e:
        logger.error(f"CNN error: {e}")
        return None


def run_arima(close_prices):
    """ARIMA time series prediction."""
    try:
        from statsmodels.tsa.arima.model import ARIMA
        
        series = pd.Series(close_prices)
        
        # Fit ARIMA(5,1,0) – simple differencing model
        model = ARIMA(series, order=(5, 1, 0))
        fitted = model.fit()
        
        # Forecast 1 step ahead
        forecast = fitted.forecast(steps=1)
        prediction = float(forecast.iloc[0]) if hasattr(forecast, 'iloc') else float(forecast[0])
        
        return prediction
    except Exception as e:
        logger.error(f"ARIMA error: {e}")
        return None


def calculate_accuracy_metrics(predictions_dict, actual_price):
    """Calculate MAE, RMSE, MAPE for each model."""
    metrics = {}
    for model_name, pred_price in predictions_dict.items():
        if pred_price is None or actual_price is None:
            continue
        
        error = abs(pred_price - actual_price)
        mae = error
        rmse = error  # single point RMSE = abs error
        mape = (error / actual_price) * 100 if actual_price != 0 else 0
        
        metrics[model_name] = {
            'mae': round(mae, 4),
            'rmse': round(rmse, 4),
            'mape': round(mape, 4),
            'prediction_error': round(pred_price - actual_price, 4),
        }
    
    return metrics


def rank_models(metrics):
    """Rank models by RMSE (ascending)."""
    if not metrics:
        return []
    
    ranked = sorted(metrics.items(), key=lambda x: x[1]['rmse'])
    result = []
    for i, (model_name, model_metrics) in enumerate(ranked):
        result.append({
            'rank': i + 1,
            'model': model_name,
            'rmse': model_metrics['rmse'],
            'mae': model_metrics['mae'],
            'mape': model_metrics['mape'],
        })
    return result


def analyze_stock(ticker, company_name, target_date_str, target_hour_str):
    """Analyze a single stock with all 6 models."""
    data, close_prices, target_dt = fetch_hourly_data(ticker, target_date_str, target_hour_str)
    
    if data is None or close_prices is None or len(close_prices) < 30:
        return {
            'stock_ticker': ticker,
            'stock_name': company_name,
            'error': 'Insufficient data available',
        }
    
    current_price = float(close_prices[-1])
    min_price = float(np.min(close_prices))
    max_price = float(np.max(close_prices))
    
    # Prepare features
    X, y = prepare_features(close_prices)
    
    if X is None or y is None:
        return {
            'stock_ticker': ticker,
            'stock_name': company_name,
            'error': 'Could not prepare features',
        }
    
    # Split: all except last for training, last for prediction
    X_train, X_test = X[:-1], X[-1]
    y_train = y[:-1]
    
    # Run all models
    predictions = {}
    predictions['Linear'] = run_linear_regression(X_train, y_train, X_test)
    predictions['Logistic'] = run_logistic_regression(X_train, y_train, X_test, current_price)
    predictions['LSTM'] = run_lstm(X_train, y_train, X_test)
    predictions['RNN'] = run_rnn(X_train, y_train, X_test)
    predictions['CNN'] = run_cnn(X_train, y_train, X_test)
    predictions['ARIMA'] = run_arima(close_prices)
    
    # Build result for each model
    model_results = {}
    for model_name, pred_price in predictions.items():
        if pred_price is not None:
            change = round(pred_price - current_price, 4)
            signal = 'increase' if pred_price > current_price else 'decrease'
        else:
            pred_price = None
            change = None
            signal = 'N/A'
        
        model_results[model_name] = {
            'predicted_score': round(pred_price, 4) if pred_price else None,
            'change': change,
            'signal': signal,
        }
    
    # Check if actual price is available (target datetime is in the past)
    actual_price = None
    now = datetime.now()
    if target_dt and target_dt < now:
        # Try to find actual price at the target hour
        try:
            target_hour = int(target_hour_str.split(':')[0])
            for idx in data.index:
                idx_naive = idx.replace(tzinfo=None) if idx.tzinfo else idx
                if (idx_naive.date() == target_dt.date() and 
                    idx_naive.hour == target_hour):
                    actual_price = float(data.loc[idx, 'Close'])
                    break
        except Exception:
            pass
    
    # Calculate accuracy if actual price exists
    accuracy_metrics = None
    if actual_price is not None:
        accuracy_metrics = calculate_accuracy_metrics(predictions, actual_price)
    
    return {
        'stock_ticker': ticker,
        'stock_name': company_name,
        'current_price': round(current_price, 4),
        'min_price': round(min_price, 4),
        'max_price': round(max_price, 4),
        'actual_price': round(actual_price, 4) if actual_price else None,
        'models': model_results,
        'accuracy_metrics': accuracy_metrics,
    }


def analyze_portfolio_stocks(stocks_queryset, target_date, target_hour):
    """
    Orchestrator: analyse every stock in the portfolio.
    Returns stocks results, model ranking, and analysis summary.
    """
    results = []
    all_predictions = {m: [] for m in ['Linear', 'Logistic', 'LSTM', 'RNN', 'CNN', 'ARIMA']}
    all_actuals = []
    has_actual = False
    
    for stock in stocks_queryset:
        result = analyze_stock(stock.ticker, stock.company_name, target_date, target_hour)
        results.append(result)
        
        if 'error' not in result and result.get('actual_price') is not None:
            has_actual = True
            all_actuals.append(result['actual_price'])
            for model_name in all_predictions:
                pred = result['models'].get(model_name, {}).get('predicted_score')
                all_predictions[model_name].append(pred)
    
    # Aggregate model ranking across all stocks (if actual prices available)
    model_ranking = []
    analysis = {
        'total_stocks': len(results),
        'stocks_with_data': sum(1 for r in results if 'error' not in r),
        'has_actual_prices': has_actual,
    }
    
    if has_actual and all_actuals:
        aggregate_metrics = {}
        for model_name, preds in all_predictions.items():
            valid = [(p, a) for p, a in zip(preds, all_actuals) if p is not None]
            if valid:
                pred_arr = np.array([v[0] for v in valid])
                actual_arr = np.array([v[1] for v in valid])
                
                mae = float(np.mean(np.abs(pred_arr - actual_arr)))
                rmse = float(np.sqrt(np.mean((pred_arr - actual_arr) ** 2)))
                mape = float(np.mean(np.abs((pred_arr - actual_arr) / actual_arr)) * 100)
                
                aggregate_metrics[model_name] = {
                    'mae': round(mae, 4),
                    'rmse': round(rmse, 4),
                    'mape': round(mape, 4),
                }
        
        model_ranking = rank_models(aggregate_metrics)
        analysis['aggregate_metrics'] = aggregate_metrics
    
    return {
        'stocks': results,
        'model_ranking': model_ranking,
        'analysis': analysis,
    }
