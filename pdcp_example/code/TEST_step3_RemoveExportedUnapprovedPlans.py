# -*- coding: utf-8 -*-
"""This is an interceptor and it was used to make sure that no rejected, or unapproved dose will be used in the analyses.

The interceptor can be skipped in cases where it is definite that there are no rejected RTDOSES. e.g. with the H&N dataset.

@author: 60183647
"""
import pandas as pd
import os
#example with unapproved plans being exported
rtdoses_file='../approved_rt_doses/patients_hashed_uids.csv'
imagefiles='../imagesummaries_initial/'#rename the file imagesummaries to be imagesummaries_initial
westmeadsummaries='../imagesummaries/'
rtfile=pd.read_csv(rtdoses_file)

pids=[]
exclude_status=['Unapproved','Rejected','Unplanned']
for file in os.listdir(imagefiles):
    if 'SUCCE' in file:
        df=pd.read_csv(f'{imagefiles}{file}')
        #get the series instances of the RTDOSES.
        qq=df.loc[(df['Modality']=='RTDOSE')&(df['DoseSummationType']=='PLAN')]['SeriesInstanceUID'].tolist()
        #status of each plan
        n=rtfile.loc[rtfile['hashed_SeriesUID'].isin(qq)]
        list_series=n['hashed_SeriesUID'].tolist()#get the list
        list_series_status=n['Status'].tolist()#get the status of each series in the list
        
        for series,status in zip(list_series,list_series_status):#remove any series UID with any of the cases above
            if status in exclude_status:
                #remove any series that matches an exclusion status
                df=df.loc[df['SeriesInstanceUID']!=series].reset_index(drop=True)
        df.to_csv(f'{westmeadsummaries}{file}',index=False)
                
                