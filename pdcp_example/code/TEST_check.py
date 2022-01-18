# -*- coding: utf-8 -*-
"""

This script was used to check if each patient will pass the first two steps of verification for the breast cancer patients

If you want to check quickly which of these patients will work, and which will not.

"""
import sys,os
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import patientImagingCRDP
import pandas as pd

codesconfig='codesconfig_test.json'
br=patientImagingCRDP(codesconfig)
link_to_ids=br.codes['link_to_ids']
x=pd.read_csv(link_to_ids)


pids=x['ids'].tolist()
pids=[127077105061]
ex_notes=[]
pa_notes=[]
br=patientImagingCRDP(codesconfig)
imagesummaries=br.codes['imagesummaries']

passed_ids=[]
exec_ids=[]

for PatId in pids:
    try:
        df=pd.read_csv(f'{imagesummaries}/{PatId}_SUCCESS.csv')
        df,notes=br.verify_initial(PatId,[])
        recommendation, codes= br.recommendation(notes)
        if recommendation =='EXECLUDE':#if condition to stop
            print(PatId)
            ex_notes.append(notes)
            exec_ids.append(PatId)
            continue
        list_of_values,notes=br.verify_study(df,notes)
        recommendation,codes=br.recommendation(notes)
        if recommendation=='EXECLUDE':
            print(PatId)
            ex_notes.append(notes)
            exec_ids.append(PatId)
        else:
            pa_notes.append(notes)
            passed_ids.append(PatId)
    except:
        print(f'{PatId} had no image summary')
        ex_notes.append([])
        exec_ids.append(PatId)
        