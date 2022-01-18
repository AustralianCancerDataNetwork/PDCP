# -*- coding: utf-8 -*-
"""
Checking successfully converted patients

@author: a.haidar
"""

import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import ReadPatientImagingData
import json
configfile='codesconfig_HN.json'
with open(configfile, "r") as read_file:
    conf = json.load(read_file)

patientnotes=conf['patientnotesdir']
spatients=[]
epatients=[]
exc_notes=[]
for filename in os.listdir(patientnotes):
    jsonfile=f'{patientnotes}{filename}'
    pid=filename.split(".json")[0]
    with open(jsonfile, "r") as read_file:
        file = json.load(read_file)
    patientimagingfilesready = file['patientimagingfilesready'] if 'patientimagingfilesready' in file else False
    if patientimagingfilesready:
        spatients.append(pid)
    else:
        epatients.append(pid)
        exc_notes.append(file)
