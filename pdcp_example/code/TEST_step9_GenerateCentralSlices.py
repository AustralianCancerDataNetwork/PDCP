# -*- coding: utf-8 -*-
"""
Generating central slices for patients.

"""
import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import ROIP


patientsnotesdirectory='../patientnotes/'
patientdirectory='../data/'

pids=os.listdir(patientsnotesdirectory)
pids=[p.split('.json')[0] for p in pids]


for pid in pids:
    roip=ROIP()
    roip.load_data_from_file(patientsnotesdirectory,patientdirectory,pid)
    roip.generate_slices_patient_rois(0)