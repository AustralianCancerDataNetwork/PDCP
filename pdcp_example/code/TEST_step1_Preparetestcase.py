# -*- coding: utf-8 -*-
"""
If there is a list of ids to be used, it can be used to update the ids for use.
Otherwise, all the ids in the orthanc server will be used.
"""

import pandas as pd

filename=''#location of the csv file that contains the ids
n1=pd.read_csv(filename)

pids=n1['hashsed_id'].unique().tolist()

idsfile='../ids/ids_test.csv'
n2=pd.read_csv(idsfile)

n3=n2.loc[n2['ids'].isin(pids)].reset_index(drop=True)

n3.to_csv('../ids/ids_test.csv',index=False)