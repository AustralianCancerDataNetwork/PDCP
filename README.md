Welcome to PDCP\'s documentation!
=================================



Overview (version 0.0.1)
========================

Patient Data Collection and Processing (PDCP) is a tool used to collect and process patients radiotherapy imaging data from
the Orthanc research PACs via its REST API.

Orthanc provides a simple and standalone DICOM server (PACS). It
supports the DICOM and DICOMweb protocols. It was used in the
AusCAT network to save patients anonymized radiotherapy data
exported from the Hospital PACS.

PDCP is a python module that consists of multiple classes used to
prepare patients records. Object oriented programming and inheritance
were followed to make the code reusable and to extend certain functions.
The **patientImaging** class is the main module and it contains a set of
functions used to collect, validate, and track the data preparation
process.

Other classes that inherit from **patientImaging** were created to
handle different cancer sites and projects:

-   **patientImagingCRDP**: a class that inherits the patientImaging
    class, used to collect and process cancer patients data from the
    AUScat data centers, where there is a need to link 4 patient
    modalities. (C: stands for CT, R: stands for RTSTRUCTS, D: stands
    for RTDOSE, P: stands for the RTPLAN)
-   **patientImagingCRD**: a class that inherits the patientImaging
    class, used to collect and process cancer patients radiotherapy data
    where the RTPLAN cannot be obtained
-   **patientImagingCR**: a class that inherits the patientImaging
    class, used to collect and process a patients data where there is a
    need to link the CT with the RTSTRUCT only (segmentation task).

Other classes/functions were implemented to facilitate the data
preparation task:

