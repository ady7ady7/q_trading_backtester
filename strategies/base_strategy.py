
'''Abstract Method Class - base strategy'''

from abc import ABC, abstractmethod
from datetime import time
import pandas as pd
import uuid
    

class BaseStrategy(ABC):
    '''A class with abstract method used to generate trading signal'''
    def __init__(self, name: str):
        self.name = name
        self.strategy_id = str(uuid.uuid4())
        
    @abstractmethod
    def generate_signal(self, row: pd.Series, current_date) -> str:
        pass
    
    @abstractmethod
    def session_start(self) -> time | None: ...

    @abstractmethod  
    def session_end(self) -> time | None: ...
    
    def get_sl(self, row: pd.Series, current_date) -> float:
        '''Override to give dynamic SL. This is just default.'''
        return row['open'] - 50


    def get_tp(self, row: pd.Series, current_date) -> float:
        '''Override to provide dynamic TP. This is just default.'''
        return row['open'] + 50
        

    def get_name(self) -> str:
        '''inherited method to fetch a given strategy name'''
        return self.name
    
    def prepare(self, df: pd.DataFrame) -> None:
        '''Optionally pre-calculate daily values for relevant levels for a given strategy. Default is None'''
        pass