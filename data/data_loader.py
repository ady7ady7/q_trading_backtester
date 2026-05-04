

'''
Data loading module for AlgoBacktest
'''


from typing import Optional
import pandas as pd


class DataLoader:
    '''
    Class used to load and validate data
    
    Attributes:
        file_path: path to the csv file with trading data
    
    '''

    def __init__(self, file_path: str) -> None:
        '''Initialize the DataLoader class with file path'''
        print('DataLoader initialized.')
        self.filepath = file_path
        self.columns = []
        
    def __repr__(self):
        '''
        Unambiguous representation
        '''
        return f'DataLoader(filepath = {self.filepath})'

    
    
    def load_data(self) -> Optional[pd.DataFrame]:
        '''
        Load CSV data with error handling.

        Returns:
            DataFrame with columns as in the file - used to be: timestamp, ticker, open, high, low, close, volume (and DF index).
            The current representation of columns might differ depending on the actual data scheme. It can be read by printing the columns attribute after using load_data. e.g.
            x = DataLoader('ohlc_mock_data.csv')  -> x.load_data() -> print(x.columns)
            Returns None if file not found.

        Raises:
            ValueError: If CSV format is invalid or missing required columns.
            FileNotFoundError: If file is missing or file name is wrong.
            Pandas Parser Error: If there are any issues with data parsing.
        '''
        
        try:
            with open(self.filepath, 'r') as f:
                data = pd.read_csv(f)
                #data.columns = ['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume'] #REMOVED FOR NOW
                self.columns = [column for column in data.columns] #replaced hardcoded columns with the actual columns from a given data source
    
        
        except FileNotFoundError as e:
            print(f'File not found: {str(e)}')
            return None
        except ValueError as e:
            print(f'Value Error! {str(e)}')
            return None
        except pd.errors.ParserError as e:
            print(f'Pandas Parser Error: {str(e)}')
            return None
        except Exception as e:
            print(f'Unexpected error: {str(e)}')
            return None
            
        else:
            print('Data loading succeeded')
            return data
        
        finally:
            print('Data loading operation ended.')
    
    
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        '''
        Method used to check whether all rows/columns are valid.
        
        checks if:
        #########- all the columns are in the dataframe #REMOVED - USELESS NOW, WE'RE SIMPLY GETTING THE COLUMNS FROM EACH FILE INSTEAD
        - there are no missing values
        - High price in every row is higher than Low price
        
        Args:
        - df - Pandas Dataframe with columns - columns are not hardcoded anymore
        
        Returns:
        - is_valid - True/False, depending on the results of the check
        '''
        
        ###req_columns = ['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume'] - removed, check above
        is_valid = True
        
        
        # missing_columns = set(req_columns) - set(df.columns)
        # if missing_columns:
        #     print(f'Missing columns: {missing_columns}')
        #     is_valid = False
                
        nan_values = df[self.columns].isna().sum()
        if nan_values.any() > 0:
            print(f'Missing values found: {len(nan_values)}')
            is_valid = False
            
        invalid_rows = df[df['high'] < df['low']] #we're assuming that high and low columns are there, but I'll leave it for now, as it SHOULD be the case in every df
        if not invalid_rows.empty:
            print(f'Found {len(invalid_rows)} invalid rows: {invalid_rows}')
            is_valid = False
            
        return is_valid
    
    
    def get_candle_count(self) -> int:
       """
       Return total number of candles in loaded data.

       Returns:
           Number of rows in DataFrame, or 0 if data not loaded.
       """
       
       data = self.load_data()
       
       if data is not None:
           return len(data)
       else:
           return 0
    
    
    def get_bullish_candles(self, data: pd.DataFrame) -> pd.DataFrame:
       """
       Return only bullish candles (close > open).

       Args:
           data: OHLC DataFrame.

       Returns:
           Filtered DataFrame with only bullish candles.
       """
       
       bullish_candles = data[data['close'] > data['open']]
       return bullish_candles
       