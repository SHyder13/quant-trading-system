"""databento_loader.py
Utility for loading historical OHLCV data from Databento *.dbn files so that it can
be fed directly into the existing back-testing pipeline.

Why a dedicated loader?
-----------------------
The rest of the codebase expects a pandas DataFrame that:
1. Has a timezone-aware DatetimeIndex (UTC).
2. Is sorted in ascending order.
3. Contains at least the columns: ``open``, ``high``, ``low``, ``close``, ``volume``.
4. Optionally includes any extra fields supplied by Databento – they will simply be
   ignored by downstream components.

This wrapper fulfils those requirements while hiding the low-level details of
Databento's SDK from the rest of the application.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Union

import pandas as pd

try:
    from databento import DBNStore
except ImportError as exc:  # pragma: no cover – improves DX if sdk is missing
    raise ImportError(
        "The `databento` package is required for DatabentoLoader. Run\n"
        "   pip install databento\n"
        "and ensure your virtualenv is activated." 
    ) from exc


class DatabentoLoader:
    """Loads OHLCV data from pre-downloaded Databento *.dbn files.

    Parameters
    ----------
    api_key
        Your Databento API key – currently unused for file reads but stored for
        future live requests.
    file_paths
        Mapping of *symbol* -> *absolute path* to that symbol's *.dbn* file.
        Example::
            {
                "MES": "/data/databento/mes_ohlcv_1m.dbn",
                "MNQ": "/data/databento/mnq_ohlcv_1m.dbn",
            }
    """

    def __init__(self, api_key: str, file_paths: Dict[str, Union[str, Path]]):
        self.api_key = api_key
        # Normalise to Path objects
        self._file_paths: Dict[str, Path] = {
            sym: Path(p) for sym, p in file_paths.items()
        }

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def load_data(
        self,
        symbol: str,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        timeframe: str = "1m",
    ) -> pd.DataFrame:
        """Return historical bars for *symbol* between *start_date* and *end_date*.

        The ``timeframe`` argument currently supports minute granularities.
        If the requested timeframe is coarser than the source data (e.g. 2m
        whilst the DBN file contains 1m), the loader will *down-sample* using
        pandas' *ohlc* aggregation.
        """
        file_path = self._file_paths.get(symbol.upper())
        if file_path is None:
            raise FileNotFoundError(
                f"No Databento file path configured for symbol '{symbol}'."
            )
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        # ------------------------------------------------------------------
        # 1. Read DBN file → DataFrame
        # ------------------------------------------------------------------
        # DBNStore is the modern replacement for the deprecated `Reader` class
        store = DBNStore.from_file(file_path)
        df = store.to_df()

        # If Databento included a human-readable symbol column we can filter
        if "symbol" in df.columns:
            # Match all contracts that start with the base symbol (e.g., "MNQ" matches "MNQU0", "MNQZ0", etc.)
            df = df[df["symbol"].str.upper().str.startswith(symbol.upper())]
        elif "publisher_id" in df.columns or "instrument_id" in df.columns:
            # Multi-instrument file without plain symbol. In that case we keep
            # everything – the calling back-tester should only request the
            # loader once per symbol so caching keeps things fast.  This can be
            # refined later by loading symbology.json.
            pass

        # ------------------------------------------------------------------
        # 2. Basic cleaning / normalisation
        # ------------------------------------------------------------------
        # DBNStore.to_df() already returns a DataFrame with a DatetimeIndex,
        # so we just need to ensure it's sorted.
        df.sort_index(inplace=True)

        # Drop any non-price columns to keep downstream code simple
        extra_cols = [c for c in df.columns if c.lower() not in ["open","high","low","close","volume"]]
        df.drop(columns=extra_cols, inplace=True, errors="ignore")

        # Keep a consistent column order
        required_cols = ["open", "high", "low", "close", "volume"]
        df = df[required_cols]

        # ------------------------------------------------------------------
        # 3. Optional resampling (e.g. 2-minute bars)
        # ------------------------------------------------------------------
        if timeframe and timeframe.lower() != "1m":
            if timeframe.endswith("m"):
                minutes = int(timeframe.rstrip("m"))
                df = df.resample(f"{minutes}min").agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                ).dropna()
            else:
                raise ValueError(
                    "DatabentoLoader currently supports only minute timeframes."
                )

        # ------------------------------------------------------------------
        # 4. Date slicing – keep only requested window
        # ------------------------------------------------------------------
        mask = (df.index >= pd.to_datetime(start_date, utc=True)) & (
            df.index <= pd.to_datetime(end_date, utc=True)
        )
        return df.loc[mask].copy()
