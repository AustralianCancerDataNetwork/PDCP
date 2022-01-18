# -*- coding: utf-8 -*-
"""
Extracting, transforming and loading 1 patient data.

"""
import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import patientImagingCRD
import time
import json

start=time.time()
patients_ids=[]
codesconfig='codesconfig_HN.json'
bcd=patientImagingCRD(codesconfig)
patients_ids=['HN-CHUM-001']
patients_to_execlude,patients_to_review,patients_passed=bcd.generate_patients_data(patients_ids)
finish=time.time()  

print(f'time taken for one patient: {finish-start}') 


notesdir=bcd.codes['patientnotesdir']
filepath=notesdir+str(patients_ids[0])+'.json'
f = open(filepath,)
file=json.load(f)

input('Enter to exit')