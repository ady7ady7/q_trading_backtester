from .base_strategy import BaseStrategy
from datetime import datetime, time
import pandas as pd

class LPPStrategy(BaseStrategy):
    '''A class with abstract method used to generate trading signal'''
    def __init__(self, ticker, side: str = None, entry: str = None, sl: str = None, tp: str = None):
        super().__init__(f'LPP Strategy')
        self.ticker = ticker
        self.side = side
        self.entry = entry
        self.sl = sl
        self.tp = tp
        self.levels_by_date: dict = {}
        
    def generate_signal(self, row: pd.Series, current_date) -> str:
        '''Generates trade signals based on specified levels and direction set in init.
        Entry fires only when this candle's range actually touches the entry level,
        regardless of which direction price approached from.
        '''
        levels = self.levels_by_date.get(current_date)
        if not levels:
            return 'HOLD'
        entry_level = levels[self.entry]
        if row['low'] <= entry_level <= row['high']:
            return self.side
        return 'HOLD'
    
    def get_entry(self, row: pd.Series, current_date) -> float:
        return self.levels_by_date[current_date][self.entry]
    
    def get_sl(self, row: pd.Series, current_date) -> float:
        return self.levels_by_date[current_date][self.sl]

    def get_tp(self, row: pd.Series, current_date) -> float:
        return self.levels_by_date[current_date][self.tp]
    
    def session_start(self) -> time:
        return time(10, 0)

    def session_end(self) -> time:
        return time(17, 30)

    def prepare(self, df: pd.DataFrame) -> None:
        '''Run once before backtest. Computes LPP levels for every trading day.'''
        times = df['candle_open'].apply(lambda x: datetime.fromisoformat(x).time())
        dates = df['candle_open'].apply(lambda x: datetime.fromisoformat(x).date())

        window_mask = (times >= time(9, 0)) & (times < time(10, 0))
        window_df = df[window_mask]

        for day_date, day_df in window_df.groupby(dates[window_df.index]):
            high = day_df['high'].max()
            low = day_df['low'].min()
            close = day_df['close'].iloc[-1]

            lpp = (high + low + close) / 3
            lr1 = (2 * lpp) - low
            ls1 = (2 * lpp) - high
            lr2 = lpp + (high - low)
            ls2 = lpp - (high - low)
            lr3 = high + 2 * (lpp - low)
            ls3 = low - 2 * (high - lpp)

            levels = {
                'LPP': lpp,
                'LR1': lr1, 'LR2': lr2, 'LR3': lr3,
                'LS1': ls1, 'LS2': ls2, 'LS3': ls3,
            }

            # Sub-levels between each adjacent pair
            pairs = [
                ('LS3', 'LS2'), ('LS2', 'LS1'), ('LS1', 'LPP'),
                ('LPP', 'LR1'), ('LR1', 'LR2'), ('LR2', 'LR3'),
            ]
            for lo_key, hi_key in pairs:
                lo = levels[lo_key]
                dist = levels[hi_key] - lo
                levels[f'{lo_key}_{hi_key}_025'] = lo + 0.25 * dist
                levels[f'{lo_key}_{hi_key}_050'] = lo + 0.50 * dist
                levels[f'{lo_key}_{hi_key}_075'] = lo + 0.75 * dist

            self.levels_by_date[day_date] = levels


        