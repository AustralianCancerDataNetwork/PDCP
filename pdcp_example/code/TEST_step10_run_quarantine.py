# -*- coding: utf-8 -*-
"""
Handling patients with multiple studies that could not be processed.

"""

import time,os,shutil,sys
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import patientImagingCRDP
import pandas as pd


start=time.time()
patients_ids=[]
codesconfig='codesconfig_HN.json'
bcd=patientImagingCRDP()

thequarantine=bcd.codes['thequarantine']
if not os.path.exists(thequarantine):
    os.mkdir(thequarantine)
imagesummaries=bcd.codes['imagesummaries']
datadirectory=bcd.codes['datadirectory']
patientnotesdir=bcd.codes['patientnotesdir']
#set the patients who were initially execluded in here.
patients_ids=[]

for patient in patients_ids:#for each patient who is in quarantine
    images=pd.read_csv(f'{imagesummaries}{str(patient)}_SUCCESS.csv')
    studies=images['StudyInstanceUID'].unique().tolist()
    for idx,astudy in enumerate(studies):
        x=images.loc[images['StudyInstanceUID']==astudy].reset_index(drop=True)
        x.to_csv(f'{imagesummaries}{str(patient)}_SUCCESS.csv',index=False)
        patients_to_execlude,patients_to_review,patients_passed=bcd.generate_patients_data([patient])
        #now copy the patients files to a new location
        destination=f'{thequarantine}{str(patient)}_{str(idx)}/'
        if not os.path.exists(destination):
            os.mkdir(destination)
        source=f'{datadirectory}{str(patient)}'
         #move the generated files
        if os.path.exists(source):
            shutil.move(source, destination)
        #move the notes
        source=f'{patientnotesdir}{str(patient)}.json'
        if os.path.exists(source):
            shutil.move(source, destination)
        
        #move the image summary
        source=f'{imagesummaries}{str(patient)}_SUCCESS.csv'
        if os.path.exists(source):
            shutil.move(source, destination)
        
    #move things back to normal
    images.to_csv(f'{imagesummaries}{str(patient)}_SUCCESS.csv',index=False)

finish=time.time()  

print(f'time taken for one patient: {finish-start}')