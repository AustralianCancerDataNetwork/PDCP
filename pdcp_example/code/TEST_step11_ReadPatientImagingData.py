# -*- coding: utf-8 -*-
"""
Reading patient images into a python dict
"""

import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import ReadPatientImagingData
import json
configfile='codesconfig_test.json'
with open(configfile, "r") as read_file:
    conf = json.load(read_file)

patientnotes=conf['patientnotesdir']

pid=98096239811
jsonfile=f'{patientnotes}{str(pid)}.json'
with open(jsonfile, "r") as read_file:
    file = json.load(read_file)

patientimagingfilesready = file['patientimagingfilesready'] if 'patientimagingfilesready' in file else False
if patientimagingfilesready:
    adict=file['list_of_values']



imagingdata=ReadPatientImagingData.load_patient_images(pid,adict,configfile)