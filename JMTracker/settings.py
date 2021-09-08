import datetime
import os
import pandas as pd

"""
This file contains global setting for the project
and oher utility functions
"""

# global settings for the project
pwd = os.path.dirname(os.path.abspath(__file__))

settings = {
    # Paths
    'project_directory': pwd,
    'input_directory': os.path.abspath(os.path.join(pwd, '../inputs/')),
    'output_directory': os.path.abspath(os.path.join(pwd, '../output/')),
    'storage_directory': os.path.abspath(os.path.join(pwd, '../storage/')),
    # Project settings
    'today': datetime.date.today(),
    'author': 'Benjamin Vatter',
    # Basic url for requesting files from the AEA
    'AEA_url': 'https://www.aeaweb.org/joe/listings?issue=2021-02',
    # Basic url for requesting files from EJM
    'EJM_url': 'https://econjobmarket.org/users/positions/download/a',
    'EJM_login_url': 'https://econjobmarket.org/login/',
}

# Pandas configuration
pd.options.display.max_columns = 300
pd.options.display.max_rows = 100
pd.options.display.width = 150
