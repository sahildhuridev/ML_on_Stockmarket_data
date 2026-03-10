"""
Feature Engineering Module
--------------------------
Generates technical indicator features from clean OHLCV data.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Generate ML-ready features from OHLCV data."""

    FEATURE_COLUMNS = ['MA7', 'MA21', 'RSI', 'daily_return', 'volatility']

    @staticmethod
    def generate(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicator columns to the DataFrame.

        Features generated:
            - MA7:          7-period simple moving average of Close
            - MA21:         21-period simple moving average of Close
            - RSI:          14-period Relative Strength Index
            - daily_return: Percentage change of Close
            - volatility:   21-period rolling standard deviation of daily returns

        Args:
            df: Cleaned OHLCV DataFrame.

        Returns:
            DataFrame with added feature columns. Warm-up NaN rows are dropped.
        """
        df = df.copy()

        close = df['Close']

        # Moving Averages
        df['MA7'] = close.rolling(window=7).mean()
        df['MA21'] = close.rolling(window=21).mean()

        # RSI (14-period)
        df['RSI'] = FeatureEngineer._compute_rsi(close, period=14)

        # Daily Return (%)
        df['daily_return'] = close.pct_change() * 100

        # Volatility (21-day rolling std of returns)
        df['volatility'] = df['daily_return'].rolling(window=21).std()

        # Drop warm-up NaN rows
        df = df.dropna()

        logger.info(f"Feature engineering complete: {len(df)} rows, features={FeatureEngineer.FEATURE_COLUMNS}")
        return df

    @staticmethod
    def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Compute RSI using exponential weighted moving average."""
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
