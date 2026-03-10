"""
Model Training Module
---------------------
Trains multiple ML models (Linear Regression, ARIMA, LSTM)
on feature-engineered stock data.
"""

import numpy as np
import pandas as pd
import logging
import warnings

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


class ModelTrainer:
    """Train multiple ML models and return predictions."""

    MIN_LSTM_SAMPLES = 60  # Minimum rows needed to train LSTM
    LSTM_SEQUENCE_LENGTH = 10

    @staticmethod
    def train(df: pd.DataFrame, feature_columns: list[str]) -> dict:
        """
        Train Linear Regression, ARIMA, and optionally LSTM.

        Args:
            df: Feature-enriched DataFrame (must have 'Close' + feature_columns).
            feature_columns: List of column names to use as features.

        Returns:
            Dict of {model_name: {"model": model_obj, "predictions": np.array,
                                   "y_test": np.array, "params": dict}}
        """
        results = {}

        close = df['Close'].values.flatten()
        n = len(close)
        split = int(n * 0.8)

        if split < 5:
            raise ValueError(f"Not enough data to train (only {n} rows)")

        # ── Linear Regression ──────────────────────────────────────────
        try:
            lr_result = ModelTrainer._train_linear_regression(
                df, feature_columns, split
            )
            results['LinearRegression'] = lr_result
            logger.info("Linear Regression training complete")
        except Exception as e:
            logger.warning(f"Linear Regression failed: {e}")

        # ── ARIMA ──────────────────────────────────────────────────────
        try:
            arima_result = ModelTrainer._train_arima(close, split)
            results['ARIMA'] = arima_result
            logger.info("ARIMA training complete")
        except Exception as e:
            logger.warning(f"ARIMA failed: {e}")

        # ── LSTM (only if enough data) ─────────────────────────────────
        if n >= ModelTrainer.MIN_LSTM_SAMPLES:
            try:
                lstm_result = ModelTrainer._train_lstm(close, split)
                results['LSTM'] = lstm_result
                logger.info("LSTM training complete")
            except Exception as e:
                logger.warning(f"LSTM failed: {e}")
        else:
            logger.info(f"Skipping LSTM — only {n} rows (need {ModelTrainer.MIN_LSTM_SAMPLES})")

        if not results:
            raise ValueError("All models failed to train")

        return results

    # ── Private helpers ────────────────────────────────────────────────

    @staticmethod
    def _train_linear_regression(df, feature_columns, split):
        available = [c for c in feature_columns if c in df.columns]
        X = df[available].values
        y = df['Close'].values.flatten()

        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        return {
            "model": model,
            "predictions": preds,
            "y_test": y_test,
            "params": {
                "model_type": "LinearRegression",
                "features": available,
                "train_size": split,
                "test_size": len(y_test),
            },
        }

    @staticmethod
    def _train_arima(close, split):
        from statsmodels.tsa.arima.model import ARIMA

        train, test = close[:split], close[split:]

        model = ARIMA(train, order=(5, 1, 0))
        fitted = model.fit()

        preds = fitted.forecast(steps=len(test))

        return {
            "model": fitted,
            "predictions": np.array(preds),
            "y_test": test,
            "params": {
                "model_type": "ARIMA",
                "order": "(5,1,0)",
                "train_size": split,
                "test_size": len(test),
            },
        }

    @staticmethod
    def _train_lstm(close, split):
        import os
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Input

        seq_len = ModelTrainer.LSTM_SEQUENCE_LENGTH

        # Scale
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = scaler.fit_transform(close.reshape(-1, 1))

        # Create sequences
        X_seq, y_seq = [], []
        for i in range(seq_len, len(scaled)):
            X_seq.append(scaled[i - seq_len:i, 0])
            y_seq.append(scaled[i, 0])
        X_seq = np.array(X_seq)
        y_seq = np.array(y_seq)

        # Adjust split for sequence offset
        adj_split = split - seq_len
        if adj_split < 5:
            raise ValueError("Not enough data for LSTM sequences after split")

        X_train = X_seq[:adj_split].reshape(-1, seq_len, 1)
        y_train = y_seq[:adj_split]
        X_test = X_seq[adj_split:].reshape(-1, seq_len, 1)
        y_test_scaled = y_seq[adj_split:]

        # Build model
        model = Sequential([
            Input(shape=(seq_len, 1)),
            LSTM(50, return_sequences=True),
            LSTM(50),
            Dense(1),
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(X_train, y_train, epochs=10, batch_size=16, verbose=0)

        # Predict
        preds_scaled = model.predict(X_test, verbose=0).flatten()
        preds = scaler.inverse_transform(preds_scaled.reshape(-1, 1)).flatten()
        y_test = scaler.inverse_transform(y_test_scaled.reshape(-1, 1)).flatten()

        return {
            "model": model,
            "predictions": preds,
            "y_test": y_test,
            "params": {
                "model_type": "LSTM",
                "sequence_length": seq_len,
                "epochs": 10,
                "batch_size": 16,
                "lstm_units": 50,
                "train_size": adj_split,
                "test_size": len(y_test),
            },
            "_scaler": scaler,
        }
