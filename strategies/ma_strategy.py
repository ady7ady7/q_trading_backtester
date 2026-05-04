
from .base_strategy import BaseStrategy
from typing import List

class MovingAverageStrategy(BaseStrategy):
    
    def __init__(self, ma_period: int):
        '''Initialization of the class, inheriting the base init from the BaseStrategy and extending it'''
        super().__init__(f'MovingAverage Strategy')
        self.ma_period = ma_period
        self.price_history: List[float] = []
    
    def add_price(self, price: float):
        '''Method used to add a price to the self.price_history list'''
        self.price_history.append(price)
        if len(self.price_history) > self.ma_period:
            self.price_history = self.price_history[-self.ma_period:]

            
    def generate_signal(self, price: float) -> str:
        '''Method used to check whether the list has enough entries to be able to calculate the MA properly'''
        
        self.price_history.append(price)
        if len(self.price_history) < self.ma_period:
            print(f'Not enough data entries to properly count ma {self.ma_period}. Currently we only have {len(self.price_history)} entries.')
            return 'HOLD'
        else:
            self.price_history = self.price_history[-self.ma_period:]
            ma_value = sum(self.price_history) / self.ma_period
            
            if price > ma_value:
                return 'BUY'
            elif price == ma_value:
                return 'HOLD'
            else: 
                return 'SELL'        