-   **ReadPatientImagingData**: used to load the patient\'s processed
    data into a python dictionary {\'CT\':,\'masks\':,etc}.
-   **ROIP** : a class used to generate the central slices patient\'s
    organs at risk (OARs) and target volumes (TV)
-   **DVH** : a class used to generate the dosimetry features for the
    patients.

Several python packages were utilized to collect the data and to process
the images:

-   **requests**: a python built-in module used to retrieve required
    files from an orthanc server (targets the orthanc server rest API)
-   **pyorthanc**: a python library that wraps the Orthanc REST API and
    facilitates the manipulation of data with several utilities. It was
    used in this script to identify patient related files. It was
    initially used to retrieve data through some fuctions
    (get\_instance\_file(), get\_instance\_simplified\_tags()), however
    it was noticed that it was slow compared to python built-in modules.
-   **concurrent.futures** : a python built-in module used to apply
    threading and multiprocessing.
-   **pydicom**: a python library used to handle dicom imaging tasks.
    i.e the orthanc server returns the files as a bytes array. pydicom
    functions were used to convert such arrays to pydicom FileDatasets
    before saving into the patient\'s directory.
-   **simpleITK**: is a simplified, open-source interface to the Insight
    Segmentation and Registration Toolkit. It was used to handle
    resampling tasks for the dose grid.
-   **numpy**: used to save radiotherapy data into 3d arrays.
-   **pandas**: a python library used with tabular data, dataframes were
    used to save the images summaries in this script
-   **json**: used to save patient notes while collecting and processing
    the records
-   **hdf5stogare**: used to save and load matlab files that contains
    the patient\'s related data (not used).

What can PDCP do?
=================

PDCP facilitates the data collection and preparation for using imaging
radiotherapy data. PDCP can:

-   Query, retrieve, and validate patient imaging summaries from an
    Orthanc PACS.
-   Analyse associations in patient studies (linking required
    modalities)
-   Retrieve patient imaging data into a local directory.
-   Prepare the records for use in various research questions (dosimetry
    analyses, contouring, image standardization)
-   Track the patients data collection process and idenfity reasons
    behind excluding patients data.
	
Data Collection Example (Public Data)
=======================================

https://zenodo.org/record/5847536

Documentation
================

Linked Software Paper:

Haidar, A.; Aly, F.; Holloway, L. PDCP: A Set of Tools for Extracting, Transforming, and Loading Radiotherapy Data from the Orthanc Research PACS. Software 2022, 1, 215-222. https://doi.org/10.3390/software1020009

Code Documentation:

https://australiancancerdatanetwork.github.io/PDCP/html/index.html


Next Steps
==========

-   Patients data are currently retrieved via the http protocol. We aim
    to utilize the WebDav, which is an extended protocol that allows
    remote web content authoring operations, in future versions to be
    able to use dicom tags and indexed images from Orthanc directly.
    Within WebDav, data can be viewed by patients, studies, or uids,
    which will help in managing DICOM data at the centres.
-   We aim to utilize the Orthanc plugins such as **serve-folders** to
    be able to track patient notes from webpages.
-   At this stage, patients with multiple studies will require manual
    review for selecting the right study. We aim to automate this
    process.

Selecting Modalities in a Patient Study
=======================================

The current linkage is conducted without retrieving patients data from
the Orthanc server. Before retrieving data, the patients will be
verified. Further details about verification can be found in documentation associated with the repo.

Selecting a Patient Study
=========================

-   A study is selected if it contains the required modalities added by
    the user.
-   A study will be discarded if the selected CT series contains a large
    number of instances
-   A study will be discarded if the study has the required RTSTRUCT,
    with the RTSTRUCT not containing any of the required keywords (i.e.
    study with RTSTRUCT with contour names PATIENT, ISO) will not be
    used.
-   A study will be discarded if it contains multiple CTs with multiple
    associations, will be discarded and will require review.
-   A study will be discarded if it contains a keyword that should not
    be found in its study name (e.g. a breast cohort is being collected
    while the study name shows \'head and neck\').

Example Data Collection
=======================

The example below shows the steps followed to prepare a cohort of 10
patients.

This example has been conducted with **patientImagingCRDP** for a breast
cohort, where a linkage between CT\--\> RTSTRUCT \--\> RTPLAN \--\>
RTDOSE is targeted.

Step 1: Setup Configuration File
--------------------------------

For each data collection and preparation task, a configuration file is
required. The first step is to create the configuration in a json file:

Here is a brief overview of the required keys:

-   **required\_modalities\_for\_patient**: a list of the required
    modalities \[\'CT\',\'RTSTRUCT\',\'RTPLAN\',\'RTDOSE\'\]
-   **study\_desc\_should\_not\_contain**: a list of keywords the
    patient study should not contain.
-   **study\_desc\_may\_contain**: a list of keywords a patient study
    might contain
-   **possibilities**: a list of keywords, where one of them at least
    should be found in the RTSTRUCT contours
-   **imagesummaries**: a directory to host the patient instances dicom
    summaries tags found in the targeted Orthanc server.
-   **patientnotesdir**: a directory to host the patient notes
-   **datadictionary**: a directory to host the patients records.
-   **quarantine**: Patients might have a rescan through the course of
    treatment. Other patients might have multiple courses of treatment.
    Quarantine is used to host patients with multiple studies.
-   **link\_to\_ids**: a csv file that contains the patient ids and its
    corresponding indexed orthanc ids.
-   **ipport**: ip and port of the Orthanc server.
-   **username**: username of an account in the Orthanc server
-   **password**: password of an account in the Orthanc server. Leave
    empty if not needed.
-   **CONNECTIONS**: the number of connections to be used when targeting
    the server.
-   **TIMEOUT**: total number of seconds to wait when sending the
    request to the server.

Step 2: Prepare directories
---------------------------

Create a directory to host the patients data and notes. This directory
should include:

-   **ids** : a directory used to save a .csv file that will contain the
    patient ids and its corresponding Orthanc ids (*links\_to\_ids* in
    the config file).
-   **imagesummaries**: a directory used to save csv files that contain
    summaries of patient\'s imaging data in the targeted orthanc server
-   **patientnotes**: a directory that will be used to save json objects
    that contain each patient data collection and preparation notes
-   **data**: will be used to save patient data. For each patient, a new
    directory will be created.
-   **quarantine**: will be used to save patient quarantine data. Each
    study will be treated as the only study associated with the patient.
    Hence, once a study is selected it will be manually moved into the
    data directory.

Step 3: Retrieve Orthanc Ids
----------------------------

The third step is to retrieve patients assoicated ids from the Orthanc
server. The Orthanc server will create a specific id for each patient.
These values are currently saved in an SQLite database (by default) with
options to utilize other servers as plugins (Postgress).

After running this script, each row in the generated .csv file will
represent the patient identifier and its corresponding Orthanc
identifier, which is used by the Orthanc server to index patient\'s
studies.

The script is currently used to get all the patients ids from the remote
server.

```
from PDCP import patientImaging
codesconfig='codesconfig_test.json'
patientImaging.collect_pids_orthanc(codesconfig)
```
The csv file will be similar to :


```
ids,orthanc_ids
1,b589720b-b3e2d6bb-e8ad034c-f3443ebd-5d155c67
2,236b7e77-7dd097d0-8e78dcac-98aca88b-1d214fd1
3,8ab22a5c-1c79ed07-229b7721-3d92e770-c7fcdf0e
4,74686685-bb06152e-9525ef4c-f5f53674-fc880224
5,c8e45dnf-bf3b1367-85aa9baa-1017d2a0-1789c6d4
```

with ids representing the patient ids and orthac\_ids representing the
patient orthanc id.

Step 4: Prepare Patients Images Summaries
-----------------------------------------

The fourth step is to collect a summary of the available data for each
patient in the Orthanc server. Various dicom tags are required to handle
the linkage between modalities and to prepare the patient sudy. These
tags are retrieved for each patient instance and added as a row to the
associated csv file. For each patient, a dataframe is expected to be
generated. Three possible cases are axpected when collecting patients
images summaries:

1.  **pid\_SUCCESS.csv** : This indicates that the patient images
    summary (dataframe) was successfully prepared .
2.  **pid\_IMAGINGDATANOTFOUND.csv** : This indicates that the patient
    images summary (dataframe) cannot be generated because patients data
    related to data collection task were not found.
3.  **pid\_ERROR.csv** : This indicates that the patient images summary
    was collected with errors. In most cases, this error occurs because
    the server failed to handle a high number of requests at the same
    time. This can be fixed by repeating the execution or by lowering
    the number of threads to target the server.


When running this script, the image summaries will be added to
**imagesummaries**. Here is a result of running a cohort of 10 patients
with patientImagingCRDP
```
import os,math,time,sys
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))

from PDCP import patientImagingCRDP
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

if __name__ == '__main__':
    try:
        print('Collecting patient summaries from the orthanc server.')
        start=time.time()
        codesconfig="codesconfig_test.json"
        if not os.path.exists(codesconfig):
            print('Congfig file does not exist.')
            input('Press ENTER to exit')
        br=patientImagingCRDP(codesconfig)
        link_to_ids=br.codes['link_to_ids']
        x=pd.read_csv(link_to_ids)
        orthanc_ids=x['orthanc_ids'].tolist()
        patients_ids=x['ids'].tolist()

        #cpus=multiprocessing.cpu_count()
        cpus=2
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
        input('Press ENTER to exit')
        input('Press ENTER to exit')
    except Exception as e:
        print(e)
        print(f"An error occured.")
        input('Press ENTER to exit')
```

Step 5: Generate Patient Data
-----------------------------

The images summary for each patient has been collected. The next step is
to verify linkage and retrieve patients data.

The fifth step includes retrieving data from the orthanc server into a
local directory that consists of:

-   **CT:** a directory that contains the patient\'s CT DICOM slices
-   **RTDOSE:** a direcotry that contains the patient\'s RTDOSES
-   **RTSTRUCT:** a direcotry of directories that contains the
    patient\'s RTSTRUCT. (each RTSTRUCT will be saved in a sub
    directory)
-   **CTnifti:** a directory that contains the patient\'s CT nifti file
-   **masks:** a directory of directories that contains the patient\'s
    structures masks. To generate the masks, a script was taken from
    platipy (Thanks Platipy !).
-   **rtdosenifti:** a directory that contains the patient\'s converted
    RTDOSES

**Part A: Example with one patient**

The previous script shows the data collection process for one patient
with an id *123456789*. Running this script, a directory with the
patient records is expected.

**Part B: Example with multiple patients using multiple CPUs**

``` {.python}
import sys,os,time,math
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import patientImagingCRDP
import pandas as pd

from concurrent.futures import ProcessPoolExecutor

def main():
    start=time.time()
    patients_ids=[]
    codesconfig='codesconfig_test.json'
    bcd=patientImagingCRDP(codesconfig)
    thedir=bcd.codes['imagesummaries']
    for filename in os.listdir(thedir):
        if "SUCCESS" in filename:
            pid=filename.split("_")[0]
            patients_ids.append(int(pid))

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
    input('Press ENTER to exit')
    input('Press ENTER to exit')


if __name__ == '__main__':
   main()
```

For each patient, a .json file will be generated to report the data
collection process. An example below shows the notes that will be added
to the **patientnotes** directory.

``` {.python}
{"raw_images_summary":{"PatId": 123456789, 
    "number_of_patient_studies": 1, 
    "number_of_CT_series": 1,
    "number_of_CT_instances": 131,
    "number_of_RTSTRUCT_series": 1,
    "number_of_RTSTRUCT_instances": 1,
    "number_of_RTDOSE_series": 1,
    "number_of_RTDOSE_instances": 1,
    "number_of_RTPLAN_series": 1,
    "number_of_RTPLAN_instances": 1, "number_of_PT_series": 0, "number_of_PT_instances": 0},
    "list_of_values": {"PatId": 123456789, 
        "CT_SeriesIdentifier": "1.3.6.1.4.1.32722.1111111111",
        "RTSTRUCT_SOPInstanceUID": ["1.3.6.1.4.1.32722.22222222"],
        "StructureSetDate": "missing",
        "StudyDate": 20141222,
        "RTDOSE_SOPInstanceUID": ["1.3.6.1.4.1.32722.3333333"],
        "RTPLAN_SOPInstanceUID": ["1.3.6.1.4.1.32722.44444444444444"],
        "CT_orthanc_identifier": "97953882-c2ac9041-5c6a81b3-asdas21-12567e46",
        "RTSTRUCT_orthanc_identifiers": ["567b1457-9971653c-333222-0bbee186-a36cff64"],
        "RTDOSE_orthanc_identifiers": ["7005f8e5-e75dfd2b-111-44-306b4626"],
        "RTPLAN_orthanc_identifiers": ["e12583b3-555422-99ad91d5-31af02e4-fc62a157"],
        "thedir": "../../pdcptest/data/123456789/", 
        "ct_directory": "../../pdcptest/data/123456789/CT/", 
        "rtdoses_directory": "../../pdcptest/data/123456789/RTDOSE/",
        "rtstruct_directory": "../../pdcptest/data/123456789/RTSTRUCT/", 
        "masks_directory": "../../pdcptest/data/123456789/masks/",
        "nifti_directory": "../../pdcptest/data/123456789/CTnifti/"},
 "verification_notes": 
     ["I: Initial Verification: no phantom was found for the patient.", 
     "I: Initial Verification: Patient has one associated study", 
     "I: I_SUCC_001:PROCEED:123456789", "II: Study verification", 
     "II: Study verification: Checking CT series: 1.3.6.1.4.1.32722.1111111111", 
     "II: Study verification: Patient has one CT associated with RTSTRUCTS and RTDOSES", 
     "II: II_SUCC_001:PROCEED:123456789"],
 "verified_images_summary": {"PatId": 123456789, 
     "number_of_patient_studies": 1, "number_of_CT_series": 1, 
     "number_of_CT_instances": 131, "number_of_RTSTRUCT_series": 1, 
     "number_of_RTSTRUCT_instances": 1, "number_of_RTDOSE_series": 1, 
     "number_of_RTDOSE_instances": 1, "number_of_RTPLAN_series": 1, 
     "number_of_RTPLAN_instances": 1, "number_of_PT_series": 0, "number_of_PT_instances": 0},
  "version": "liverpool python v1.0.", 
  "retrieval_notes": ["XI: CT retrieval:Took 5.89 s", 
      "XI: CT retrieval: skipped, no SliceLocation: 0", 
      "XI: CT retrieval: skipped, no ImagePositionPatient: 0",
       "XI: CT retrieval: retrieved the CT series instances to the local directory.",
        "XI: XI_SUCC_001:PROCEED",
         "XII: CTnifti generation",
          "XII: CTnifti generation: Successfully added the CT nifti file to its directory", 
      "XII: XII_SUCC_001:PROCEED", "XIII: RTSTRUCTS retrieval", 
      "XIII: RTSTRUCTS retrieval: added an RTSTRUCT instance to the RTSTRUCT directory.", 
      "XIII: XIII_SUCC_001: PROCEED", 
      "XIV: RTSTRUCTS nifti masks generation.", 
      "XIV: XIV_SUCC_001:PROCEED ", "XV: RTDOSE retrieval.",
       "XV: RTDOSE retrieval: added 1 rtdose PLAN instances to the RTDOSE directory. ",
        "XV: XV_SUCC_001: PROCEED"], 
    "loading_notes": ["XXI: load CT", "XXI: XXI_SUCC_001: PROCEED", "XXII: XXII loading masks", 
    "XXII: XXII loading masks: loaded the mask to numpy array:COMBLUNG", 
    "XXII: XXII loading masks: loaded the mask to numpy array:CTV", 
    "XXII: XXII loading masks: loaded the mask to numpy array:CTV_TUMOURBED", 
    "XXII: XXII loading masks: loaded the mask to numpy array:CTWIRE", 
    "XXII: XXII loading masks: loaded the mask to numpy array:External_ROI", 
    "XXII: XXII loading masks: loaded the mask to numpy array:Lung_L", 
    "XXII: XXII loading masks: loaded the mask to numpy array:Lung_R", 
    "XXII: XXII loading masks: loaded the mask to numpy array:PTV",
     "XXII: XXII loading masks: loaded all the patient's masks.", 
     "XXII: XXII_SUCC_001:PROCEED", 
     "XXIII: XXIII loading RTDOSES", 
     "XXIII: XXIII loading RTDOSES: added an rt dose: 1.3.6.1.4.1.32722.3333333", 
     "XXIII: XXIII_SUCC_001: PROCEED", "XXIV: XXIV select RTDOSES", 
     "XXIV: XXIV select RTDOSES: Maximum of rt doses: [46.318787]", 
     "XXIV: XXIV_SUCC_001:PROCEED"],
     "status": "SUCCESS", "patientimagingfilesready": true}
```

Step 6: Check Patients
----------------------

The successfully collected patients are patients who has the key
patientimagingfilesready equal to true in the patient notes.

```
import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import ReadPatientImagingData
import json
configfile='codesconfig_test.json'
with open(configfile, "r") as read_file:
    conf = json.load(read_file)

patientnotes=conf['patientnotesdir']
spatients=[]
epatients=[]
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

```

Step 7: Generate Dosimetry Features
-----------------------------------

Some dosimetry features can be generated for each generated mask at this
stage and added to the patients directory.

```

import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import DVH
import sys,os
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import ReadPatientImagingData
import json
configfile='codesconfig_test.json'
with open(configfile, "r") as read_file:
    conf = json.load(read_file)

patientnotes=conf['patientnotesdir']

for pid in spatients:
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

```

For each patient,a directory will be obtained with all the required data.



Step 8: Patients in Quarantine
------------------------------

In most cases, patients will be in quarantine if they have mutliple
studies with successful associations. In other words, patients with two
studies ready to use. This can occure because:

-   a patient might have two studies, where one of them is a rescan
-   a patient might have multiple studies, representing multiple cancer
    treatments

Those patients will need manual review to select the correct study that
matches the project research question.

The studies will be created and mapped to the quarantine directory. Once
the correct study is selected, it can be mapped into the **data**
directory to be included in any further analyses.

```
import time,os,shutil,sys
sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import patientImagingCRDP
import pandas as pd
import json

start=time.time()
patients_ids=[]

configfile='codesconfig_test.json'
with open(configfile, "r") as read_file:
        conf = json.load(read_file)

bcd=patientImagingCRDP(configfile)

thequarantine=conf['thequarantine']
if not os.path.exists(thequarantine):
        os.mkdir(thequarantine)
imagesummaries=conf['imagesummaries']
datadirectory=conf['datadirectory']
patientnotesdir=conf['patientnotesdir']
#set the patients who were initially execluded in here.
patients_ids=[]

for patient in patients_ids:#for each patient who is in quarantine
        images=pd.read_csv(f'{imagesummaries}{str(patient)}_SUCCESS.csv')
        studies=images['StudyInstanceUID'].unique().tolist()
        for idx,astudy in enumerate(studies):
                x=images.loc[images['StudyInstanceUID']==astudy].reset_index(drop=True)
                x.to_csv(f'{imagesummaries}{str(patient)}_SUCCESS.csv',index=False)
                patients_to_execlude,patients_to_review,patients_passed=bcd.generate_patients_data([patient])
                #now copy the patients files to a new location
                destination=f'{thequarantine}{str(patient)}_{str(idx)}/'
                if not os.path.exists(destination):
                        os.mkdir(destination)
                source=f'{datadirectory}{str(patient)}'
                 #move the generated files
                if os.path.exists(source):
                        shutil.move(source, destination)
                #move the notes
                source=f'{patientnotesdir}{str(patient)}.json'
                if os.path.exists(source):
                        shutil.move(source, destination)

                #move the image summary
                source=f'{imagesummaries}{str(patient)}_SUCCESS.csv'
                if os.path.exists(source):
                        shutil.move(source, destination)

        #move things back to normal
        images.to_csv(f'{imagesummaries}{str(patient)}_SUCCESS.csv',index=False)

finish=time.time()

print(f'time taken for one patient: {finish-start}')
```

The studies will be created and mapped to the quarantine directory. Once the correct study is selected, it can be mapped into the **data** directory to be included in any further analyses.


Step 9: Generate Central Slices
--------------------------------

To generate central slices of the masks

```
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
    roip.generate_slices_patient_rois(0)#0 is depth 
    
```

Codes Associated with Errors
===============================

The following codes will be associated with the patient data retrieval and processing.

Initial Verification Codes
-----------------------------

_Table 1 Initial Verification (the patient imaging data summary)._

| **Code** | **Description** |
| --- | --- |
| I\_EXEC\_001:EXECLUDE | I: Initial Verification: Patient details not found in the directory. |
| I\_EXEC\_002:EXECLUDE | I: Initial Verification: ERROR in collected the dataset. |
| I\_EXEC\_003:EXECLUDE | I: Initial Verification: IMAGING DATA NOT FOUND. |
| I\_EXEC\_004:EXECLUDE | I: Initial Verification: contained phantom study only (Patient cannot be included in the study). |
| I\_EXEC\_005:EXECLUDE | I: Initial Verification: modality missing (Patient cannot be included in the study):modality |
| I\_EXEC\_006:EXECLUDE | I: Initial Verification: The patient had no more available studies after removing studies with ineligible keywords in each study description. |
| I\_SUCC\_001:PROCEED | I: Initial Verification: Patient has one associated study |
| I\_REV\_001:LOW | I: Initial Verification: Patient has x multiple associated studies |
| I\_SUCC\_002:PROCEED | I: Initial Verification: Conflict removed. only one study remains |
| I\_EXEC\_007:EXECLUDE | I: Initial Verification: The patient have multiple studies associated, discard. Patient data can be later exported to quarantine for review. |

_Table 2 Study Verification codes._

| **Code** | **Description** |
| --- | --- |
| II\_EXEC\_001:EXECLUDE | II: Study verification: Patient has no associated CT modality. |
| II\_EXEC\_002:EXECLUDE | II: Study verification: Patient has no associations between modalities |
| II\_SUCC\_001:PROCEED | II: Study verification: Patient has one CT associated with RTSTRUCTS and RTDOSES. |
| II\_EXEC\_003:EXECLUDE | II: Study verification: Patient has multiple associations between modalities, must be reviewed. Discard for now. |

Retrieval Notes
----------------

_Table 3 CT retrieval codes._

| **Code** | **Description** |
| --- | --- |
| XI\_EXEC\_001: EXECLUDE | XI: CT retrieval: cannot sort retrieved instances. |
| XI\_EXEC\_02: EXECLUDE | XI: CT retrieval: Failed to retrieve the patient&#39;s CT. |
| XI\_SUCC\_001:PROCEED | CT retrieved successfully. |

_Table 4 CT NIFTI generation codes._

| **Code** | **Description** |
| --- | --- |
| XII\_SUCC\_001:PROCEED | XII: CTnifti generation: Successfully added the CT nifti file to its directory |
| XII\_EXEC\_001: EXECLUDE | XII: CTnifti generation: Failed to generate the patient&#39;s CTnifti. |

_Table 5 RTSTRUCTs retrieval codes._

| **Code** | **Description** |
| --- | --- |
| XIII: XIII\_EXEC\_001: EXECLUDE | XIII: RTSTRUCTS retrieval: failed to retrieve an RTSTRUCT |
| XIII: XIII\_SUCC\_001: PROCEED | Retrieved the rtstructs successfully|
| XIII: XIII\_EXEC\_001: EXECLUDE | XIII: RTSTRUCTS retrieval: failed to retrieve the RTSTRUCTs |

_Table 6 RTSTRUCTs NIFTI masks generation._

| **Code** | **Description** |
| --- | --- |
| XIV\_SUCC\_001:PROCEED | RTSTRUCT masks generated  |
| XIV\_EXEC\_001:EXECLUDE | XIV: RTSTRUCTS nifti masks generation: failed to generate the nifti masks for the patients. |

_Table 7 RTPLAN retrieval codes._

| **Code** | **Description** |
| --- | --- |
| XV\_EXEC\_001: EXECLUDE | XV: RTPLAN retrieval: failed to retrieve an RTPLAN |
| XV\_SUCC\_001: PROCEED | RTPLAN retrieved successfully |
| XV\_EXEC\_002: EXECLUDE | Exception |

_Table 8 RTDOSE retrieval codes._

| **Code** | **Description** |
| --- | --- |
| XVI\_EXEC\_001: EXECLUDE | XVI: RTDOSE Retrieval: failed to retrieve an RTDOSE |
| XV\_SUCC\_001: PROCEED | XVI: RTDOSE Retrieval: added {x} rtdose instances with dosesummationtype as PLAN to the RTDOSE directory. |
| XVI\_EXEC\_002: EXECLUDE | XVI: RTDOSE Retrieval: Exception |

Loading notes
----------------

_Table 9 Loading the CT NIFTI file to a numpy array._

| **Code** | **Description** |
| --- | --- |
| XXI\_SUCC\_001: PROCEED | Load was successful |
| XXI\_EXEC\_001:EXECLUDE | XXI: loading CT: EXCEPTION |

_Table 10 loading the masks to numpy arrays._

| **Code** | **Description** |
| --- | --- |
| XXII\_EXEC\_001:EXECLUDE | XXII: XXII loading masks: No mask folders found in the directory |
| XXII\_REV\_001: NORMAL | XXII: XXII loading masks: no masks were found for the RTSTRUCT. |
| XXII\_REV\_002: NORMAL | XXII: XXII loading masks: failed to load the mask |
| XXII\_REV\_003: NORMAL | XXII: XXII loading masks: multiple masks referring to the same roi names, possibly a duplicate. |

_Table 11 Loading the RTDOSES to numpy arrays._

| **Code** | **Description** |
| --- | --- |
| XXIV\_EXEC\_001:EXECLUDE | XXIV select RTDOSES: No dosegrids associated with the list |
| XXIV\_EXEC\_002:EXECLUDE | XXIV select RTDOSES: No dosegrids associated with the study. |
| XXIV\_EXEC\_003:EXECLUDE | Maximum dose received by a voxel is not acceptable. |
| XXIV\_SUCC\_001:PROCEED | RTDOSES successfully loaded |
    


Contact
============================

email: ali.hdrv@outlook.com . Latest review 11/01/2022.

License
==========
MIT


Copyright 2022, Ali Haidar

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.