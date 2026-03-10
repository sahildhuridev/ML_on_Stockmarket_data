"""
Data Ingestion Module
---------------------
Downloads historical OHLCV data from Yahoo Finance using yfinance.
This is the first stage of the ML pipeline.
"""

import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataIngestion:
    """Fetch historical stock data from Yahoo Finance."""

    @staticmethod
    def fetch(ticker: str, period: str = "30d", interval: str = "1h") -> pd.DataFrame:
        """
        Download historical data for a given ticker.

        Args:
            ticker: Stock symbol (e.g. 'AAPL')
            period: How far back to fetch (e.g. '30d', '90d', '1y')
            interval: Data granularity (e.g. '1h', '1d')

        Returns:
            DataFrame with OHLCV columns and DatetimeIndex.

        Raises:
            ValueError: If no data could be fetched.
        """
        logger.info(f"Ingesting data for {ticker} | period={period} interval={interval}")

        df = yf.download(ticker, period=period, interval=interval, progress=False)

        if df is None or df.empty:
            raise ValueError(f"No data returned by yfinance for ticker '{ticker}'")

        # Flatten multi-level columns if present (yfinance sometimes returns them)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        logger.info(f"Ingested {len(df)} rows for {ticker}")
        return df
