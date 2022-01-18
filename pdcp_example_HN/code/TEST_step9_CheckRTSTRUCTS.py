# -*- coding: utf-8 -*-
"""
For this script, read all the organs in all the rtstructs associated with the studies (just reviewing patient details)

At somepoint, you might want to deleted these structures from the orthanc server.

@author: 60183647
"""
import os
import pandas as pd
westmeadsummaries='../imagesummaries/'

for idx,file in enumerate(os.listdir(westmeadsummaries)):
    if idx==0:
        df=pd.read_csv(f'{westmeadsummaries}{file}')
    else:
        x=pd.read_csv(f'{westmeadsummaries}{file}')
        df=pd.concat([df, x], ignore_index=True)
        
        


rtstructs=df.loc[df['SeriesModality']=='RTSTRUCT']

rtstructs['organs'].head()