# -*- coding: utf-8 -*-
"""
Getting the patients imaging summaries based on the logic added in the configuration document.
Getting multiple patients images summaries
"""
import os,math,time,sys
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))

from PDCP import patientImagingCRD
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

if __name__ == '__main__':
    try:
        print('Collecting patient summaries from the orthanc server.')
        start=time.time()
        codesconfig="codesconfig_HN.json"
        if not os.path.exists(codesconfig):
            print('Congfig file does not exist.')
            input('Press ENTER to exit')
        br=patientImagingCRD(codesconfig)
        link_to_ids=br.codes['link_to_ids']
        x=pd.read_csv(link_to_ids)
        
        orthanc_ids=x['orthanc_ids'].tolist()
        patients_ids=x['ids'].tolist()
    
        #cpus=multiprocessing.cpu_count()
        cpus=5
        n=int(math.ceil(len(orthanc_ids)/(cpus)))#leave one CPU for other things :p
        #n=2 #I assume we have 2 processes available in the server. 
        oids = [orthanc_ids[i * n:(i + 1) * n] for i in range((len(orthanc_ids) + n - 1) // n )]  
        pids=[patients_ids[i * n:(i + 1) * n] for i in range((len(patients_ids) + n - 1) // n )] 
        processes=[]
        with ProcessPoolExecutor(max_workers = cpus) as executor:
          results = executor.map(br.generate_orthanc_files_summaries, oids,pids)   
        wpids=[]
        wpatient_comments=[]
        for result in results:#results is an iterable of tuples
            wpids=wpids+result[0]
            wpatient_comments=wpatient_comments+result[1]
        print(wpatient_comments)
        finish=time.time()
        print(f"time taken to get patient imaging data: {finish-start}")
    except Exception as e:
        print("This error occurred while collecting the patient image summaries.")
        print(e)
        
        input('Press ENTER to exit')
