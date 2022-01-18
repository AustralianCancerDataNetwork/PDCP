# -*- coding: utf-8 -*-
"""
Extracting, transforming and loading one patient data.


"""
import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import patientImagingCRDP
import time
import json

start=time.time()
patients_ids=[]
codesconfig='codesconfig_test.json'
bcd=patientImagingCRDP(codesconfig)
patients_ids=[761856252766]
patients_to_execlude,patients_to_review,patients_passed=bcd.generate_patients_data(patients_ids)
finish=time.time()  

print(f'time taken for one patient: {finish-start}') 


notesdir=bcd.codes['patientnotesdir']
filepath=notesdir+str(patients_ids[0])+'.json'
f = open(filepath,)
file=json.load(f)