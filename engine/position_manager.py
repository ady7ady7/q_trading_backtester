'''
A class used to handle multiple positions
'''


from typing import List
from engine.position import Position


class PositionManager:
    """
    Manages multiple open positions.

    Attributes:
        positions: List of currently open Position objects.
    """

    def __init__(self) -> None:
        """Initialize empty position manager."""
        self.positions: List[Position] = []
    
        
    def add_position(self, position: Position) -> None:
        """
        Add a new position to the manager.

        Args:
            position: Position object to add.
        """
        
        self.positions.append(position)
        print(f'Position {position} added successfully')
        
    def remove_position(self, position: Position) -> None:
        '''Remove a position from a manager e.g. a forced close
        
        Args:
            position: Position object to remove
        '''
        
        self.positions.remove(position)
        print(f'Position {position} removed successfully')
        

    def get_total_pnl(self, current_price: float) -> float:
        """
        Calculate total unrealized P&L for all positions.

        Args:
            current_price: Current market price.

        Returns:
            Sum of all position P&Ls.
        """
        
        total_pnl = sum([position.calculate_pnl(current_price) for position in self.positions])
        if total_pnl is not None:
            return total_pnl
        else:
            return 0.0

    def close_triggered_positions(self, ticker: str, current_price: float) -> List[Position]:
        """
        Check all positions for SL/TP triggers and remove them.

        Args:
            current_price: Current market price.

        Returns:
            List of positions that should be closed.
        """
        closed_positions = [(p, p.should_close(current_price)[1]) for p in self.positions if p.ticker == ticker and p.should_close(current_price)[0]]

        closed_ids = [p[0].position_id for p in closed_positions]
        self.positions = [p for p in self.positions if p.position_id not in closed_ids]

        return closed_positions
    
                
    def get_positions_by_ticker(self, ticker: str) -> List[Position]:
        '''Returns all positions that match a given ticker'''
        matching_positions = [p for p in self.positions if p.ticker == ticker]
        return matching_positions
    
    def get_position_count(self) -> int:
        """Return number of open positions."""
        return len(self.positions)

    def __repr__(self) -> str:
        """Return unambiguous representation."""
        return f"PositionManager(positions={len(self.positions)})"

    def __str__(self) -> str:
        """Return user-friendly representation."""
        if not self.positions:
            return "PositionManager: No open positions"
        return f"PositionManager: {len(self.positions)} open positions"
    
    

