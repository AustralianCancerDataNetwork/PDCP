# -*- coding: utf-8 -*-
"""INTERCEPTOR

for this particular dataset, we know that we want the study that contains the PT scan.
Hence, remove all the studies with no PT

Change the imagesummaries folder to be imagesummaries_initial
"""

import pandas as pd
import os
#from PatientOrthanc import patientImaging

newdir='../imagesummaries/'
olddir='../imagesummaries_initial/'
for filename in os.listdir(olddir):
    df=pd.read_csv(f'{olddir}{filename}')
    study_ids=df.loc[df['Modality']=='PT']['StudyIdentifier'].unique().tolist()
    df=df.loc[df['StudyIdentifier'].isin(study_ids)]
    if df.shape[0]==0:
        print(f"no data for {filename}")
    df=df.reset_index(drop=True)
    df.to_csv(newdir+filename)
                