# -*- coding: utf-8 -*-
"""
Select the patient ids to prepare and process
"""

import pandas as pd
#reload the csv file from the first step
filename='../ids/final_ids_remoteorthanc.csv'#location of the csv file that contains the ids
n1=pd.read_csv(filename)

#select the head and neck cancer data
n1=n1.loc[n1['ids'].str.contains('HN-')].reset_index(drop=True)
#select the first 5 patients for as example
n1=n1.head(5)
#save the csv file.
n1.to_csv('../ids/hn_ids_test.csv',index=False)