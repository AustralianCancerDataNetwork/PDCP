# -*- coding: utf-8 -*-
"""
This is a script used to collect all the patients ids with their orthanc ids from the server. 
"""
import os,math,time,sys
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import patientImaging
codesconfig='codesconfig_HN.json'       
patientImaging.collect_pids_orthanc(codesconfig)