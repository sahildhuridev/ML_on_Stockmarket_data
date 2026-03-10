"""
Data Validation Module
----------------------
Cleans and validates raw OHLCV data.
Handles missing values, duplicate timestamps, and data integrity.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Validate and clean raw market data."""

    @staticmethod
    def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        """
        Clean the ingested DataFrame.

        Steps:
            1. Ensure the index is a DatetimeIndex
            2. Sort by timestamp
            3. Remove duplicate timestamps
            4. Drop rows where ALL price columns are NaN
            5. Forward-fill remaining NaNs
            6. Drop any remaining NaN rows (at the very start)

        Args:
            df: Raw OHLCV DataFrame from ingestion.

        Returns:
            Tuple of (cleaned DataFrame, validation report dict).

        Raises:
            ValueError: If DataFrame is empty after cleaning.
        """
        report = {
            "original_rows": len(df),
            "issues": [],
        }

        # 1. Ensure DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
                report["issues"].append("Converted index to DatetimeIndex")
            except Exception:
                raise ValueError("Could not convert index to DatetimeIndex")

        # 2. Sort
        df = df.sort_index()

        # 3. Remove duplicate timestamps
        duplicates = df.index.duplicated(keep='first')
        if duplicates.any():
            n_dup = int(duplicates.sum())
            df = df[~duplicates]
            report["issues"].append(f"Removed {n_dup} duplicate timestamps")

        # 4. Drop all-NaN price rows
        price_cols = [c for c in ['Open', 'High', 'Low', 'Close'] if c in df.columns]
        if price_cols:
            all_nan_mask = df[price_cols].isna().all(axis=1)
            n_all_nan = int(all_nan_mask.sum())
            if n_all_nan:
                df = df[~all_nan_mask]
                report["issues"].append(f"Dropped {n_all_nan} all-NaN rows")

        # 5. Forward-fill
        n_nan_before = int(df.isna().sum().sum())
        df = df.ffill()
        n_filled = n_nan_before - int(df.isna().sum().sum())
        if n_filled:
            report["issues"].append(f"Forward-filled {n_filled} NaN values")

        # 6. Drop remaining NaNs (start of series)
        df = df.dropna()

        report["cleaned_rows"] = len(df)
        report["rows_removed"] = report["original_rows"] - report["cleaned_rows"]

        if df.empty:
            raise ValueError("DataFrame is empty after validation/cleaning")

        logger.info(
            f"Validation complete: {report['original_rows']} → {report['cleaned_rows']} rows "
            f"({len(report['issues'])} issues fixed)"
        )
        return df, report
