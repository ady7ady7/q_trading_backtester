"""Tick data loader for AlgoBacktest — loads and indexes trade-level tick data."""

from typing import Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class TickDataLoader:
    """
    Loads raw tick data from CSV and indexes it by date for fast per-day access.

    Args:
        file_path: Path to the raw CSV file.
        timestamp_col: Name of the timestamp column to parse (e.g. 'ts_recv_berlin', 'ts_recv_et').
        timezone: Target timezone for conversion (e.g. 'Europe/Berlin', 'America/New_York').

    We keep only: datetime (from timestamp_col), price, side.
    Side values: 'B' = aggressive buyer (lifted ask), 'A' = aggressive seller (hit bid), 'N' = ignore.

    Attributes:
        ticks_by_date: dict mapping date -> DataFrame(datetime, price, side), sorted by datetime.
    """

    def __init__(self, file_path: str, timestamp_col: str = 'ts_recv_berlin', timezone: str = 'Europe/Berlin') -> None:
        self.file_path = file_path
        self.timestamp_col = timestamp_col
        self.timezone = timezone
        self.ticks_by_date: dict[object, pd.DataFrame] = {}

    def __repr__(self) -> str:
        return f'TickDataLoader(file_path={self.file_path!r}, dates_loaded={len(self.ticks_by_date)})'

    def load_and_index(self) -> bool:
        """
        Load the CSV, parse the timestamp column, and build a per-date index.

        Only keeps rows where side is 'B' or 'A' (drops 'N' and any other values).

        Returns:
            True if loading succeeded, False otherwise.
        """
        try:
            logger.info(f'Loading tick data from {self.file_path}...')
            df = pd.read_csv(
                self.file_path,
                usecols=[self.timestamp_col, 'price', 'side'],
                dtype={'price': float, 'side': str},
            )

            df['datetime'] = pd.to_datetime(df[self.timestamp_col], utc=True).dt.tz_convert(self.timezone)
            df = df.drop(columns=[self.timestamp_col])

            df = df[df['side'].isin(['B', 'A'])].copy()

            df['date'] = df['datetime'].dt.date
            df = df[['date', 'datetime', 'price', 'side']].sort_values('datetime')

            for date, group in df.groupby('date'):
                self.ticks_by_date[date] = group[['datetime', 'price', 'side']].reset_index(drop=True)

            logger.info(f'Tick data indexed: {len(self.ticks_by_date)} trading days loaded.')
            return True

        except FileNotFoundError:
            logger.error(f'Tick data file not found: {self.file_path}')
            return False
        except Exception as e:
            logger.error(f'Failed to load tick data: {e}')
            return False

    def get_ticks_for_day(self, date: object) -> Optional[pd.DataFrame]:
        """
        Return the tick DataFrame for a given date, or None if not available.

        Args:
            date: datetime.date object.

        Returns:
            DataFrame with columns [datetime, price, side] sorted ascending, or None.
        """
        return self.ticks_by_date.get(date)

    def get_session_ticks(self, date: object, start, end) -> Optional[pd.DataFrame]:
        """
        Return ticks for a given date filtered to a session time window.

        Args:
            date: datetime.date object.
            start: datetime.time — session start (inclusive).
            end: datetime.time — session end (inclusive).

        Returns:
            Filtered DataFrame with columns [datetime, price, side], or None if empty.
        """
        day_ticks = self.get_ticks_for_day(date)
        if day_ticks is None:
            return None
        tick_time = day_ticks['datetime'].dt.time
        mask = (tick_time >= start) & (tick_time <= end)
        result = day_ticks[mask].reset_index(drop=True)
        return result if not result.empty else None
