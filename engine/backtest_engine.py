from typing import List
from datetime import datetime
from typing import Optional
import logging
from engine.position import Position
from engine.trade import Trade
from engine.position_manager import PositionManager


logger = logging.getLogger(__name__)


class BacktestEngine:
    '''
    This module is used as the main orchestrator for integrating other modules and handling our strategy backtesting in one place.
    As of now it's connected with few other modules:

    - Position - simulates 'open' positions, assigns unique position_id and potentially triggers closing positions
    - PositionManager - similar as above, yet it manages multiple positions and logs them, the rest is the same
    - Trade - manages CLOSED positions, after a given position is triggered as closed, a Trade object is created based on the relevant attributes

    The current structure of the flow is quite clear, and in the end it should allow me to test multiple strategies and their performance if they were launched simultaneously.
    This is and always was the MAIN goal of creating this project, and we're not far from that.

    The current methods of the BacktestEngine:

    - open_position(self, ticker, side, entry, quantity, stop_loss, take_profit) -> returns a Position object + appends it to the position manager
    - process_price(self, ticker: str, current_price: float) -> returns a list of closed trades for a given ticker,
    based on the processed price, automatically creates trade objects for every closed trade and appends them to self.completed_trades list.
    
    - trades_by_strategy @26.02.26 - method used to group all trades based on their strategy for reporting, so we can see how different strats perform
    - strategy_report  @26.02.26 - self explanatory, reporting method for strategies

    Read-only properties:
    win_rate 
    total_pnl

    These are self-explanatory.

    Updated on 23.02.2026 (added this module-level docstring)
    '''
    
    def __init__(self):
        self.position_manager = PositionManager()
        self.completed_trades: List[Trade] = []
        self._win_rate = 0
        self._total_pnl = 0
        
        
    def __str__(self) -> str:
        """
        Return a summary like:
        BacktestEngine: 2 open | 3 closed | PnL: $1500.00
        """
        
        return f'{__class__.__name__}: {(self.position_manager.get_position_count())} open | {len(self.completed_trades)} closed | PnL: ${self.total_pnl}'
    
    def __repr__(self):
        return self.__str__()
        
        
    def open_position(self, 
                      ticker, 
                      side, 
                      entry, 
                      quantity, 
                      stop_loss, 
                      take_profit, 
                      strategy_id: Optional[str] = None, 
                      strategy_name: Optional[str] = None,
                      open_time: Optional[str] = None
                      ) -> Position:
        """
        Open a new position and add to manager.
        
        Args:
        ticker: str,
        side: str,
        entry_price: float, 
        quantity: float, 
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
        

        Returns:
            The created Position object
        """
        
        position = Position(ticker, side, entry, quantity, stop_loss, take_profit, strategy_id, strategy_name, open_time)
        self.position_manager.add_position(position)
        logger.info(f'@Strategy {position.strategy_name}: {position.strategy_id} Position {position.position_id}: {position.side} {position.ticker} @ {entry}')
        return position
        
    
    def process_price(self, ticker: str, current_price: float, candle_time: Optional[str] = None) -> List[Trade]:

        """
        Check all positions for a given ticker and given price.
        Close any that hit SL/TP and convert to Trade objects.

        Args:
        - ticker: str
        - current_price: float
        - candle_time: Optional[str]

        Returns:
            List of newly closed trades (empty if none closed)
        """

        closed_positions = self.position_manager.close_triggered_positions(ticker, current_price)
        logger.debug(f'Processing price for {ticker} at ${current_price}')
        newly_closed_trades = []
        for position in closed_positions:
            trade = Trade(
                          position[0].position_id,
                          position[0].ticker,
                          position[0].side,
                          position[0].entry_price,
                          current_price,
                          position[0].quantity,
                          stop_loss = position[0].stop_loss,
                          take_profit = position[0].take_profit,
                          exit_reason = position[1],
                          strategy_id = position[0].strategy_id,
                          strategy_name = position[0].strategy_name,
                          entry_time = position[0].open_time,
                          exit_time = candle_time,
                          )
            logger.info(f'@Strategy {position[0].strategy_id}, {position[0].strategy_name} || Position {trade.position_id} @ {position[0].ticker} closed with {trade.pnl} as a {position[1]}')
            newly_closed_trades.append(trade)
            self.completed_trades.append(trade)
            
        return newly_closed_trades
    
    def trades_by_strategy(self) -> dict[str, list[Trade]]:
        '''Method used to filter trades based on their strategy - it can be called explicitly and/or its return may be eventually added to Class attributes, 
        but for now it just returns the dict, and we will use it in strategy_report without adding extra Class attributes
        
        Args:
        None - we use the self.completed_trades from our Class instance
        
        Returns:
        A dict where each strategy_id represents a key, and its trades are represented as a list.
        
        e.g 
        
        {'432': [Trade(position_id='957d8746-f5c1-4c9e-93df-2342e2a316d6', ticker='EURUSD', side='BUY', entry_price=105.6, exit_price=104.2, quantity=10000, pnl=-14000.00, exit_reason='still open', strategy_id='432', strategy_name='Super XD'), 
        Trade(position_id='e14c1475-c77b-4683-90cd-fda6946f42dd', ticker='EURUSD', side='SELL', entry_price=105.6, exit_price=104.2, quantity=10000, pnl=14000.00, exit_reason='still open', strategy_id='432', strategy_name='Super XD')]}
        '''
        
        if not self.completed_trades:
            logger.info(f'There are no completed trades in self.completed_trades, and we cannot proceed with filtering them by the strategy.')
            return None
        else:
            strategies_set = set([(trade.strategy_id, trade.strategy_name) for trade in self.completed_trades])
            completed_trades_by_strategy = {}
            for strategy in strategies_set:
                filtered_trades = [trade for trade in self.completed_trades if trade.strategy_id == strategy[0]]
                completed_trades_by_strategy[strategy] = filtered_trades
            return completed_trades_by_strategy
        
    
    def process_tick(self, ticker: str, price: float, side: str, tick_time: Optional[str] = None) -> list:
        """
        Process a single tick against all open positions for a given ticker.

        Uses bid/ask side semantics to resolve SL/TP:
          - BUY position  SL: 'A' tick (aggressive seller) at price <= stop_loss
          - BUY position  TP: 'B' tick (aggressive buyer)  at price >= take_profit
          - SELL position SL: 'B' tick (aggressive buyer)  at price >= stop_loss
          - SELL position TP: 'A' tick (aggressive seller) at price <= take_profit

        Args:
            ticker: Instrument symbol.
            price: Tick price.
            side: 'B' (aggressive buyer) or 'A' (aggressive seller).
            tick_time: ISO timestamp string of the tick, used as exit_time on the trade.

        Returns:
            List of newly closed Trade objects (empty if none closed).
        """
        newly_closed: list = []
        triggered = []

        for position in list(self.position_manager.positions):
            if position.ticker != ticker:
                continue

            exit_reason: Optional[str] = None

            if position.side == 'BUY':
                if side == 'A' and price <= position.stop_loss:
                    exit_reason = 'Buy SL hit'
                elif side == 'B' and price >= position.take_profit:
                    exit_reason = 'Buy TP hit'
            elif position.side == 'SELL':
                if side == 'B' and price >= position.stop_loss:
                    exit_reason = 'Sell SL hit'
                elif side == 'A' and price <= position.take_profit:
                    exit_reason = 'Sell TP hit'

            if exit_reason:
                triggered.append((position, exit_reason))

        for position, exit_reason in triggered:
            self.position_manager.remove_position(position)
            trade = Trade(
                position.position_id,
                position.ticker,
                position.side,
                position.entry_price,
                price,
                position.quantity,
                stop_loss=position.stop_loss,
                take_profit=position.take_profit,
                exit_reason=exit_reason,
                strategy_id=position.strategy_id,
                strategy_name=position.strategy_name,
                entry_time=position.open_time,
                exit_time=tick_time,
            )
            logger.info(
                f'@Strategy {position.strategy_id}, {position.strategy_name} || '
                f'Position {trade.position_id} @ {position.ticker} closed at {price} ({side} tick) as {exit_reason}'
            )
            newly_closed.append(trade)
            self.completed_trades.append(trade)

        return newly_closed

    def force_close_all(self, ticker: str, strategy_id: str, price: float, candle_time: Optional[str] = None) -> None:
        '''Force close all open positions on a given ticker'''
        filtered_positions = [position for position in self.position_manager.positions if (ticker == position.ticker and position.strategy_id == strategy_id)]
        for position in filtered_positions:
            trade = Trade(
                          position.position_id,
                          position.ticker, 
                          position.side, 
                          position.entry_price,
                          price, 
                          position.quantity,
                          stop_loss = position.stop_loss,
                          take_profit = position.take_profit,
                          exit_reason = 'forced close',
                          strategy_id = position.strategy_id,
                          strategy_name = position.strategy_name,
                          entry_time = position.open_time,
                          exit_time = candle_time
                          )
            logger.info(f'@Strategy {position.strategy_id}, {position.strategy_name} || Position {trade.position_id} @ {position.ticker} closed with {trade.pnl} as a forced close')
            self.completed_trades.append(trade)
            self.position_manager.remove_position(position)
            
    
        
    def strategy_report(self):
        '''Method used to call trades_by_strategy method to get filtered trades and print out a report with stats for every strategy and portfolio total'''
        
        trades_filtered_by_strategy = self.trades_by_strategy()
        for strategy in trades_filtered_by_strategy:
            total_pnl = round(sum([trade.pnl for trade in trades_filtered_by_strategy[strategy]]), 2)
            win_rate = Trade.calculate_win_rate(trades_filtered_by_strategy[strategy])
            r_values = [trade.r_multiple for trade in trades_filtered_by_strategy[strategy] if trade.r_multiple is not None]
            avg_r_str = f'{sum(r_values) / len(r_values):.2f}R' if r_values else 'N/A'
            print(f'''{3* '-'} {strategy[1]} (ID: {strategy[0]}) {3* '-'}

                  Trades: {len(trades_filtered_by_strategy[strategy])}
                  Win Rate: {win_rate}%
                  Total PnL: ${total_pnl:.2f}
                  Avg R: {avg_r_str}

                  ''')
        print(f'''{3* '-'} PORTFOLIO TOTAL  {3* '-'}
                  
                  Trades: {len(self.completed_trades)}
                  Win Rate: {self.win_rate}%
                  Total PnL: ${self.total_pnl}
                  Avg R: {(lambda r: f'{sum(r)/len(r):.2f}R' if r else 'N/A')([t.r_multiple for t in self.completed_trades if t.r_multiple is not None])}
                  
                  ''')
        

 
    @property
    def total_pnl(self) -> float:
        """Sum of PnL from all completed trades."""
        self._total_pnl = round(sum([trade.pnl for trade in self.completed_trades]), 2)
        return self._total_pnl

    @property
    def win_rate(self) -> float:
        """Win rate using Trade.calculate_win_rate()."""
        self._win_rate = Trade.calculate_win_rate(self.completed_trades)
        return self._win_rate
    
    

if __name__ == '__main__':
    pass
###Outdated test, removed for now