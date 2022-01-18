# -*- coding: utf-8 -*-
"""
Loading a patient set into a python dic
"""

import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import ReadPatientImagingData
import json
configfile='codesconfig_LUNG.json'
with open(configfile, "r") as read_file:
    conf = json.load(read_file)

patientnotes=conf['patientnotesdir']

pid='LUNG1-003'
jsonfile=f'{patientnotes}{str(pid)}.json'
with open(jsonfile, "r") as read_file:
    file = json.load(read_file)

patientimagingfilesready = file['patientimagingfilesready'] if 'patientimagingfilesready' in file else False
if patientimagingfilesready:
    adict=file['list_of_values']



imagingdata=ReadPatientImagingData.load_patient_images(pid,adict,configfile)