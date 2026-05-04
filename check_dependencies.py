

'''Module used to check dependencies'''

def check_deps():
    try:
        import pandas as pd
        import numpy as np
        
    except ImportError as e:
        print(f'Import error: {str(e)}')
    except ModuleNotFoundError as e:
        print(f'Module not found: {str(e)}')
    except Exception as e:
        print(f'Unexpected error: {str(e)}')
        
    else:
        print('Imports succeeded!')
        print(f'Pandas version: {pd.__version__}')
        print(f'Numpy version: {np.__version__}')