# -*- coding: utf-8 -*-
"""
This is an interceptor. It was used to keep only the records in the csv files with dates higher than november 2013 for specific patient values. 

The list is empty and it was left to the user to add this if he/she wants to use this interceptor.

"""

patients_ids=[]
import pandas as pd
from datetime import datetime
da=datetime(2013,11,1)
for p in patients_ids:
    df=pd.read_csv(f'../imagesummaries/{p}_SUCCESS.csv')
    df['n'] = pd.to_datetime(df['StudyDate'], format='%Y%m%d')
    df=df.loc[df['n']>da].reset_index(drop=True)
    df.to_csv(f'../imagesummaries/{p}_SUCCESS.csv',index=False)
    