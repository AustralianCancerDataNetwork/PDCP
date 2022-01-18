# -*- coding: utf-8 -*-
"""Extracting, transforming and loading a patients cohort.
"""
import sys,os,time,math
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import patientImagingCRD
import pandas as pd

from concurrent.futures import ProcessPoolExecutor


def main():
    try:
        start=time.time()
        patients_ids=[]
        codesconfig='codesconfig_HN.json'
        bcd=patientImagingCRD(codesconfig)
        thedir=bcd.codes['imagesummaries']
        for filename in os.listdir(thedir):
            if "SUCCESS" in filename:
                pid=filename.split("_")[0]
                patients_ids.append(pid)
        
        processedrecords=[]
        for filename in os.listdir('../patientnotes/'):
            pid=filename.split(".json")[0]
            processedrecords.append(pid)
        
        x=[]
        for pid in patients_ids:
            if pid not in processedrecords:
                x.append(pid)
        patients_ids=x
        cpus=2
        n=int(math.ceil(len(patients_ids)/(cpus)))
        pids=[patients_ids[i * n:(i + 1) * n] for i in range((len(patients_ids) + n - 1) // n )] 
        with ProcessPoolExecutor(max_workers = cpus) as executor:
          results = executor.map(bcd.generate_patients_data, pids)   
        patients_to_execlude=[]
        patients_to_review=[]
        patients_passed=[]
        for result in results:
          patients_to_execlude=patients_to_execlude+result[0]
          patients_to_review=patients_to_review+result[1]
          patients_passed=patients_passed+result[2]
        finish=time.time()
        print(f"time taken to get patient imaging data: {finish-start}")
        print(f"patients_to_execlude: {len(patients_to_execlude)}")
        print(f"patients_to_review: {len(patients_to_review)}")
        print(f"patients_passed: {len(patients_passed)}")
        print("patients_to_execlude")
        print(patients_to_execlude)
        print("patients_to_review")
        print(patients_to_review)
        print("patients_passed")
        print(patients_passed)
    except Exception as e:
        print(e)
    input('Press ENTER to exit')
    input('Press ENTER to exit')
    

if __name__ == '__main__':
   main()

    