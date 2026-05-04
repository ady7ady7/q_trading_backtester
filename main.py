

'''

This is the main.py for my professional backtesting framework for algotrading strategies
I'm working on this project as a part of my daily Python PCAP practice routine, using the small steps methodology

'''

import logging
import sys
from __init__ import __version__
import check_dependencies
import pandas as pd
from datetime import datetime, time
from typing import Literal

from engine.backtest_engine import BacktestEngine
from data.data_loader import DataLoader
from data.tick_data_loader import TickDataLoader
from strategies.vwap_strategy import VwapStrategy
from strategies.lpp_strategy import LPPStrategy

BACKTEST_MODE = Literal['SL_TP', 'CONDITION_CLOSE']

def setup_logging():
    logger = logging.getLogger() #root logger, not __main__
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter('%(asctime)s [%(levelname)-8s] %(name)s: %(message)s')
    stream_handler.setFormatter(fmt)

    logger.addHandler(stream_handler)

    logger.debug('Logging in main initialized.')


def _entry_tick_matches(price: float, side: str, signal: str, entry_level: float) -> bool:
    """
    Return True if this tick qualifies as an entry for the given signal direction.

    BUY  entry: 'A' tick (aggressive seller hits our bid) at price <= entry_level
    SELL entry: 'B' tick (aggressive buyer lifts our ask) at price >= entry_level
    """
    if signal == 'BUY':
        return side == 'A' and price <= entry_level
    if signal == 'SELL':
        return side == 'B' and price >= entry_level
    return False


def run_backtest(
    df: pd.DataFrame,
    strategies: list,
    tick_loader: TickDataLoader,
    mode: BACKTEST_MODE = 'CONDITION_CLOSE',
) -> BacktestEngine:
    """
    Run a backtest over all strategies against the provided OHLC and tick data.

    Args:
        df: OHLC DataFrame, one row per minute candle.
        strategies: List of strategy instances to run simultaneously.
        tick_loader: Pre-loaded TickDataLoader instance.
        mode: 'SL_TP' — positions exit via SL/TP hits (ticks), with force_close as
              deadline safety net at session end.
              'CONDITION_CLOSE' — SL/TP are ignored entirely; positions always exit
              via force_close at session end. R metrics will be None for all trades.
    """
    backtest_engine = BacktestEngine()
    current_positions = {strategy: None for strategy in strategies}
    traded_today = {strategy: None for strategy in strategies}

    for strategy in strategies:
        strategy.prepare(df)

    dates = sorted(df['candle_open'].apply(lambda x: datetime.fromisoformat(x).date()).unique())

    for current_date in dates:
        day_mask = df['candle_open'].apply(lambda x: datetime.fromisoformat(x).date()) == current_date
        day_df = df[day_mask]

        session_ticks = None
        for strategy in strategies:
            start = strategy.session_start()
            end = strategy.session_end()
            if start is not None and session_ticks is None:
                session_ticks = tick_loader.get_session_ticks(current_date, start, end)

        for _, row in day_df.iterrows():
            t = datetime.fromisoformat(row['candle_open']).time()

            for strategy in strategies:
                start = strategy.session_start()
                end = strategy.session_end()
                is_rth = (start is None) or (start <= t <= end)
                session_ending = end is not None and t > end

                if session_ending and current_positions[strategy] is not None:
                    backtest_engine.force_close_all(
                        'FDAX',
                        strategy.strategy_id,
                        price=row['open'],
                        candle_time=row['candle_close'],
                    )
                    current_positions[strategy] = None
                    continue

                if is_rth and traded_today[strategy] != current_date and current_positions[strategy] is None:
                    signal = strategy.generate_signal(row, current_date)

                    if signal in ('BUY', 'SELL'):
                        entry_level = strategy.get_entry(row, current_date)
                        candle_open_time = datetime.fromisoformat(row['candle_open']).time()
                        candle_close_time = datetime.fromisoformat(row['candle_close']).time()

                        if session_ticks is None:
                            continue

                        candle_tick_time = session_ticks['datetime'].dt.time
                        candle_ticks = session_ticks[
                            (candle_tick_time >= candle_open_time) &
                            (candle_tick_time <= candle_close_time)
                        ]

                        entry_tick = None
                        entry_idx = None
                        for tick_row in candle_ticks.itertuples():
                            if _entry_tick_matches(tick_row.price, tick_row.side, signal, entry_level):
                                entry_tick = tick_row
                                entry_idx = tick_row.Index
                                break

                        if entry_tick is None:
                            continue

                        sl = strategy.get_sl(row, current_date) if mode == 'SL_TP' else None
                        tp = strategy.get_tp(row, current_date) if mode == 'SL_TP' else None

                        backtest_engine.open_position(
                            'FDAX',
                            signal,
                            entry=strategy.get_entry(row, current_date),
                            quantity=1,
                            stop_loss=sl,
                            take_profit=tp,
                            strategy_id=strategy.strategy_id,
                            strategy_name=strategy.get_name(),
                            open_time=entry_tick.datetime.isoformat(),
                        )
                        current_positions[strategy] = True
                        traded_today[strategy] = current_date

                        if mode == 'SL_TP':
                            remaining_ticks = session_ticks.loc[entry_idx + 1:]
                            for tick_row in remaining_ticks.itertuples(index=False):
                                newly_closed = backtest_engine.process_tick(
                                    'FDAX',
                                    tick_row.price,
                                    tick_row.side,
                                    tick_time=tick_row.datetime.isoformat(),
                                )
                                if newly_closed:
                                    current_positions[strategy] = None
                                    break

        for strategy in strategies:
            if current_positions[strategy] is not None:
                backtest_engine.force_close_all(
                    'FDAX',
                    strategy.strategy_id,
                    price=day_df.iloc[-1]['close'],
                    candle_time=day_df.iloc[-1]['candle_close'],
                )
                current_positions[strategy] = None

    return backtest_engine


if __name__ == '__main__':

    x = DataLoader('algo_backtest\data\FDAX_M1_OHLC.csv')
    print(x)
    data = x.load_data()
    x.validate_data(data)
    print(len(data))
    print(data.head(3))

    setup_logging()
    print('Starting the backtest test procedure in main.py - logging set!')

    tick_loader = TickDataLoader('algo_backtest\data\FDAX_trades_raw.csv')
    tick_loader.load_and_index()

                    #ticker #entry #sl #tp
    strategies = [
                LPPStrategy('FDAX', 'BUY', 'LR1_LR2_025', 'LPP_LR1_050', 'LR2'), #4
                LPPStrategy('FDAX', 'SELL', 'LS2', 'LS2_LS1_050', 'LS3'), #6
                LPPStrategy('FDAX', 'SELL', 'LR2', 'LR3', 'LPP'), #7
                LPPStrategy('FDAX', 'SELL', 'LR2_LR3_075', 'LR3', 'LR1'), #8
                LPPStrategy('FDAX', 'SELL', 'LS2_LS1_025', 'LS2_LS1_050', 'LS3'), #10 BEZ FILTRA modyfikowany S3
                LPPStrategy('FDAX', 'SELL', 'LS2_LS1_025', 'LS2_LS1_075', 'LS3_LS2_075') #11
                  ]
    test_engine = run_backtest(data, strategies, tick_loader, mode='CONDITION_CLOSE')
    print(test_engine)
    test_engine.strategy_report()

    for trade in test_engine.completed_trades[::10]:
        print(trade)
