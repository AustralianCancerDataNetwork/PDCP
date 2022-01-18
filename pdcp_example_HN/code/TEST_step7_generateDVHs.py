# -*- coding: utf-8 -*-
"""
Generating the DVHs of the successfully converted patients.
"""

import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import DVH
from PDCP import ReadPatientImagingData
import json
configfile='codesconfig_HN.json'
with open(configfile, "r") as read_file:
    conf = json.load(read_file)

patientnotes=conf['patientnotesdir']

for pid in spatients:
    print(pid)
    jsonfile=f'{patientnotes}{str(pid)}.json'
    with open(jsonfile, "r") as read_file:
        file = json.load(read_file)
    
    patientimagingfilesready = file['patientimagingfilesready'] if 'patientimagingfilesready' in file else False
    if patientimagingfilesready:
        adict=file['list_of_values']
    
    
    #load patient imaging data into imagingdata
    imagingdata=ReadPatientImagingData.load_patient_images(pid,adict,configfile)
    
    
    dvh=DVH(pid)
    prescribedDose=None#if we can get the prescribed dose at this stage.
    dvh_df=dvh.compute_dvh_data(imagingdata,prescribedDose)
    
    datadirectory=conf['datadirectory']
    
    dosimetrydir=f'{datadirectory}{str(pid)}/dosimetrydata/'
    if not os.path.exists(dosimetrydir):# a directory that save all the patient's details
        os.mkdir(dosimetrydir)
    dvh_df.to_csv(f'{dosimetrydir}/{str(pid)}_.csv',index=False)


