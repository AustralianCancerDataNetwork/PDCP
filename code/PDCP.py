import concurrent.futures
import requests
import SimpleITK as sitk
import os,time
from convert import convert_rtstruct
import pandas as pd
import numpy as np
import pickle
import shutil
import pydicom
from io import BytesIO
from pyorthanc import Orthanc
import os.path
import sys
from pyorthanc import Patient#, Study, Series, Instance
import json
import re
import math
from scipy import ndimage



#10/01/2022

class patientImaging:
    """A class that contains all the required functions to prepare and process patient records from an Orthanc server.
    
    """
    
    @staticmethod
    def get_pid(orthanc,orthanc_identifier):
        """Get the patient id from the orthanc server.

        Parameters
        ----------
        orthanc : pyorthanc instance 
            a pyorthanc instance with connections to the orthanc server.
            
        orthanc_identifier: str
            Orthanc identifier
            
        Returns
        -------
        patient_id: str/int
            the patient id
            
        orthanc_identifier: str
            Orthanc identifier
        
        """
        p=Patient(orthanc_identifier,orthanc)
        patient_id = p.get_id()
        print(patient_id)
        return patient_id,orthanc_identifier
    
    @staticmethod
    def collect_pids_orthanc(codesconfig=None,outputcsv='../ids/final_ids_remoteorthanc.csv',saveids_asstr=True):
        """Send requests to the orthanc server to collect patient ids, and save outputs to a csv file.
        
        Parameters
        ----------
        codesconfig : dict
            configuration file with details about the targeted cohort.
            
        outputcsv: str
            path to the location of the output file.
            
        saveids_asstr: bool
            a boolean to save the retrived ids as strings. 
           

        """
        start=time.time()
        if codesconfig is not None:
            with open(codesconfig) as json_file:
                codes = json.load(json_file) 
        ipport=codes['ipport']
        orthanc = Orthanc(f"{ipport}")
        #add the pw if needed
        if len(codes['username'])>0:
            orthanc.setup_credentials(codes['username'], codes['password'])
        print('Getting the orthanc indexed ids.')
        patients_identifiers=orthanc.get_patients()
        pat_ids=[]
        orthanc_ids=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=codes['CONNECTIONS']) as executor:
            future_to_url = (executor.submit(patientImaging.get_pid, orthanc, orthanc_id) for orthanc_id in patients_identifiers)
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    patient_id,orthanc_identifier = future.result()#get the result of each request
                except Exception as exc:
                    print(exc)
                    exit()
                finally:
                    pat_ids.append(patient_id)
                    orthanc_ids.append(orthanc_identifier)
    
        di={'ids':pat_ids,'orthanc_ids':orthanc_ids}
        df=pd.DataFrame(di)
        if saveids_asstr:
            df['ids']= df['ids'].astype(str)
        df.to_csv(outputcsv,index=False)
        finish=time.time()
        dur=round(finish-start,2)
        print(f"The time taken to get patients ids from the orthanc server was: {dur} seconds.")
        input('Press ENTER to exit')
        
    
    def __init__(self,codesconfig=None):
        """Class initializer that loads a json file, which contains the experiment directories.
        
        Parameters
        ----------
        
        codesconfig : dict
            configuration file with details about the targeted cohort.
        """
        if codesconfig is not None:
            with open(codesconfig) as json_file:
                codes = json.load(json_file)
            #reload the json object and add new keys
            s=",".join(codes['study_desc_may_contain'])
            e=",".join(codes['study_desc_should_not_contain'])
            codes['message']=f'This process collects data related to {s} patients. It deletes studies with descriptions that contain: {e}. If this is not the cohort required, please revisit the codes function in PatientOrthanc and update the lists to include the required patients with the right cancer site.'
            #list of DICOM tags that will be collected for any instance of a the patient modality.
            #removed 'ROIContourSequence',RTROIObservationsSequence,StructureSetROISequence
            # 'StructureSetLabel','StructureSetName',  'ReferencedFrameOfReferenceSequence',BeamSequence
            instance_keys=['AccessionNumber', 'AcquisitionNumber', 'ApprovalStatus', 'BitsAllocated', 'BitsStored', 'BurnedInAnnotation',
                       'Columns', 'DoseGridScaling', 'DoseSummationType', 'DoseType', 'DoseUnits', 'FractionGroupSequence', 
                       'FrameIncrementPointer', 'FrameOfReferenceUID', 'GridFrameOffsetVector', 'HighBit', 'ImageOrientationPatient',
                       'ImagePositionPatient', 'ImageType', 'InstanceCreationDate', 'InstanceCreationTime', 'InstanceCreatorUID',
                       'InstanceNumber', 'IssuerOfPatientID', 'KVP', 'LargestImagePixelValue', 'Manufacturer', 
                       'ManufacturerModelName', 'Modality', 'NumberOfFrames', 'PatientBirthDate', 'PatientID', 'PatientName',
                       'PatientPosition', 'PatientSetupSequence', 'PatientSex', 'PhotometricInterpretation', 'PixelData',
                       'PixelRepresentation', 'PixelSpacing', 'PositionReferenceIndicator', 'RTPlanDate', 'RTPlanDescription',
                       'RTPlanGeometry', 'RTPlanLabel', 'RTPlanName', 'RTPlanTime', 'ReferencedRTPlanSequence',
                       'ReferencedStructureSetSequence', 'ReferencedStudySequence', 'ReferringPhysicianName',
                       'RescaleIntercept', 'RescaleSlope', 'ReviewDate', 'ReviewerName', 'Rows', 'SOPClassUID', 
                       'SOPInstanceUID', 'SamplesPerPixel', 'SeriesInstanceUID', 'SeriesNumber', 'SliceLocation',
                       'SliceThickness', 'SmallestImagePixelValue', 'SoftwareVersions', 'SpecificCharacterSet',
                       'StationName', 'StructureSetDate', 'StructureSetTime', 'StudyDate', 'StudyDescription', 
                       'StudyID', 'StudyInstanceUID', 'StudyTime']
            instance_keys=instance_keys +['organs','len_of_associated_ct_slices','referenced_ct_series_uid']
            all_keys=instance_keys+['OrthancId','PatId','StudyId','StudyIdentifier',
                            'StudyDescription','SeriesIdentifier','SeriesDescription',
                            'SeriesDate']
            codes['instance_keys']=instance_keys
            codes['all_keys']=all_keys
            self.codes=codes
            self.u=True
          
    def get_instance_details(self,orthanc,instance_identifier):
        """A function that retrieves an orthanc file simplified tags associated with an instance identifier.
        Uses the request module in python to retrieve a bytes array.
        
        Parameters
        ------------
        orthanc : pyorthanc Orthanc variable 
            Connection to the orthanc details (not used can be empty/ used orginally with the first version). Left for the user if he/she wants to use later without using the requests module.
            
        instance_identifier: str
            Instance orthanc identifier
            
        Returns
        ---------
        dictionary: dictionary
            A dictionary with the simplified tag associated with the instance
            
        status: int
            An integer to indicate if the request to the server was successful. i.e. 200,401,etc.
        
        """
        try:
            #t=orthanc.get_instance_simplified_tags(instance_identifier)
            c=self.codes
            ipport=c['ipport']
            #the url to an instance in orthanc
            url=ipport+'/instances/'+instance_identifier+'/simplified-tags'
            response = requests.get(url, timeout=c['TIMEOUT'],auth=(c['username'],c['password']),verify=False) if len(c['username'])>0 else requests.get(url, timeout=c['TIMEOUT'],verify=False)
            status_code=response.status_code
            if status_code !=200:
                return {},status_code
            t=response.content
            t=json.loads(t)
            instance_keys=self.codes['instance_keys']#the keys expected to be found in an instance.
            z=len(instance_keys)
            values=['missing']*z
            dictionary = dict(zip(instance_keys, values))
            dictionary['InstanceIdentifier']=instance_identifier
            #set all the values in the new dataframe
            for key in t:#go through the collected dict
                if key in instance_keys:#check if this is a key that we need
                    dictionary[key]=t[key]
            #set the organs column:
            if 'StructureSetROISequence' in t:#this means its an RTSTRUCT
                try:#get the organs 
                    organs=[]
                    for i in t['StructureSetROISequence']:
                        if "ROIName" in i:
                            roiname=i['ROIName']
                        else:
                            roiname='missing'
                        if "ROIVolume" in i:
                            volume=i['ROIVolume']
                        else:
                            volume='missing'
                        organ={roiname:volume}
                        organs.append(organ)
                except:
                    organs=[]
            else:
                organs=[]
            
            dictionary['organs']=organs
            if 'ReferencedFrameOfReferenceSequence' in t:
                len_of_associated_ct_slices=len(t['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['RTReferencedSeriesSequence'][0]['ContourImageSequence'])
                referenced_ct_series_uid=t['ReferencedFrameOfReferenceSequence'][0]['RTReferencedStudySequence'][0]['RTReferencedSeriesSequence'][0]['SeriesInstanceUID']
            else:
                len_of_associated_ct_slices='missing'
                referenced_ct_series_uid='missing'
                
            dictionary['len_of_associated_ct_slices']=len_of_associated_ct_slices
            dictionary['referenced_ct_series_uid']=referenced_ct_series_uid
            
            return dictionary,200
        except Exception as e:
            print(e)
            return {},400      
    
    
    def generate_imaging_dataframe_threading(self,orthanc,OrthancId,PatId,save=True):
        """This function targets the Orthanc server and retrieves the summaries of all the patient related instances in the server to a pandas dataframe.
        
        This function uses threading to get the patient's summaries
        
        while collecting the studies, any study that does not contain all the required modalities listed in codes function will be removed.
        
        Parameters
        ------------
        orthanc : pyorthanc Orthanc variable 
            connection to the orthanc (pyorthanc variable). Not used (requests module used instead). Left as parameter if users wanted to change.  
            
        OrthancId: str
            Patient orthanc identifier
            
        PatId: str/int
            Patient identifier
            
        save: boolean
            A variable to indicate if to save the patient files. default True
            
        Returns
        -------
        df: pandas dataframe
            A pandas dataframe that contains the summaries of the patients instances with simplified tags
            
        comment: str
            A str with a comment that determines if the image summaries collection was successful (_SUCCESS) or not (_ERROR, _PATIENTFILESNOTFOUND)
        """
        print(PatId)
        list_of_instances=[]
        p=Patient(OrthancId,orthanc)#create a pyorthanc Patient instance
        patient_id=p.get_id()# get the patient id
        all_keys=self.codes['all_keys']
        if patient_id !=PatId and patient_id !=str(PatId):
            print("Different ids associated with the patient. ")
            patient_data=pd.DataFrame(columns=all_keys)
            if save:
                imagesummaries=self.codes['imagesummaries']
                if not os.path.exists(imagesummaries):# a directory that save all the patient's details
                    os.mkdir(imagesummaries)
                self.purge(imagesummaries, str(PatId))#to keep the latest attempt of data collection only.
                patient_data.to_csv(imagesummaries+str(PatId)+'_ERROR.csv',index=False)
            return patient_data,"_ERROR"
        #main_information=p.get_main_information()#get general information
        p.build_studies()# build the studies (needed in pyorthanc)
        studies=p.get_studies()# get the studies
        for study in studies:# for each study
            StudyId=study.get_id()
            remove_study=False
            StudyIdentifier=study.get_identifier()
            di=study.get_main_information()
            try:
                StudyDescription=di['MainDicomTags']['StudyDescription']
            except:
                StudyDescription='missing'
            study.build_series()
            study_serieses=study.get_series()#gets series objects
            codes=self.codes
            required_modalities_for_patient=codes['required_modalities_for_patient']
            #initial check to remove studies with no modalities
            modalities_in_study=[]
            for study_series in study_serieses:# collect the study series modalities
                 modality=study_series.get_modality()
                 modalities_in_study.append(modality)
            for modality in required_modalities_for_patient:
                if modality not in modalities_in_study:
                    remove_study=True
            
            if remove_study:#if the study doesnt have the required modalities.
                continue
            
            #This is used to add more modalities if needed for later use.
            required_modalities_for_patient_plus_rtplan=self.codes['required_modalities_for_patient_plus_rtplan']
            for study_series in study_serieses:
                SeriesIdentifier=study_series.get_identifier()
                modality=study_series.get_modality()
                if modality in required_modalities_for_patient_plus_rtplan:#you can collect other modalities
                    x=study_series.get_main_information()
                    try:#get series description
                        SeriesDescription=x['MainDicomTags']['SeriesDescription']
                        #print(series_description)
                    except:
                        SeriesDescription='missing' 
                        
                    try:#get series date
                        SeriesDate=x['MainDicomTags']['SeriesDate'] 
                    except:
                        SeriesDate='missing'
                        
                    di={'OrthancId':OrthancId,'PatId':PatId,'StudyId':StudyId,'StudyIdentifier':StudyIdentifier,
                        'StudyDescription':StudyDescription,'SeriesIdentifier':SeriesIdentifier,'SeriesDescription':SeriesDescription,
                        'SeriesDate':SeriesDate}#'SeriesNumber':SeriesNumber,'StationName':StationName,'SeriesInstanceUID':SeriesInstanceUID
                    instances=x['Instances']#get the instances in the series
                    len_instances=len(instances)
                    if len_instances>=100:
                        CONNECTIONS=self.codes['CONNECTIONS'] 
                    elif len_instances>50:
                        CONNECTIONS=50
                    elif len_instances>20:
                        CONNECTIONS=20
                    else:
                        CONNECTIONS=len_instances
                    out=[]
                    with concurrent.futures.ThreadPoolExecutor(max_workers=CONNECTIONS) as executor:
                        #this command stards the task for each URL in urls lists
                        future_to_url = (executor.submit(self.get_instance_details, orthanc,instance) for instance in instances)
                        #after running the task, check the results in each one. 
                        #as_completed does not return the values in order. 
                        for future in concurrent.futures.as_completed(future_to_url):
                            try:
                                di_instance,s = future.result()#get the result of each request
                            except Exception as exc:
                                print(exc)
                                s = str(exc)
                                #print(s)
                            finally:
                                di_instance.update(di)#add the study details to the record
                                list_of_instances.append(di_instance)#add the record 
                                out.append(s)
                    #check if data collection task was successful.
                    if list(set(out))!=[200]:
                        print(list(set(out)))
                        print("A number of Instances was not collected properly. This is due to the high number of requests targeting the server at the same time.")
                        patient_data=pd.DataFrame(columns=all_keys)
                        if save:
                            imagesummaries=self.codes['imagesummaries']
                            if not os.path.exists(imagesummaries):# a directory that save all the patient's details
                                os.mkdir(imagesummaries)
                            self.purge(imagesummaries, str(PatId))#to keep the latest attempt of data collection only.
                            patient_data.to_csv(imagesummaries+str(PatId)+'_ERROR.csv',index=False)
                        return patient_data,"_ERROR"
        
        if len(list_of_instances)==0:# no imaging data were found after removing studies that do not have the required modalities.
            patient_data=pd.DataFrame(columns=all_keys)
            comment="_IMAGINGDATANOTFOUND"
        else:          
            patient_data=pd.DataFrame(list_of_instances)              
            patient_data.sort_values(by=['SeriesNumber'],inplace=True,ascending=False)
            patient_data=patient_data.reset_index(drop=True)
            comment="_SUCCESS"
        if save:# if the decision was to save the scripts
            imagesummaries=self.codes['imagesummaries']
            if not os.path.exists(imagesummaries):# a directory that save all the patient's details
                os.mkdir(imagesummaries)
            self.purge(imagesummaries, str(PatId))#to keep the latest attempt of data collection only.
            patient_data.to_csv(imagesummaries+str(PatId)+comment+'.csv',index=False)
        return patient_data,comment    
    
    
    def verify_initial(self,PatId,notes):
        """A function that checks the dataframe that summarizes patient imaging files (resulted from generate_imaging_dataframe_threading()).
        It reports details about modalities listed in required_modalities in the codes function.
        

        Parameters
        ----------
        PatId : int/str 
            an int/str that represents the patient identifier
            
        notes: list
            a list that contains the notes assoicated with the verification, and is used to append new notes while verifying the patient files.
            
        Returns
        ---------
        df: Pandas dataframe
            A pandas dataframe with the verified imaging records, i.e the required modalities
            
        notes: list
            list of notes appended while verifying the patient's imaging files.

        """
        self.purge(self.codes['patientnotesdir'],str(PatId))#removes all the files related to the patient from from the associated directory
        dataframefilepath=''
        comment=''
        for filename in os.listdir(self.codes['imagesummaries']):
            if str(PatId) in filename:
                dataframefilepath=self.codes['imagesummaries']+filename
                #comment saves the data collection outcome: _SUCCESS, _ERROR, _PATIENTIMAGESNOTFOUND.
                comment=filename.split("_")[1].split(".csv")[0]
                break
        if len(dataframefilepath)==0:#patient image summary dataframe not found
            notes.append("I: Initial Verification: Patient details not found in the directory.")
            print("Patient details not found in the directory.")
            c='I_EXEC_001:EXECLUDE'
            notes.append(f"I:{c}")
            self.savepatientnotes(PatId,'imagesummary',['PATIENT IMAGE SUMMARY NOT FOUND'])
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return None,notes
        if comment !='SUCCESS':# error/patientimaging not found condition.
            if comment=='ERROR':# if there is an error that occurred while collecting the patients records from the orthanc server.
                notes.append("I: Initial Verification: ERROR in collected the dataset.")
                self.savepatientnotes(PatId,'imagesummary',['ERROR IN THE COLLECTION PROCESS'])
                self.savepatientnotes(PatId,'status','EXECLUDE')
                c='I_EXEC_002:EXECLUDE'
                self.savepatientnotes(PatId,'code',c)
                notes.append(f"I: {c}")
            else:#if the patient images were not found.
                notes.append("I: Initial Verification: IMAGING DATA NOT FOUND.")
                self.savepatientnotes(PatId,'imagesummary',['IMAGING DATA NOT FOUND'])
                self.savepatientnotes(PatId,'status','EXECLUDE')
                c='I_EXEC_003:EXECLUDE'
                self.savepatientnotes(PatId,'code',c)
                notes.append(f"I: {c}")
            print("patient details were either missing or a problem occured in collecion")
            return None,notes
        #read the csv file
        df=pd.read_csv(dataframefilepath)
        #get a raw summary of the patient's collected images.
        raw_images_summary=self.imagefile_summary(PatId,df)
        self.savepatientnotes(PatId,'raw_images_summary',raw_images_summary)#save to the patient's notes file
        df,notes=self.remove_phantom_studies(df.copy(),notes)# Remove phantom associated studies
        df,notes=self.remove_unused_rtstructs(df.copy(),notes)# Remove rtstruct with missing organs, i.e. an rtstruct with all the organs names missing.
        if df.shape[0]==0:#if after the first set of conditions, no records remain in the dataframe.
            notes.append("I: Initial Verification: Contained phantom study only (Patient cannot be included in the study).")
            c='I_EXEC_004:EXECLUDE'
            self.savepatientnotes(PatId,'code',c)
            notes.append(f"I: {c}")
            return None,notes
        # If a required modality was not found in all the patient's associated studies. i.e. the RTSTRUCT is required, and couldn't be found in any study.
        modalities=list(set(df['Modality'].tolist()))
        codes=self.codes
        required_modalities_for_patient=codes['required_modalities_for_patient']
        for modality in required_modalities_for_patient:
            if modality not in modalities:
                notes.append(f"I: Initial Verification: {modality} missing (Patient cannot be included in the study):{modality}.")
                c='I_EXEC_005:EXECLUDE'
                self.savepatientnotes(PatId,'code',c)
                notes.append(f"I: {c}")
                return df,notes
        studies=df['StudyIdentifier'].unique().tolist()
        #remove any study with a description not related to the cohort. e.g. lung keyword in study description for a breast study.
        study_desc_should_not_contain=self.codes['study_desc_should_not_contain']
        for study in studies:
            study_records=df.loc[df['StudyIdentifier']==study]#get the study records
            study_description_list=study_records['StudyDescription'].unique().tolist()#should be one element
            s= "".join(study_description_list).lower()#create a str of the description 
            for sds in study_desc_should_not_contain:
                if sds in s:#remove the study from the dataframe if a non eligible keyword was found.
                    notes.append(f"I: Initial Verification: ineligible keyword {sds} found in study description {s}. Check the key study_desc_should_not_contain in the associated configuration file.")
                    df=df.loc[df['StudyIdentifier']!=study]
                    df=df.reset_index(drop=True)
        
        studies=df['StudyIdentifier'].unique().tolist()#get the patient's studies list again.
        if df.shape[0]==0:
            notes.append("I: Initial Verification: The patient had no more available studies after removing studies with ineligible keywords in each study description.")
            c='I_EXEC_006:EXECLUDE'
            self.savepatientnotes(PatId,'code',c)
            notes.append(f"I: {c}")
            return df,notes
        if len(studies)==1:
            notes.append("I: Initial Verification: Patient has one associated study.")
            notes.append(f"I: I_SUCC_001:PROCEED:{PatId}")
            return df, notes
        
        v=len(studies)
        notes.append(f"I: Initial Verification: Patient has {v} multiple associated studies")
        notes.append(f"I: I_REV_001:LOW:{PatId}")
        #Remove any study with missing requirements (modalities)
        for study in studies:
            all_found=True
            study_records=df.loc[df['StudyIdentifier']==study]
            modalities=study_records['Modality'].unique().tolist()
            for modality in required_modalities_for_patient:
                if modality not in modalities:
                    all_found=False
            if not all_found:#some modalities are missing for the study     
                df=df.loc[df['StudyIdentifier']!=study]
                notes.append(f"I: Initial Verification: removed a study as it does not contain all the required modalities: {modality}")
                df=df.reset_index(drop=True)
        # Get the remaining studies again.
        studies=df['StudyIdentifier'].unique().tolist()
        if len(studies)==1:
            notes.append("I: Initial Verification: Conflict removed. only one study remains")
            notes.append(f"I: I_SUCC_002:PROCEED:{PatId}")
            return df, notes
        
        #patient having multiple studies, execlude for now. 
        notes.append("I: Initial Verification: The patient have multiple studies associated, discard. Patient data can be later exported to quarantine for review.")
        c='I_EXEC_007:EXECLUDE'
        self.savepatientnotes(PatId,'code',c)
        notes.append(f"I: {c}")
        return df, notes
        
        #THIS CONDITION IS NOT USED AT THIS STAGE.
        #Multiple studies obtained for the same patient that belongs to the same cancer site. Select the latest one, and set the patient for review. 
        if ['missing']==df['StudyDate'].unique().tolist():
            notes.append("I: Initial Verification: No dates associated with any of the studies")
            notes.append(f"I: I_REV_002:NORMAL:{PatId}")
        elif 'missing' in df['StudyDate'].unique().tolist():
            notes.append("I: Initi al Verification: missing dates for some of the studies, comparison without confidence between studies")
            notes.append(f"I: I_REV_003:LOW:{PatId}")
        else:
            notes.append("I:Initial Verification: no missing dates for some of the studies, comparison with confidence between studies")
        #select the latest study.
        x=df[['StudyIdentifier','StudyDate']].reset_index(drop=True)
        x=x.sort_values(by='StudyDate',ascending=False)
        x=x.drop_duplicates()
        x=x.reset_index(drop=True)
        latest_study=x['StudyIdentifier'].iloc[0]
        notes.append(f"I: Initial Verification:study selected:{latest_study}")
        df=df.loc[df['StudyIdentifier']==latest_study]#select the latest study only.
        df=df.reset_index(drop=True)
        
        return df, notes
 
    
    
    def verify_study(self,df,notes,modality='CT'):
        """Within this function, the links between different modalities are identified to find connections.
        
        In each of the child classes, the logic that connects the required modalities is implemented.
        
        """
        print("The parent function was called.")
        pass
    
    
    def generate_patients_data(self,firstversion):
        """A function that collects a set of patients required and verified files (CT slices, rt structs, etc.) from the orthanc server.
        
        It is expected that for each child, another function is created. 
        """
        print("You have called the parents version of generate_patients_data, which is an abstract class and should be overriden in each of the child classes.")
        pass

    
    
    def generate_orthanc_files_summaries(self,orthanc_ids,patients_ids):
        """A function that collects a set of patients images summaries from the orthanc server.
        
        Parameters
        ----------
        orthanc_ids : list 
            a list of orthanc ids
            
        patients_ids: list
            a list of patient ids
            
        Returns
        ---------
        pids: list
            the patient ids
            
        comments: list
            a list of the patients comments (_SUCCESS, _ERROR, or _PATIENTIMAGESNOTFOUND)
        
        """
        print(" process Id: "+str(os.getpid())+" parent id: "+str(os.getppid()))
        c=self.codes
        ipport=c['ipport']
        username=c['username']
        password=c['password']
        orthanc = Orthanc(ipport)
        if len(username)>0:
            orthanc.setup_credentials(username, password) 
        pids=[]
        comments=[]
        for orthanc_id,pat_id in zip(orthanc_ids,patients_ids):#generate the images files
            t,c=self.generate_imaging_dataframe_threading(orthanc,orthanc_id,str(pat_id),True)
            pids.append(pat_id)
            comments.append(c)
        return pids,comments
    
    
    def imagefiles_summaries(self,thedir):
        """A function that reloads all the patients summaries into a dataframe.
        
        Parameters
        ----------
        thedir : str 
            path to the directory with the patients files summaries.
            
            
        Returns
        -------
        thesummary: pandas dataframe
            a dataframe with the patients files summaries (i.e number of CTs, number of studies, etc.)
            
        """    
        list_of_dicts=[]
        for filename in os.listdir(thedir):
            df=pd.read_csv(thedir+filename)
            patient_id=filename.split(".csv")[0]
            di={}
            di['PatId']=patient_id
            #number of studies
            v=len(df['StudyIdentifier'].unique().tolist())
            di['number_of_patient_studies']=v
            
            codes=self.codes
            required_modalities_for_patient_plus_rtplan=codes['required_modalities_for_patient_plus_rtplan']
            for i in required_modalities_for_patient_plus_rtplan:
                v=len(df.loc[df['Modality']==i]['SeriesIdentifier'].unique().tolist())
                di['number_of_'+i+'_series']=v
                v=df.loc[df['Modality']==i].shape[0]
                di['number_of_'+i+'_instances']=v
            list_of_dicts.append(di)
            
        thesummary=pd.DataFrame.from_dict(list_of_dicts)
        return thesummary
    
    
    
    def imagefile_summary(self,patient_id,df):
        """A function that summarizes the records in a patient pandas dataframe
        
        Parameters
        ----------
        patient_id : int/str 
            patient identifier
            
        df: pandas dataframe
            a dataframe with the patient's image summaries saved as rows in the dataframe
            
        Returns
        -------
        di: dictionary
            a dictionary with the dataframe summary (i.e. number of CTs, number of studies)
            
        """        
        di={}
        di['PatId']=patient_id#patient id
        v=len(df['StudyIdentifier'].unique().tolist())#number of studies
        di['number_of_patient_studies']=v
            
        codes=self.codes
        required_modalities_for_patient_plus_rtplan=codes['required_modalities_for_patient_plus_rtplan']
        for i in required_modalities_for_patient_plus_rtplan:
            v=len(df.loc[df['Modality']==i]['SeriesIdentifier'].unique().tolist())
            di['number_of_'+i+'_series']=v
            v=df.loc[df['Modality']==i].shape[0]
            di['number_of_'+i+'_instances']=v
        
        return di
    
    
    def adapt_dataset_from_bytes(self,blob):
        """A function that changes a bytes array into a pydicom FileDataset
        

        Parameters
        ----------
        blob : bytes array 
            a str that consists of bytest
            
        Returns
        -------
        dataset: FileDataset
            A pydicom object 

        """
        # you can just read the dataset from the byte array
        dataset = pydicom.dcmread(BytesIO(blob))
        return dataset
    
    
    def remove_phantom_studies(self,df,patient_notes):
        """A function that identifies phantom studies and removes them.

        Parameters
        ----------
        df : pandas dataframe
            patient files summary dataframe
            
        patient_notes: list
            list with the patients notes in the initial verification task.
            
        Returns
        -------
        df : pandas dataframe
            a dataframe with no phantom studise
            
        patient_notes: list
            list with the patients notes in the initial verification task.
        """
        z=df.loc[df['SeriesDescription'].str.contains('phantom',case=False, na=False)]['StudyIdentifier'].tolist()
        z=list(set(z))
        if len(z)==0:
            patient_notes.append('I: Initial Verification: no phantom was found for the patient.')
            return df,patient_notes
        df=df.loc[~df['StudyIdentifier'].isin(z)]
        return df,patient_notes
    
    
    def check_if_organs_in_rtstruct(self,list_of_organs):
        """A function that checks if a list of organs is not found in the rtstruct
        
        Parameters
        ----------
        list_of_organs : list of organs
            the list of organs found in the rtstruct and to be checked.
            
        Returns
        -------
        boolean: boolean
            a boolean value to indicate that the rtstruct contain usable target volumes
            
        """        
        list_of_organs=[s.lower() for s in list_of_organs]
        possibilities=self.codes['possibilities']
        for p in possibilities:
            for q in list_of_organs:
                if p in q:
                    return True
        return False
        
    def remove_unused_rtstructs(self,df,notes):
        """A function that removes rtstructs with no target volumes related to any of the possible studies.
        i.e. any rtstruct without any keyword such as ptv, ctv, heart, or lung will be removed.
        
        Parameters
        ----------
        df : pandas dataframe
            patient image files summary dataframe
            
        notes : list
            patient verfication notes list
            
        Returns
        -------
        df : pandas dataframe
            patient image files summary dataframe with removed ununsed rtstructs, if any
            
        notes : list
            patient verfication notes list with updated notes, if any
            
        """ 
        #get the rtstructs with the organs
        x=df.loc[df['Modality']=='RTSTRUCT'][['organs','InstanceIdentifier']]
        #list of organs
        organs=x['organs'].tolist()
        #list of instances identifiers 
        instances=x['InstanceIdentifier'].tolist()
        #change the str to list for better comparison
        organs=[eval(o) for o in organs]
        for dict_of_organs,instance in zip(organs,instances):
            if len(dict_of_organs)==0:#to match cases like empty list []
                df=df.loc[df['InstanceIdentifier']!=instance].reset_index(drop=True)
                notes.append("I: Initial Verification: RTSTRUCT with no ROIs !.")
            else:
                #get the unique list of keys in the organs list
                rf = set().union(*(d.keys() for d in dict_of_organs))
                rf=list(rf)
                #check if the list_of_organs contains meaningful values
                c=self.check_if_organs_in_rtstruct(rf)
                if not c:#if there was no organ that should be checked.
                    #delete the rtstruct
                    df=df.loc[df['InstanceIdentifier']!=instance].reset_index(drop=True)
                    notes.append(f"I: Initial Verification: RTSTRUCT with no organs associated with in a study was removed. {instance}")
        return df,notes
            
        
    
    def search_for_code(self,notes,code):
        """A function that searches for a code in a list of notes associated with a patient.
        
        Parameters
        ----------
        notes : list
            list of patient's notes
            
        code : str
            a code to search for in a list of strs
            
        Returns
        -------
        boolean
            True if the code is in the list of strs, otherwise False.
        """ 
        for note in notes:
            s=note.split(":")
            s=[n.strip() for n in s]
            if code in s:
                return True
        return False
    
    
    def recommendation(self,patientnotes):
        """A function that recommends the patient inclusion in the study based on a list of patient notes.
        
        Parameters
        ----------
        patientnotes : list
            list of patient's notes
            
            
        Returns
        -------
        str
            recommendation (SUCCESS, REVIEW, or EXECLUDE)
            
        codes : list
            list of patient codes collected from the list of notes.
        """ 
        review_codes=[]
        success_codes=[]
        exec_codes=[]
        for i in patientnotes:
            z=i.split(":")
            if len(z)<=2:
                continue
            if "_EXEC_" in z[1]:
                exec_codes.append(z[1])
                exec_codes.append(z[2])
            if "_REV_" in z[1]:
                review_codes.append(z[1])
                review_codes.append(z[2])
            if "_SUCC_" in z[1]:
                success_codes.append(z[1])
                success_codes.append(z[2])
        if len(exec_codes)==0:
            if len(review_codes)==0:
                return "SUCCESS",success_codes
            else:
                return "REVIEW",review_codes
        else:
            return "EXECLUDE",exec_codes
        
    
    
    def savepatientnotes(self,pid,thekey,patientnotes):
        """A function that adds a list of patient notes with a key to the patient notes JSON file.
        
        Parameters
        ----------
        pid : int/str
            Patient identifier
            
        thekey : str
            The type of the notes to be saved
            
        patientnotes : list 
            A list of strs to save the the patient's notes file
            
        """ 
        patientnotesdir=self.codes['patientnotesdir']
        if not os.path.exists(patientnotesdir):# a directory that save all the patient's details
            os.mkdir(patientnotesdir)
        #set the file name
        filename=patientnotesdir+str(pid)+'.json'
        if not os.path.isfile(filename):# a directory that save all the patient's details
            data = {}
            data[thekey]=patientnotes
            with open(filename, 'w') as outfile:
                json.dump(data, outfile)
        else:
            with open(filename) as json_file:
                data = json.load(json_file)
            data[thekey]=patientnotes
            with open(filename, 'w') as outfile:
                json.dump(data, outfile)
    
    
    def loadpatientnotes(self,pid):
        """A function that loads the patient notes based on the patient's identifier.
        
        Parameters
        ----------
        pid : int/str
            Patient identifier
            
        Returns
        -------
        data : dictionary
            Patient dictionaty with various types of notes. i.e. collection, retrieval, verification, etc.
            
        """         
    
        patientnotesdir=self.codes['patientnotesdir']
        filename=patientnotesdir+str(pid)+'.json'
        if not os.path.isfile(filename):
            print(f" file {filename} does not exist")
            return
        with open(filename) as json_file:
            data = json.load(json_file)
        return data
    
    
      
    def prepare_patient_directory(self,adict,remove_old=True):
        """A function that prepares the patient directories. i.e. CT directory, RTSTRUCTs directory, etc.
        
        Parameters
        ----------
        adict : dictionary
            a patient dictionary to add the paths to
            
        remove_old: boolean
            an attribute used to specify if the old directory should be removed
            
        Returns
        -------
        adict : dictionary
            patient dictionary with the updates paths to the directories, where data collected from the orthan server will be saved.
            
        """ 
        an_id=adict['PatId']
        datadirectory=self.codes['datadirectory']
        thedir=datadirectory+str(an_id)+"/"
        if remove_old:
            if os.path.isdir(thedir):
                shutil.rmtree(thedir)
        ct_directory=thedir+'CT/'
        rtdoses_directory=thedir+'RTDOSE/'
        rtdoses_directory_nifti=thedir+'RTDOSEnifti/'
        rtstruct_directory=thedir+'RTSTRUCT/'
        masks_directory=thedir+'masks/'
        nifti_directory=thedir+'CTnifti/'
    
        if not os.path.exists(thedir):# a directory that save all the patient's details
            os.mkdir(thedir)
        if not os.path.exists(ct_directory):
            os.mkdir(ct_directory)
        if not os.path.exists(rtdoses_directory):
            os.mkdir(rtdoses_directory)
        if not os.path.exists(rtdoses_directory_nifti):
            os.mkdir(rtdoses_directory_nifti)
        if not os.path.exists(rtstruct_directory):
            os.mkdir(rtstruct_directory)
        if not os.path.exists(masks_directory):
            os.mkdir(masks_directory)
        if not os.path.exists(nifti_directory):
            os.mkdir(nifti_directory)
        
        adict['thedir']=thedir
        adict['ct_directory']=ct_directory
        adict['rtdoses_directory']=rtdoses_directory
        adict['rtdoses_directory_nifti']=rtdoses_directory_nifti
        adict['rtstruct_directory']=rtstruct_directory
        adict['masks_directory']=masks_directory
        adict['nifti_directory']=nifti_directory
        return adict   
          
       
    def purge(self,adir, pattern):
        """A function that removes any file with a keyword in the variable pattern from a directory.
        It is used with patients where file/directory should be removed.
        
        Parameters
        ----------
        adir : str 
            a directory
            
        pattern: str
            a str value, where all filenames that contain this keyword will be removed.
            
        """      
        for f in os.listdir(adir):
            if re.search(pattern, f):
                os.remove(os.path.join(adir, f))
        
    
    def get_ct_threading(self,orthanc,adict,notes):
        """A function that collects the patient's CT instances through a set of threads.
        With threading the returned files might return out of order. At the same time, the instances associated with the CT might not be in the correct order.
        For this reason, each set of CT instances is checked based on SliceLocation and PatientImagePosition tags.
        
        Parameters
        ----------
        orthanc : pyorthanc Orthanc instance
            a pyorthanc Orthanc class instance, used to get the CT instance identifiers.
            
        adict: dictionary
            a dict with the paths to patient files location (where to save CT instances).
            
        notes: list
            a list of patient notes
            
            
        Returns
        -------
        notes : list
            a list of the patient's notes with updates about the CT collection task, if any.
            
        """ 
        
        try:
            ct_directory=adict['ct_directory']
            ct_identifier=adict['CT_orthanc_identifier']#orthanc identifier of the CT
            series_slices = orthanc.get_series_ordered_slices(ct_identifier) #get information of the CT
            CONNECTIONS = self.codes['CONNECTIONS'] #number of threads
            files = []#files to save instances
            out=[] #out saves the status of each request.
            urls=series_slices['Dicom']#urls of each instance 
            ipport=self.codes['ipport']
            urls=[ipport+url for url in urls]#url for each request
            #Start the thread pool executor:
            with concurrent.futures.ThreadPoolExecutor(max_workers=CONNECTIONS) as executor:
                #this command stards the task for each URL in urls lists
                future_to_url = (executor.submit(self.load_url, url) for url in urls)
                time1 = time.time()
                #after running the task, check the results in each one. 
                #as_completed does not return the values in order. 
                for future in concurrent.futures.as_completed(future_to_url):
                    try:
                        data,s = future.result()#get the result of each request
                    except Exception as exc:
                        s = str(type(exc))
                    finally:
                        data=self.adapt_dataset_from_bytes(data)
                        files.append(data)
                        out.append(s)
            
                time2 = time.time()
            notes.append(f'XI: CT retrieval:Took {time2-time1:.2f} s')
            out=list(set(out))#check if there was an error while retieving one of the instances.
            if out!=[200]:
                notes.append("XI: CT retrieval: Issue in retrieving CT slices.")
                notes.append(f"XI: CT retrieval: {out}")
                notes.append("XI: XI_EXEC_002: EXECLUDE")
                return notes
            #check details about slice location and imagepatientposition
            slices_SliceLocation=[]
            slices_ImagePositionPatient = []
            skipcount_SliceLocation = 0
            skipcount_ImagePositionPatient=0
            for f in files:#add details about SliceLocation and ImagePositionPatient
                if hasattr(f, 'SliceLocation'):
                    slices_SliceLocation.append(f)
                else:
                    skipcount_SliceLocation = skipcount_SliceLocation + 1
                if hasattr(f, 'ImagePositionPatient'):
                    slices_ImagePositionPatient.append(f)
                else:
                    skipcount_ImagePositionPatient = skipcount_ImagePositionPatient + 1  
            notes.append(f"XI: CT retrieval: skipped, no SliceLocation: {skipcount_SliceLocation}")
            notes.append(f"XI: CT retrieval: skipped, no ImagePositionPatient: {skipcount_ImagePositionPatient}")
            notes.append("XI: CT retrieval: retrieved the CT series instances to the local directory.")
            list_of_instances=[]#list of dictionaries
            if skipcount_SliceLocation==0:#will check based on SliceLocation
                for fi in files:
                    di={'SliceLocation':fi.SliceLocation, 'dicom':fi}
                    list_of_instances.append(di)
            else:#if there was missing values in the SlicesLocations
                if skipcount_ImagePositionPatient==0:#check based on ImagePatientPosition
                    for fi in files:
                        x=list(fi.ImagePositionPatient)#get image patient position
                        if len(x)!=3:#
                            notes.append("XI: CT retrieval: unexpected value found in imagepatientposition.")
                            notes.append("XI: XI_EXEC_001: EXECLUDE")
                            return notes
                        v=float(x[2])#third dimension will be used to sort the CT instances
                        di={'SliceLocation':v, 'dicom':fi}
                        list_of_instances.append(di)
                else:            
                    notes.append("XI: CT retrieval: cannot sort retrieved instances.")
                    notes.append("XI: XI_EXEC_001: EXECLUDE")
                    return notes   
            #sort the list
            newlist = sorted(list_of_instances, key=lambda k: k['SliceLocation'])
            all_locations=[]
            final_list=[]
            for a in newlist:#remove duplicate slicelocations or patient image positions
                if a['SliceLocation'] in all_locations:
                    continue
                final_list.append(a)
                all_locations.append(a['SliceLocation'])
            for idx,a in enumerate(final_list):
                a['dicom'].InstanceNumber=idx+1#override the instance number.
                a['dicom'].save_as(ct_directory+str(idx)+'.dcm')
            notes.append("XI: XI_SUCC_001:PROCEED")
        
        except Exception as e:#if for any reason, the CT collection failed.
            notes.append(f"XI: CT retrieval: {e}")
            notes.append("XI: CT retrieval: Failed to retrieve the patient's CT.")
            notes.append("XI: XI_EXEC_02: EXECLUDE")
            #return the notes.
        return notes
        
       
    def get_ct_nifti(self,adict,notes):
        """A function that creates CT nifti file.

        Parameters
        ----------
        adict : dictionary
            a dictionary with a key to the CT instances directory i.e. adict['ct_directory']
              
        notes: list
            a list of patient notes
            
            
        Returns
        -------
        notes : list
            a list of the patient's notes with updates about the CT nifti file generation task.
            
        """ 
        ct_directory=adict['ct_directory']
        nifti_directory=adict['nifti_directory']
        PatId=adict['PatId']
        CT_SeriesIdentifier=adict['CT_SeriesIdentifier']
        notes.append("XII: CTnifti generation")
        try:
            #load all the image files using the sitk file reader.
            #This does not mean that the files will be loaded as required.
            files_names=list(sitk.ImageSeriesReader.GetGDCMSeriesFileNames(ct_directory))
            list_of_indices= []
            for file_name in files_names:
                list_of_indices.append(int(file_name.split(".dcm")[0].split("/")[-1]))
            #sort the filesnames based on the list of indices 
            files_names= [x for _,x in sorted(zip(list_of_indices,files_names))]
            files_names=tuple(files_names)#map to tuple since sitk ReadImage function works with tuples.
            #make sure that the order of the images is correct in the generated tuple.
            ct_img = sitk.ReadImage(files_names)
            filename=f'{nifti_directory}{PatId}_{CT_SeriesIdentifier}.nii.gz'
            sitk.WriteImage(ct_img, filename)
            notes.append("XII: CTnifti generation: Successfully added the CT nifti file to its directory")
            notes.append("XII: XII_SUCC_001:PROCEED")
        except Exception as e:
            print(e)
            notes.append(f"XII: CTnifti generation: {e}")
            notes.append("XII: CTnifti generation: Failed to generate the patient's CTnifti.")
            notes.append("XII: XII_EXEC_001: EXECLUDE")
            
        return notes
        
      
    def get_rtstruct(self,orthanc,adict,notes):
        """A function that collects the patient rt struct files. RTSTRUCTS collected based on instances

        Parameters
        ----------
        orthanc: pyorthanc Orthanc instance
            not used anymore, used originally to retrieve the rtstructs, before moving to requests.
        
        adict : dictionary
            a dictionary with a key to the path to save the retieved RTSTRUCTS i.e. adict['rtstructs_directory']
              
        notes: list
            a list of patient notes
            
            
        Returns
        -------
        notes : list
            a list of the patient's notes with updates about the rtstruct collection task.
            
        """
        try:
            rtstruct_directory=adict['rtstruct_directory']
            RTSTRUCT_orthanc_identifiers=adict['RTSTRUCT_orthanc_identifiers']#instances associated with the dictionary
            RTSTRUCT_SOPInstanceUID=adict['RTSTRUCT_SOPInstanceUID']#use to name the rtstructs
            notes.append("XIII: RTSTRUCTS retrieval")
            c=self.codes
            ipport=c['ipport']
            #id, dicom id
            for rtstruct_instance_identifier,sop in zip(RTSTRUCT_orthanc_identifiers,RTSTRUCT_SOPInstanceUID):
                ip_port_url=ipport+'/instances/'+rtstruct_instance_identifier+'/file'
                f,statuscode=self.load_url(ip_port_url)#get the file
                if statuscode !=200:
                    notes.append(f"XIII: RTSTRUCTS retrieval: failed to retrieve an RTSTRUCT: {rtstruct_instance_identifier}")
                    notes.append("XIII: XIII_EXEC_001: EXECLUDE")
                    return notes
                else:
                    DICOMStruct = self.adapt_dataset_from_bytes(f)# get the file in bytes
                    #structNameSequence = ["_".join(i.ROIName.split()) for i in DICOMStruct.StructureSetROISequence]
                    DICOMStruct.save_as(rtstruct_directory+"/"+ str(sop) +'_rtstruct.dcm')
                    notes.append("XIII: RTSTRUCTS retrieval: added an RTSTRUCT instance to the RTSTRUCT directory.")
            notes.append("XIII: XIII_SUCC_001: PROCEED")
        except Exception as e:
            notes.append(f"XIII: RTSTRUCTS retrieval: {e}")
            notes.append("XIII: RTSTRUCTS retrieval: failed to retrieve the RTSTRUCTs.")
            notes.append("XIII: XIII_EXEC_001: EXECLUDE")
        
        return notes
        
    
    def get_masks_nifti(self,adict,notes):
        """A function that uses a convert RTSTRUCT function developed by RF & PC to convert rt struct ROIs to nifti masks.
        It saves the created files to the patient directory.

        Parameters
        ----------
        adict: dictionary
            A dictionary that contains the patient details.
                    
        notes: list
            a list of patient notes
            
            
        Returns
        -------
        notes : list
            a list of the patient's notes with updates about the masks generation process.
            
        """
        try:
            ct_directory=adict['ct_directory']
            rtstruct_directory=adict['rtstruct_directory']
            masks_directory=adict['masks_directory']
            notes.append("XIV: RTSTRUCTS nifti masks generation.")
            sops=adict['RTSTRUCT_SOPInstanceUID']
            PatId=adict['PatId']
            #each directory will hold the masks found in an SOPInstanceUID
            for sop in sops:
                instance_masks_dir=masks_directory+sop+'/'
                #print(instance_masks_dir)
                if not os.path.exists(instance_masks_dir):# a directory that save all the patient's details
                    os.makedirs(instance_masks_dir)
                pre = 'patient_'+str(PatId)+"_" # Define a prefix for generated masks
                #for each instance associated with the file, generate the masks
                filename=f'{rtstruct_directory}{sop}_rtstruct.dcm'
                convert_rtstruct(ct_directory,filename, prefix=pre, output_dir=instance_masks_dir)
                #notes.append("Step: added the masks to the masks directory.")
            notes.append("XIV: XIV_SUCC_001:PROCEED ")
        except Exception as e:
            notes.append(f'XIV: RTSTRUCTS nifti masks generation: {e}')
            notes.append("XIV: RTSTRUCTS nifti masks generation: failed to generate the nifti masks for the patients.")
            notes.append("XIV: XIV_EXEC_001:EXECLUDE")
            c='XIV_EXEC_001:EXECLUDE'
            self.savepatientnotes(PatId,'code',c)
        return notes
        

    def get_rtplan(self,orthanc,adict,notes):
        """A function that retrieves the patients associated RTPLAN.

        Parameters
        ----------
        
        adict: dictionary
            A dictionary that contains the patient details.
              
        notes: list
            a list of patient notes
              
        Returns
        -------
        
        notes : list
            a list of the patient's notes with updates about the RTPLAN retrieve task.
            
        """
        try:
            rtplans_directory=adict['rtplans_directory']
            #rtdoses_directory_nifti=adict['rtdoses_directory_nifti']
            RTPLAN_orthanc_identifiers=adict['RTPLAN_orthanc_identifiers']
            RTPLAN_SOPInstanceUID=adict['RTPLAN_SOPInstanceUID']
            notes.append("XV: RTPLAN retrieval.")
            c=self.codes
            ipport=c['ipport']
            for rtplan,sop in zip(RTPLAN_orthanc_identifiers,RTPLAN_SOPInstanceUID):
                ip_port_url=ipport+'/instances/'+rtplan+'/file'
                f,statuscode=self.load_url(ip_port_url)#get the file
                #f=orthanc.get_instance_file(rtdose)#get the instance identifier
                if statuscode !=200:
                    notes.append(f"XV: RTPLAN Retrieval: failed to retrieve an RTPLAN: {rtplan}")
                    notes.append("XV: XV_EXEC_001: EXECLUDE")
                    return notes
                else:
                    DICOMStruct = self.adapt_dataset_from_bytes(f)# get the file in bytes
                    filename=f'{rtplans_directory}{sop}.dcm'
                    DICOMStruct.save_as(filename)

            x=len(RTPLAN_orthanc_identifiers)
            notes.append(f"XV: RTPLAN Retrieval: added {x} RTPLANS into the RTPLANS directory. ")
            notes.append("XV: XV_SUCC_001: PROCEED")
            
        except Exception as e:
            notes.append(f"XV: RTPLAN retieval: Exception {e}")
            notes.append("XV: XV_EXEC_002: EXECLUDE")
        
        return notes

        
      
    def get_rtdoses(self,orthanc,adict,notes):
        """A function that retrieves the patients associated RTDOSES with the selected study. It saves the collected files 
        to the patient directory pid/RTDOSE/UID.dcm. It also exports the file to a nifti file. It should be noted that in the RTDOSES
        all the files will be saved in the same folder, unlike the RTSTRUCTS where each struct will have a seperate folder. 

        Parameters
        ----------
        
        adict: dictionary
            A dictionary that contains the patient details.
              
        notes: list
            a list of patient notes
              
        Returns
        -------
        
        notes : list
            a list of the patient's notes with updates about the RTDOSE retrieve task.
            
        """
        try:
            rtdoses_directory=adict['rtdoses_directory']
            rtdoses_directory_nifti=adict['rtdoses_directory_nifti']
            RTDOSE_orthanc_identifiers=adict['RTDOSE_orthanc_identifiers']
            RTDOSE_SOPInstanceUID=adict['RTDOSE_SOPInstanceUID']
            notes.append("XVI: RTDOSE retrieval.")
            c=self.codes
            ipport=c['ipport']
            for rtdose,sop in zip(RTDOSE_orthanc_identifiers,RTDOSE_SOPInstanceUID):
                ip_port_url=ipport+'/instances/'+rtdose+'/file'
                f,statuscode=self.load_url(ip_port_url)#get the file
                #f=orthanc.get_instance_file(rtdose)#get the instance identifier
                if statuscode !=200:
                    notes.append(f"XVI: RTDOSE Retrieval: failed to retrieve an RTDOSE: {rtdose}")
                    notes.append("XVI: XVI_EXEC_001: EXECLUDE")
                    return notes
                else:
                    DICOMStruct = self.adapt_dataset_from_bytes(f)# get the file in bytes
                    filename=f'{rtdoses_directory}{sop}.dcm'
                    DICOMStruct.save_as(filename)
                    #read the dicom object through sitk and save as nifti
                    itk_dose = sitk.ReadImage(filename)#read the RT DOSE
                    
                    itk_dose = sitk.Cast(itk_dose, sitk.sitkFloat32) * float(DICOMStruct.DoseGridScaling) # apply the scaling
                    niftifilename=filename=f'{rtdoses_directory_nifti}{sop}.nii.gz'
                    sitk.WriteImage(itk_dose,niftifilename)

            x=len(RTDOSE_orthanc_identifiers)
            notes.append(f"XVI: RTDOSE Retrieval: added {x} rtdose instances with dosesummationtype as PLAN to the RTDOSE directory. ")
            notes.append("XVI: XVI_SUCC_001: PROCEED")
            
        except Exception as e:
            notes.append(f"XVI: RTDOSE Retrieval: Exception {e}")
            notes.append("XVI: XVI_EXEC_002: EXECLUDE")
        
        return notes
            
           
    def get(self,orthanc,adict):
        """An abstract function.
        
        """
        return []
        
    
    
    def load_url(self,url):
        """A function that uses the requests module to target the orthanc server.
        
        Parameters
        ----------
        url : str
            a url to a file location (usually an instance file)
            
            
        Returns
        -------
        content : request content
            an attribute with the patient content (with instances it should be a bytes array).
            
        status_code: int
            the response code (i.e 200, 401, etc.)
            
        """ 
        c=self.codes
        response = requests.get(url, timeout=c['TIMEOUT'],auth=(c['username'],c['password']),verify=False) if len(c['username'])>0 else requests.get(url, timeout=c['TIMEOUT'],verify=False)
        return response.content, response.status_code    
        
      
    def load_roi_names_from_rtstuct(self,rtstruct_path,notes):
        """ A function that can be used to extract ROI names from the patient rtstruct file.

        Parameters
        ----------
        
        rtstruct_path: str
            Path to the RTSTRUCT file in the patient directory.
        
 
        notes: list
            a list of patient notes
            
            
        Returns
        -------
        notes : list
            a list of the patient's notes with updates about the RTSTRUCT ROIs.
            
        """
        DICOMStruct = pydicom.read_file(rtstruct_path, force=True)
        #structPointSequence=DICOMStruct.ROIContourSequence
        structNameSequence = ["_".join(i.ROIName.split()) for i in DICOMStruct.StructureSetROISequence]
        notes.append("Adding structure names.")
        notes.append(structNameSequence) # Get the ROIs from the struct and save.
        return structNameSequence,notes
    
    
    def load_ct_nifti_2_numpyarray(self,adict,notes):
        """ A function used to load the patient CT nifti file into a 3D numpy array.

        Parameters
        ----------
        
        adict: dict
            A dictionary that contains the patient details.
        
        notes: list
            a list of patient notes
            
            
        Returns
        -------

        thect: 3D numpy array
            The collected 3D array
            
        spacing: tuple
            The ct image spacing, empty array is returned if an error occured.
            
        notes : list
            a list of the patient's notes with updates about the RTSTRUCT ROIs.
                
        """
        try:
            nifti_directory=adict['nifti_directory']
            PatId=adict['PatId']
            CT_SeriesIdentifier=adict['CT_SeriesIdentifier']
            filename=f'{nifti_directory}{PatId}_{CT_SeriesIdentifier}.nii.gz'
            notes.append("XXI: loading the CTnifti to a numpy array.")
            ct_image=sitk.ReadImage(filename)
            thect = sitk.GetArrayFromImage(ct_image)#get the image from array 
            notes.append('XXI: XXI_SUCC_001: PROCEED')
            return thect,ct_image.GetSpacing(),notes
        except Exception as e:
            notes.append(f'XXI: loading CT: EXCEPTION {e}')
            notes.append('XXI: XXI_EXEC_001:EXECLUDE')
            thect=np.asarray([])
            return thect,thect, notes
    
    
    def load_nifti_mask_2_numpyarray(self,pid,nifti_mask_path,notes):
        """ A function used to load a patient mask into a 3D numpy array

        Parameters
        ----------
        
        pid: int
            patient id
            
        nifti_mask_path: str
            path to the nifti mask
            
        notes: list
            a list of patient notes
            
            
        Returns
        -------

        thect: 3D numpy array
            The collected 3D array mask
            
        sn: str
            name of the mask
            
        notes : list
            a list of the patient's notes with updates on reading the mask from the nifti file.
                
        """
        try:
            if nifti_mask_path.endswith(".nii.gz"):
                #get the 3d numpy array
                mask_image=sitk.ReadImage(nifti_mask_path)
                nda = sitk.GetArrayFromImage(mask_image)#get the array which is the mask. Z is X index
                #get the mask name
                s=nifti_mask_path.split("patient_"+str(pid)+"_")
                sn=s[-1].split(".nii.gz")[0]
                notes.append("XXII: XXII loading masks: loaded the mask to numpy array:"+str(sn))
                return nda,sn,notes
        except:
            notes.append("XXII: XXII loading masks: failed to load the mask ")
            notes.append("XXII: XXII_REV_002: NORMAL")
            mask=np.asarray([])
            return mask, "failed mask",notes
        
    
    def load_nifti_masks(self,adict,notes):
        """ A function used to load the patient nifti masks to a list of 3D numpy arrays.

        Parameters
        ----------
        
        adict: dict
            A dictionary that contains the patient details.
        
        notes: list
            a list of patient notes
            
            
        Returns  
        -------

        list_of_masks: list
            The list of 3D numpy arrays
            
        name_of_masks: list
            The list of the OARs and TV
            
        roi_masks: dict
            A dict with keys as (mask0,mask1,mask2) represnting each roi in name_of_masks. i.e. roiname at position 0 in the list name_of_masks is mask0 and so on.
            
        notes : list
            a list of the patient's notes with updates on loading the nifti masks.
                
        """
        masks_directory=adict['masks_directory']
        sops=adict['RTSTRUCT_SOPInstanceUID']
        PatId=adict['PatId']
                
        list_of_masks=[]
        name_of_masks=[]
        notes.append("XXII: XXII loading masks to numpy arrays.")
        if len(os.listdir(masks_directory))==0:
            notes.append("XXII: XXII loading masks: No mask folders found in the directory")
            notes.append("XXII: XXII_EXEC_001:EXECLUDE")
            return list_of_masks,name_of_masks,[],notes
        for sop in sops:
            dir_name=masks_directory+sop+'/'
            #check if empty
            if len(os.listdir(dir_name))==0:
                notes.append("XXII: XXII loading masks: no masks were found for the RTSTRUCT. ")
                notes.append("XXII: XXII_REV_001: NORMAL")
                continue
            for filename in os.listdir(dir_name):
                if filename.endswith(".nii.gz"):
                    mask_path=dir_name+filename
                    nda,sn,notes=self.load_nifti_mask_2_numpyarray(PatId,mask_path,notes)
                    if sn in name_of_masks:
                        if sn!="failed mask":
                            notes.append("XXII: XXII loading masks: multiple masks referring to the same roi names, possibly a duplicate.")
                            notes.append("XXII: XXII_REV_003: NORMAL")
                    list_of_masks.append(nda)
                    name_of_masks.append(sn)
        if len(list_of_masks)==0:
            notes.append("ERROR while loading the masks.")
            return list_of_masks,name_of_masks,[],notes
        roi_masks={}#need to save in a directory to match the new code 
        counter=0
        for i in list_of_masks:#numpy array of mat structs
            maskname='mask'+str(counter)
            roi_masks[maskname]=i
            counter=counter+1
        notes.append("XXII: XXII loading masks: loaded all the patient's masks.")
        notes.append("XXII: XXII_SUCC_001:PROCEED")
        return list_of_masks,name_of_masks,roi_masks,notes
    
    
 

    
    
    def load_doses_2_numpyarray(self,adict,notes):
        """ A function used to load the patient dicom RTDOSES to a list of 3D numpy arrays.

        Parameters
        ----------
        
        adict: dict
            A dictionary that contains the patient details.
        
        notes: list
            a list of patient notes
            
            
        Returns 
        ---------

        doseGrids: list
            The list of 3D numpy arrays representing each dose grid
            
        notes : list
            a list of the patient's notes with updates on loading the dose grids.
                
        """
        try:
            notes.append("XXIII: XXIII loading RTDOSES")
            #get the path to the ct nifti file.
            nifti_directory=adict['nifti_directory']
            PatId=adict['PatId']
            CT_SeriesIdentifier=adict['CT_SeriesIdentifier']
            ctnifti_path=f'{nifti_directory}{PatId}_{CT_SeriesIdentifier}.nii.gz'
            ct_image=sitk.ReadImage(ctnifti_path)
            
            sops=adict['RTDOSE_SOPInstanceUID']#get the sops associated with the study
            rtdoses_directory=adict['rtdoses_directory']
            doseGrids=[]
            for sop in sops:
                #Dose grid scaling
                filename=sop+'.dcm'
                dcm_rtdose = pydicom.read_file(rtdoses_directory+filename, force=True)#read the dicom image
                itk_dose = sitk.ReadImage(rtdoses_directory+filename)#read the RT DOSE
                itk_dose = sitk.Cast(itk_dose, sitk.sitkFloat32) * float(dcm_rtdose.DoseGridScaling) # apply the scaling
                new_dose = sitk.Resample(itk_dose,ct_image)
                #sitk.WriteImage(new_dose,filename)
                doseGrid=sitk.GetArrayFromImage(new_dose)
                doseGrids.append(doseGrid)
                notes.append("XXIII: XXIII loading RTDOSES: added an RTDOSE numpy array: "+str(sop))
            notes.append("XXIII: XXIII_SUCC_001: PROCEED")
            return doseGrids,notes
        except Exception as e:
            notes.append(f"XXIII: XXIII loading RTDOSES: {e}")
            notes.append("XXIII: XXIII loading RTDOSES: Failed to add the RTDOSES.")
            notes.append("XXIII: XXIII_EXEC_001:EXECLUDE")
            doseGrids=np.asarray([])
            return doseGrids,notes
            
            
    
    def select_and_combine_dosegrids(self,doseGrids,notes):
        """ A function used to select the dose grids. This function is used to handle the logic for combining dose grids.

        Parameters
        ----------
        
        doseGrids: list
            The list of 3D numpy arrays representing each dose grid
        
        notes: list
            a list of patient notes
            
            
        Returns 
        ---------

        doseGrid: 3D numpy array
            The final 3D dose grid
            
        notes : list
            a list of the patient's notes with updates on loading the dose grids.
                
        """        
        notes.append("XXIV: XXIV select RTDOSES")
        if len(doseGrids)==0:
            notes.append("XXIV: XXIV select RTDOSES: No dosegrids associated with the list")
            notes.append("XXIV: XXIV_EXEC_001:EXECLUDE")
            final_dosegrid=np.asarray([])
            return notes,[],final_dosegrid
        #the verification dose will be lower than the other ones since it is per fraction
        maxs=[]
        selectdoses=[]
        for d in doseGrids:
            m=max(d.ravel())
            maxs.append(m)
            if m<3: # Checking dose girds with small max dose. Kept if at some point, such doses will be excluded. 
                notes.append("XXIV: select dosegrids: dose grid with small max dose. ")
            selectdoses.append(d)
        
        if len(selectdoses)==0:
            notes.append("XXIV: XXIV select RTDOSES: No dosegrids associated with the study.")
            notes.append("XXIV: XXIV_EXEC_002:EXECLUDE")
            final_dosegrid=np.asarray([])
            return notes,[],final_dosegrid
            
        #Add a test case to check the sum of the grids. 
        sum_dosegrids_max=sum(maxs)
        suspicious_max_dose_lower_bound=self.codes['suspicious_max_dose_lower_bound']
        suspicious_max_dose_upper_bound=self.codes['suspicious_max_dose_upper_bound']
        
        if sum_dosegrids_max<=suspicious_max_dose_lower_bound:
            notes.append(f"XXIV: XXIV select RTDOSES: Low dose received. Sum of max values in dose grids less than {suspicious_max_dose_lower_bound}.")
        if sum_dosegrids_max>=suspicious_max_dose_upper_bound:
            notes.append(f"XXIV: XXIV select RTDOSES: Max dose received. Sum of max values in dose grids higher than {suspicious_max_dose_upper_bound}.")
        
        notes.append(f"XXIV: XXIV select RTDOSES: Maximum of rt doses: {maxs}")
        final_dosegrid=np.zeros(doseGrids[0].shape)
        for d in selectdoses:
            final_dosegrid=final_dosegrid+d
        if sum_dosegrids_max<=suspicious_max_dose_lower_bound or sum_dosegrids_max>=suspicious_max_dose_upper_bound:
            notes.append("XXIV: XXIV_EXEC_003:EXECLUDE")
        else:
            notes.append("XXIV: XXIV_SUCC_001:PROCEED")
        
        return final_dosegrid,maxs,notes
            
            

    
    def load(self,pid,notes,df,ctnifti_path,masks_directory,rtdoses_directory):
        """An abstract function.
        """
        
        
        return []
        

    
    def export_2_matlab(self,filename,patdict):
        """A function to save the dictionary generated into a matlab file.
        """
        import hdf5storage
        import h5py
        matlabfiles=self.codes['matlabfiles']
        if not os.path.exists(matlabfiles):
            os.mkdir(matlabfiles)
        hdf5storage.savemat(matlabfiles+filename,patdict)
        
    
    def export_2_pickle(self,filename,patdict):
        """A function to save the dictionary generated into a pickle file.
        """
        picklefiles=self.codes['picklefiles']
        if not os.path.exists(picklefiles):
            os.mkdir(picklefiles)
        with open(picklefiles+filename, 'wb') as f:  
            pickle.dump(patdict, f)     
            


class patientImagingCRDP(patientImaging):
    """This class was used to collect and process datasets where connections between CT, RTSTRUCTS,RTDOSES, PLANS are required.
    """

    def __init__(self,codesconfig=None):
        super().__init__(codesconfig)


    def verify_study(self,df,notes,modality='CT'):
        """Within this function, the links between different modalities are identified to find connections.
        It is expected that each CT will have associated RTSTRUCTS which will also have associated RTPLAN (SOPinstanceUID),
        which will also have links to the RTDOSES. 
        By finding these links, we try to remove any unused RTDOSES, RTSTRUCTS, CTs
        
        To do that, the CT SeriesInstanceUID links to the RTSTRUCT through the tag: ReferencedFrameOfReferenceSequence -- > SeriesInstanceUID
        The RTSTRUCT SOPInstanceUID links to RTPLAN instances through the tag: ReferencedStructureSetSequence --> ReferencedSOPInstanceUID
        The RTDOSE SOPInstanceUID links to the RTPLAN instances through the tag: ReferencedRTPlanSequence -->
        
        By that, it is assumed that the modalities, files used in treatment will be all connected.
        
        Any study with no connections will be discarded. Any study with multiple connections will be discarded
        
        
        Parameters
        ----------
        df : Pandas dataframe 
            a dataframe with the patient imaging records
            
        notes: list
            a list that contians the notes, and is used to append new notes while verifying the patient files.
            
        Returns
        -------
        list_of_values: list of dicts
            A list of dictionaries that contain the details of associations between studies objects.
            
        notes: list
            list of notes appended while verifying the patient's imaging files.
        
        """
        PatId=df['PatId'].unique().tolist()[0]
        notes.append("II: Study verification")
        cts=df.loc[df['Modality']=='CT']['SeriesInstanceUID'].unique().tolist()
        cts_len=len(cts)
        if cts_len==0:#if no CTs were found in the study
            notes.append("II: Study verification: Patient has no associated CT modality.")
            c='II_EXEC_001:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        
        list_of_values=[]# a list of dictionaries that will save the connections in the study between the cts, structs, and doses.
        for ct in cts:#for each CT inside the study
            notes.append(f"II: Study verification: Checking CT series: {ct}")
            StudyDate=df.loc[df['SeriesInstanceUID']==ct]['StudyDate'].iloc[0]#get the date of the study.
            StructureSetDate=df.loc[df['SeriesInstanceUID']==ct]['StructureSetDate'].iloc[0]#get the series instance UIDs that has the CT, and get the date. 
            
            t=df.loc[(df['Modality']=='RTSTRUCT')&(df['referenced_ct_series_uid']==ct)][['SOPInstanceUID','SeriesIdentifier']]#get the rtstructs with the selected as the referenced_ct_series_uid.
            rtstructs_SOPs=t['SOPInstanceUID'].tolist()#the rt structs with a link to the ct series identifier
            if len(rtstructs_SOPs)==0:
                notes.append("II: Study verification: NO RTSTRUCTS assoicated with the CT, Discard the CT")
                continue
            
            #RTPLANS
            #get the rtplan instances that reference to the rtstruct SOPs
            rtplan_twocolumns=df.loc[df['Modality']=='RTPLAN'][['SOPInstanceUID','ReferencedStructureSetSequence']]
            rtplan_twocolumns=df.loc[df['ReferencedStructureSetSequence']!='missing']
            rtplans_SOPs=rtplan_twocolumns['SOPInstanceUID'].tolist()
            if len(rtplans_SOPs)==0:#no rtplans associated with the rtstruct.
                notes.append("II: Study verification:No RTPLANS associated witht the RTSTRUCT associated with the CT, Discard")
                continue
            ReferencedStructureSetSequence=rtplan_twocolumns['ReferencedStructureSetSequence'].tolist()
            ReferencedStructureSetSequence=[eval(i) for i in ReferencedStructureSetSequence]
            ReferencedSOPInstanceUIDs_RTPLAN_to_RTSTRUCT=[e[0]['ReferencedSOPInstanceUID'] for e in ReferencedStructureSetSequence]
            
            di={'rtplans_SOPs':rtplans_SOPs,'RTPLAN_to_RTSTRUCT':ReferencedSOPInstanceUIDs_RTPLAN_to_RTSTRUCT}
            x=pd.DataFrame(di)
            #select the RTPLAN instances that are linked to the list of the rtstruct instances that are linked to the ct identifier.
            final_rtplans_SOPs=x.loc[x['RTPLAN_to_RTSTRUCT'].isin(rtstructs_SOPs)]['rtplans_SOPs'].tolist()
            if len(final_rtplans_SOPs)==0:
                notes.append("II: Study verification:No RTPLANS associated witht the RTSTRUCT associated with the CT, Discard")
                continue
            #get the RTDOSE instances that are linked to the list of rtplan instances that are linked to the rtstruct instances that are linked to the ct idenifier.
            #get the referenced RTPLAN instance from the dicom tag ReferencedRTPlanSequence
            rtdose_twocolumns=df.loc[df['DoseSummationType']=='PLAN'][['SOPInstanceUID','ReferencedRTPlanSequence']]
            rtdoses_SOPs=rtdose_twocolumns['SOPInstanceUID'].tolist()
            ReferencedRTPlanSequence=rtdose_twocolumns['ReferencedRTPlanSequence'].tolist()
            #remove missing values
            #ReferencedRTPlanSequence=list(filter(lambda a: a != 'missing', ReferencedRTPlanSequence))
            if len(ReferencedRTPlanSequence)==0:
                notes.append("II: Study verification:No RTDOSES associated with the RTPLANS associated with the RTSTRUCT associated with the CT, Discard.")
                notes.append("")
                continue
            ReferencedRTPlanSequence=[eval(i) for i in ReferencedRTPlanSequence]#assuming that all the values in b are lists with no missing values
            #b is now a list of lists.Each list contains a dictionary. we need the ReferencedSOPInstanceUID
            #ReferencedSOPInstanceUID contains the references 
            ReferencedSOPInstanceUIDs_RTDOSE_2_RTPLAN=[e[0]['ReferencedSOPInstanceUID'] for e in ReferencedRTPlanSequence]
            
            di={'rtdoses_SOPs':rtdoses_SOPs,'RTDOSE_to_RTPLAN':ReferencedSOPInstanceUIDs_RTDOSE_2_RTPLAN}
            x=pd.DataFrame(di)
            final_dose_SOPs=x.loc[x['RTDOSE_to_RTPLAN'].isin(final_rtplans_SOPs)]['rtdoses_SOPs'].tolist()
            #print("Final doses")
            #print(final_dose_SOPs)
            if len(final_dose_SOPs)==0:
                notes.append("II: Study verification:No RTDOSES associated with the approved RTPLAN associated with the RTSTRUCT associated with the CT, Discard")
                notes.append("")
                continue
            
            #get the CT series Identifier
            CT_orthanc_identifier=df.loc[df['SeriesInstanceUID']==ct]['SeriesIdentifier'].unique().tolist()[0]#one value expected
            #get the rt structs identifiers
            RTSTRUCT_orthanc_identifiers=df.loc[df['SOPInstanceUID'].isin(rtstructs_SOPs)]['InstanceIdentifier'].tolist()
            #get the dose instance identifiers
            RTDOSE_orthanc_identifiers=df.loc[df['SOPInstanceUID'].isin(final_dose_SOPs)]['InstanceIdentifier'].tolist()
            #get the plan instances identifiers
            RTPLAN_orthanc_identifiers=df.loc[df['SOPInstanceUID'].isin(final_rtplans_SOPs)]['InstanceIdentifier'].tolist()
            
            StudyDate=None if math.isnan(StudyDate) else StudyDate
            StudyDate=None if StudyDate is None else int(StudyDate)
            di={'PatId':PatId,'CT_SeriesIdentifier':ct,'RTSTRUCT_SOPInstanceUID':rtstructs_SOPs,'StructureSetDate':StructureSetDate,'StudyDate':StudyDate,
                'RTDOSE_SOPInstanceUID':final_dose_SOPs,'RTPLAN_SOPInstanceUID':final_rtplans_SOPs,
                'CT_orthanc_identifier':CT_orthanc_identifier,'RTSTRUCT_orthanc_identifiers':RTSTRUCT_orthanc_identifiers,
                'RTDOSE_orthanc_identifiers':RTDOSE_orthanc_identifiers,'RTPLAN_orthanc_identifiers':RTPLAN_orthanc_identifiers}
            list_of_values.append(di)
        

        #Verify the ct size (number of instances is large)
        list_of_values_1=[]
        for adict in list_of_values:
            ct_identifier=adict['CT_SeriesIdentifier']
            PatId=adict['PatId']
            u=df.loc[df['SeriesInstanceUID']==ct_identifier].shape
            if u[0]>500:
                notes.append(f"II: CT verification: Large number of instances associated with the patient CT: {u[0]}")
                notes.append("Removing a dictionary from the list")
                continue
                #list_of_values = list(filter(lambda i: i['CT_SeriesIdentifier'] != '', list_of_values))
            elif u[0]>380:
                notes.append(f"II: CT verification: Large number of instances associated with the patient CT: {u[0]}")
                notes.append(f"II: II_REV_001:SEVERE:{PatId}")
            if u[0]<50:
                notes.append("II: CT verification: Low number of instances associated with the patient CT.")
                notes.append(f"II: II_REV_002:SEVERE:{PatId}")
                continue
            #if it arrives here, this means everything is normal.
            list_of_values_1.append(adict)  
                
        if len(list_of_values_1)==0:
            notes.append("II: Study verification: Patient has no associations between modalities.")
            c='II_EXEC_002:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        elif len(list_of_values_1)==1:
            notes.append("II: Study verification: Patient has one CT associated with RTSTRUCTS and RTDOSES.")
            notes.append(f"II: II_SUCC_001:PROCEED:{PatId}")
        else:
            notes.append("II: Study verification: Patient has multiple associations between modalities, must be reviewed. Discard for now.")
            c='II_EXEC_003:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            #saving the multiple dictionaries
            self.savepatientnotes(PatId,'list_of_values',list_of_values_1)   
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        
        self.savepatientnotes(PatId,'list_of_values',list_of_values_1)    
        return list_of_values_1,notes   

        
    def generate_patients_data(self,firstversion):
        """A function that collects a set of patients required and verified files (CT slices, rt structs, etc.) from the orthanc server.
        
        Parameters
        ----------
        orthanc_ids : list 
            a list of orthanc ids
            
        patients_ids: list
            a list of patient ids
            
        Returns
        -------
        pids: list
            the patient ids
            
        comments: list
            a list of the patients comments (_SUCCESS, _ERROR, or _PATIENTIMAGESNOTFOUND)
        """
        execlude="EXECLUDE"
        c=self.codes
        version=c['version']
        ipport=c['ipport']
        username=c['username']
        password=c['password']
        link_to_ids=c['link_to_ids']
        #load the csv file that contains all the anynomized ids and their associated orthanc ids
        #it is worth mentioning that orthanc has its own ids
        x=pd.read_csv(link_to_ids)
        x=x.loc[x['ids'].isin(firstversion)].reset_index(drop=True)
        orthanc_ids=x['orthanc_ids'].tolist()
        patients_ids=x['ids'].tolist()        
        orthanc = Orthanc(ipport)
        if len(username)>0:
            orthanc.setup_credentials(username, password) 
        patients_to_execlude=[]
        patients_to_review=[]
        patients_passed=[]
        for pid,orthanc_id in zip(patients_ids,orthanc_ids):
            print(pid)
            try:
                #initial verifiction,checks phantom studies, studies with no modalities, rtstructs with empty columns.
                df,verification_notes=self.verify_initial(pid,[])
                recommendation, codes= self.recommendation(verification_notes)
                if recommendation ==execlude:#if condition to stop
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'verification_notes',verification_notes)
                    continue
                #At this stage, the study is selected.
                list_of_values,verification_notes=self.verify_study(df,verification_notes)#link modalities in the studies
                recommendation, codes= self.recommendation(verification_notes)
                self.savepatientnotes(pid,'verification_notes',verification_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    continue
                verified_images_summary=self.imagefile_summary(pid,df)
                self.savepatientnotes(pid,'verified_images_summary',verified_images_summary)
                
                adict=list_of_values[0]#should be one value only
                adict=self.prepare_patient_directory(adict)#add the directories
                self.savepatientnotes(pid,'list_of_values',adict)  #to add links to the directories of the images
                self.savepatientnotes(pid,'version',version) 
                #Retieve the images in the study to the patient directory
                retrieval_notes=[]
                
                retrieval_notes=self.get_ct_threading(orthanc,adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                    continue
                
                retrieval_notes=self.get_ct_nifti(adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                    continue
                
                retrieval_notes=self.get_rtstruct(orthanc,adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                    continue
                
                
                retrieval_notes=self.get_masks_nifti(adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                    continue
                
                
                retrieval_notes=self.get_rtdoses(orthanc,adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    continue
                
                loading_notes=[]
                thect,getspacing,loading_notes=self.load_ct_nifti_2_numpyarray(adict,loading_notes)
                recommendation, codes= self.recommendation(loading_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'loading_notes',loading_notes)
                    continue
                
                
                list_of_masks,name_of_masks,roi_masks,loading_notes=self.load_nifti_masks(adict,loading_notes)
                recommendation, codes= self.recommendation(loading_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'loading_notes',loading_notes)
                    continue
                
                
                doseGrids,loading_notes=self.load_doses_2_numpyarray(adict,loading_notes)
                recommendation, codes= self.recommendation(loading_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'loading_notes',loading_notes)
                    continue
                
                final_dosegrid,maxs,loading_notes=self.select_and_combine_dosegrids(doseGrids,loading_notes)
                recommendation, codes= self.recommendation(loading_notes)
                self.savepatientnotes(pid,'loading_notes',loading_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    continue
                
                StudyDate=adict['StudyDate']
                StructureSetDate=adict['StructureSetDate']
                patdict = {"ct_image": thect, 
                   "dose_data": final_dosegrid,
                   "roi_names":name_of_masks,
                   "roi_masks":roi_masks,
                  "PixelSpacing":getspacing, 'StudyDate':StudyDate,
                  "StructureSetDate": str(StructureSetDate)}
                
                patdict['version']=version
                #filename=str(pid)+"_RS"+str(orthanc_id)+'.mat'
                #self.export_2_matlab(filename,patdict)
                patient_notes=verification_notes +retrieval_notes + loading_notes
                recommendation,codes=self.recommendation(patient_notes)
                self.savepatientnotes(pid,'status',recommendation)
                self.savepatientnotes(pid,'patientimagingfilesready',True)
                if recommendation=='REVIEW':
                    patients_to_review.append(pid)
                if recommendation=='SUCCESS':
                    patients_passed.append(pid)
            except Exception as e:
                print(e)
                print(f'{pid} had an exception while working with data. ')
                patients_to_execlude.append(pid)
        return patients_to_execlude,patients_to_review,patients_passed
    
    
class patientImagingCRD(patientImagingCRDP):
    """This is the class used to collect the patients data where the CT & the RTSTRUCT & RTDOSE are only required.
    With no plans required, all the RTDOSES in the study will be linked to the CT, which is not always the right approach.
    
    
    """

    def __init__(self,codesconfig=None):
        super().__init__(codesconfig)
        print('This class should be used when CTs+RTSTRUCTS + RTDOSES are required.')
        print('Checking the required modalities key in the associated configuration file.')
        req_moda=['CT','RTSTRUCT','RTDOSE']
        if not all(modalit in self.codes['required_modalities_for_patient'] for modalit in req_moda):
            print(f'A required modality is not added. Please add the required modalities {req_moda} to the configuration file.')
            self.u=False


    def verify_study(self,df,notes,modality='CT'):
        """Within this function, the links between different modalities are identified to find connections.
        It is expected that each CT will have associated RTSTRUCTS which will also have associated RTPLAN (SOPinstanceUID),
        which will also have links to the RTDOSES. 
        By finding these links, we try to remove any unused RTDOSES, RTSTRUCTS, CTs
        
        To do that, the CT SeriesInstanceUID links to the RTSTRUCT through the tag: ReferencedFrameOfReferenceSequence -- > SeriesInstanceUID
        The RTSTRUCT SOPInstanceUID links to RTPLAN instances through the tag: ReferencedStructureSetSequence --> ReferencedSOPInstanceUID
        The RTDOSE SOPInstanceUID links to the RTPLAN instances through the tag: ReferencedRTPlanSequence -->
        
        By that, it is assumed that the modalities, files used in treatment will be all connected.
        
        Any study with no connections will be discarded. Any study with multiple connections will be discarded
        
        
        Parameters
        ----------
        df : Pandas dataframe 
            a dataframe with the patient imaging records
            
        notes: list
            a list that contians the notes, and is used to append new notes while verifying the patient files.
            
        Returns
        -------
        list_of_values: list of dicts
            A list of dictionaries that contain the details of associations between studies objects.
            
        notes: list
            list of notes appended while verifying the patient's imaging files.
        
        """
        PatId=df['PatId'].unique().tolist()[0]
        notes.append("II: Study verification")
        cts=df.loc[df['Modality']=='CT']['SeriesInstanceUID'].unique().tolist()
        cts_len=len(cts)
        if cts_len==0:#if no CTs were found in the study
            notes.append("II: Study verification: Patient has no associated CT modality")
            c='II_EXEC_001:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        
        list_of_values=[]# a list of dictionaries that will save the connections in the study between the cts, structs, and doses.
        for ct in cts:#for each CT inside the study
            notes.append(f"II: Study verification: Checking CT series: {ct}")
            StudyDate=df.loc[df['SeriesInstanceUID']==ct]['StudyDate'].iloc[0]#get the date of the study.
            StructureSetDate=df.loc[df['SeriesInstanceUID']==ct]['StructureSetDate'].iloc[0]#get the series instance UIDs that has the CT, and get the date. 
            
            t=df.loc[(df['Modality']=='RTSTRUCT')&(df['referenced_ct_series_uid']==ct)][['SOPInstanceUID','SeriesIdentifier']]#get the rtstructs with the selected as the referenced_ct_series_uid.
            rtstructs_SOPs=t['SOPInstanceUID'].tolist()#the rt structs with a link to the ct series identifier
            if len(rtstructs_SOPs)==0:
                notes.append("II: Study verification: NO RTSTRUCTS assoicated with the CT, Discard the CT")
                continue
            
            #with the study verification, as there is no RTPLAN, it will be assumed that all the RTDOSES are linked to the CT. 

            rtdose_twocolumns=df.loc[df['DoseSummationType']=='PLAN'][['SOPInstanceUID']]
            rtdoses_SOPs=rtdose_twocolumns['SOPInstanceUID'].tolist()
            final_dose_SOPs=rtdoses_SOPs
            #print("Final doses")
            #print(final_dose_SOPs)
            if len(final_dose_SOPs)==0:
                notes.append("II: Study verification:No RTDOSES associated with the approved RTPLAN associated with the RTSTRUCT associated with the CT, Discard")
                notes.append("")
                continue
            
            #get the CT series Identifier
            CT_orthanc_identifier=df.loc[df['SeriesInstanceUID']==ct]['SeriesIdentifier'].unique().tolist()[0]#one value expected
            #get the rt structs identifiers
            RTSTRUCT_orthanc_identifiers=df.loc[df['SOPInstanceUID'].isin(rtstructs_SOPs)]['InstanceIdentifier'].tolist()
            #get the dose instance identifiers
            RTDOSE_orthanc_identifiers=df.loc[df['SOPInstanceUID'].isin(final_dose_SOPs)]['InstanceIdentifier'].tolist()
            
            StudyDate=None if math.isnan(StudyDate) else StudyDate
            StudyDate=None if StudyDate is None else int(StudyDate)
            di={'PatId':PatId,'CT_SeriesIdentifier':ct,'RTSTRUCT_SOPInstanceUID':rtstructs_SOPs,'StructureSetDate':StructureSetDate,'StudyDate':StudyDate,
                'RTDOSE_SOPInstanceUID':final_dose_SOPs,
                'CT_orthanc_identifier':CT_orthanc_identifier,'RTSTRUCT_orthanc_identifiers':RTSTRUCT_orthanc_identifiers,
                'RTDOSE_orthanc_identifiers':RTDOSE_orthanc_identifiers}
            list_of_values.append(di)
        

        #Verify the ct size (number of instances is large)
        list_of_values_1=[]
        for adict in list_of_values:
            ct_identifier=adict['CT_SeriesIdentifier']
            PatId=adict['PatId']
            u=df.loc[df['SeriesInstanceUID']==ct_identifier].shape
            if u[0]>500:
                notes.append(f"II: CT verification: Large number of instances associated with the patient CT: {u[0]}")
                notes.append("Removing a dictionary from the list")
                continue
                #list_of_values = list(filter(lambda i: i['CT_SeriesIdentifier'] != '', list_of_values))
            elif u[0]>380:
                notes.append(f"II: CT verification: Large number of instances associated with the patient CT: {u[0]}")
                notes.append(f"II: II_REV_001:SEVERE:{PatId}")
            if u[0]<50:
                notes.append("II: CT verification: Low number of instances associated with the patient CT.")
                notes.append(f"II: II_REV_002:SEVERE:{PatId}")
                continue
            #if it arrives here, this means everything is normal.
            list_of_values_1.append(adict)  
                
        if len(list_of_values_1)==0:
            notes.append("II: Study verification: Patient has no assoications between modalities")
            c='II_EXEC_002:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        elif len(list_of_values_1)==1:
            notes.append("II: Study verification: Patient has one CT associated with RTSTRUCTS and RTDOSES")
            notes.append(f"II: II_SUCC_001:PROCEED:{PatId}")
        else:
            notes.append("II: Study verification: Patient has multiple assoications between modalities, must be reviewed. Discard for now.")
            c='II_EXEC_003:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        
        self.savepatientnotes(PatId,'list_of_values',list_of_values_1)    
        return list_of_values_1,notes   

        


class patientImagingCR(patientImaging):
    """This is the class used to collect the patients data where the CT & the RTSTRUCT are only required.
    
    
    """

    def __init__(self,codesconfig=None):
        super().__init__(codesconfig)
    
    
    def verify_study(self,df,notes,modality='CT'):
        """Within this function, the links between different modalities are identified to find connections.
        It is expected that each CT will have associated RTSTRUCTS 
        To do that, the CT SeriesInstanceUID links to the RTSTRUCT through the tag: ReferencedFrameOfReferenceSequence -- > SeriesInstanceUID
        
        
        Parameters
        ----------
        df : Pandas dataframe 
            a dataframe with the patient imaging records
            
        notes: list
            a list that contians the notes, and is used to append new notes while verifying the patient files.
            
        Returns
        -------
        list_of_values: list of dicts
            A list of dictionaries that contain the details of associations between studies objects.
            
        notes: list
            list of notes appended while verifying the patient's imaging files.
        
        """
        PatId=df['PatId'].unique().tolist()[0]
        notes.append("II: Study verification")
        cts=df.loc[df['Modality']=='CT']['SeriesInstanceUID'].unique().tolist()
        cts_len=len(cts)
        if cts_len==0:#if no CTs were found in the study
            notes.append("II: Study verification: Patient has no associated CT modality")
            c='II_EXEC_001:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        
        list_of_values=[]# a list of dictionaries that will save the connections in the study between the cts, structs, and doses.
        for ct in cts:
            notes.append(f"II: Study verification: Checking CT series: {ct}")
            StudyDate=df.loc[df['SeriesInstanceUID']==ct]['StudyDate'].iloc[0]
            StructureSetDate=df.loc[df['SeriesInstanceUID']==ct]['StructureSetDate'].iloc[0]
            t=df.loc[(df['Modality']=='RTSTRUCT')&(df['referenced_ct_series_uid']==ct)][['SOPInstanceUID','SeriesIdentifier']]
            rtstructs_SOPs=t['SOPInstanceUID'].tolist()#the rt structs with a link to the ct series identifier
            if len(rtstructs_SOPs)==0:
                notes.append("II: Study verification: No RTSTRUCTS assoicated with the CT, Discard")
                continue
            
            #get the CT series Identifier
            CT_orthanc_identifier=df.loc[df['SeriesInstanceUID']==ct]['SeriesIdentifier'].unique().tolist()[0]#one value expected
            #get the rt structs identifiers
            RTSTRUCT_orthanc_identifiers=df.loc[df['SOPInstanceUID'].isin(rtstructs_SOPs)]['InstanceIdentifier'].tolist()
            
            StudyDate=None if math.isnan(StudyDate) else StudyDate
            StudyDate=None if StudyDate is None else int(StudyDate)
            di={'PatId':PatId,'CT_SeriesIdentifier':ct,
                'RTSTRUCT_SOPInstanceUID':rtstructs_SOPs,
                'StructureSetDate':StructureSetDate,
                'StudyDate':StudyDate,
                'CT_orthanc_identifier':CT_orthanc_identifier,
                'RTSTRUCT_orthanc_identifiers':RTSTRUCT_orthanc_identifiers}
            list_of_values.append(di)
        

        #Verify the ct size (number of instances is large)
        list_of_values_1=[]
        for adict in list_of_values:
            ct_identifier=adict['CT_SeriesIdentifier']
            PatId=adict['PatId']
            u=df.loc[df['SeriesInstanceUID']==ct_identifier].shape
            if u[0]>500:
                notes.append(f"II: CT verification: Large number of instances associated with the patient CT: {u[0]}")
                notes.append("Removing a dictionary from the list")
                continue
                #list_of_values = list(filter(lambda i: i['CT_SeriesIdentifier'] != '', list_of_values))
            elif u[0]>380:
                notes.append(f"II: CT verification: Large number of instances associated with the patient CT: {u[0]}")
                notes.append(f"II: II_REV_001:SEVERE:{PatId}")
            if u[0]<50:
                notes.append("II: CT verification: Low number of instances associated with the patient CT.")
                notes.append(f"II: II_REV_002:SEVERE:{PatId}")
                continue
            #if it arrives here, this means everything is normal.
            list_of_values_1.append(adict)  
                
        if len(list_of_values_1)==0:
            notes.append("II: Study verification: Patient has no assoications between modalities")
            c='II_EXEC_002:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        elif len(list_of_values_1)==1:
            notes.append("II: Study verification: Patient has one CT associated with RTSTRUCTS.")
            notes.append(f"II: II_SUCC_001:PROCEED:{PatId}")
        else:
            notes.append("II: Study verification: Patient has multiple assoications between modalities, must be reviewed. Discard for now.")
            c='II_EXEC_003:EXECLUDE'
            notes.append(f"II: {c}")
            self.savepatientnotes(PatId,'status','EXECLUDE')
            self.savepatientnotes(PatId,'code',c)
            return [],notes
        
        self.savepatientnotes(PatId,'list_of_values',list_of_values_1)    
        return list_of_values_1,notes 
    
    
    def generate_patients_data(self,firstversion):
        """A function that collects a set of patients required and verified files
        (CT slices, rt structs, etc.) from the orthanc server.
        
        Parameters
        ----------
        orthanc_ids : list 
            a list of orthanc ids
            
        patients_ids: list
            a list of patient ids
            
        Returns
        -----------
        pids: list
            the patient ids
            
        comments: list
            a list of the patients comments (_SUCCESS, _ERROR, or _PATIENTIMAGESNOTFOUND)
        """
        execlude="EXECLUDE"
        c=self.codes
        version=c['version']
        ipport=c['ipport']
        username=c['username']
        password=c['password']
        link_to_ids=c['link_to_ids']
        #load the csv file that contains all the anynomized ids and their associated orthanc ids
        #it is worth mentioning that orthanc has its own ids
        x=pd.read_csv(link_to_ids)
        x=x.loc[x['ids'].isin(firstversion)].reset_index(drop=True)
        orthanc_ids=x['orthanc_ids'].tolist()
        patients_ids=x['ids'].tolist()        
        orthanc = Orthanc(ipport)
        if len(username)>0:
            orthanc.setup_credentials(username, password) 
        patients_to_execlude=[]
        patients_to_review=[]
        patients_passed=[]
        for pid,orthanc_id in zip(patients_ids,orthanc_ids):
            print(pid)
            try:
                #initial verifiction,checks phantom studies, studies with no modalities, rtstructs with empty columns.
                df,verification_notes=self.verify_initial(pid,[])
                recommendation, codes= self.recommendation(verification_notes)
                if recommendation ==execlude:#if condition to stop
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'verification_notes',verification_notes)
                    continue
                #At this stage, the study is selected.
                list_of_values,verification_notes=self.verify_study(df,verification_notes)#link modalities in the studies
                recommendation, codes= self.recommendation(verification_notes)
                self.savepatientnotes(pid,'verification_notes',verification_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    continue
                verified_images_summary=self.imagefile_summary(pid,df)
                self.savepatientnotes(pid,'verified_images_summary',verified_images_summary)
                
                adict=list_of_values[0]#should be one value only
                adict=self.prepare_patient_directory(adict)#add the directories
                self.savepatientnotes(pid,'list_of_values',adict)  #to add links to the directories of the images
                self.savepatientnotes(pid,'version',version) 
                #Retieve the images in the study to the patient directory
                retrieval_notes=[]
                
                retrieval_notes=self.get_ct_threading(orthanc,adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                    continue
                
                retrieval_notes=self.get_ct_nifti(adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                    continue
                
                retrieval_notes=self.get_rtstruct(orthanc,adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                    continue
                
                
                retrieval_notes=self.get_masks_nifti(adict,retrieval_notes)
                recommendation, codes= self.recommendation(retrieval_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'retrieval_notes',retrieval_notes)
                    continue
                
                #if data needed in matlab files.
                """
                loading_notes=[]
                thect,getspacing,loading_notes=self.load_ct_nifti_2_numpyarray(adict,loading_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'loading_notes',loading_notes)
                    continue
                
                
                list_of_masks,name_of_masks,roi_masks,loading_notes=self.load_nifti_masks(adict,loading_notes)
                if recommendation ==execlude:#if not execlude, go to next step
                    patients_to_execlude.append(pid)
                    self.savepatientnotes(pid,'loading_notes',loading_notes)
                    continue
                self.savepatientnotes(pid,'loading_notes',loading_notes)
                StudyDate=adict['StudyDate']
                StructureSetDate=adict['StructureSetDate']
                patdict = {"ct_image": thect, 
                   "roi_names":name_of_masks,
                   "roi_masks":roi_masks,
                  "PixelSpacing":getspacing, 'StudyDate':StudyDate,
                  "StructureSetDate": str(StructureSetDate)}
                
                patdict['version']=version
                filename=str(pid)+"_RS"+str(orthanc_id)+'.mat'
                self.export_2_matlab(filename,patdict)
                    
                """
                patient_notes=verification_notes +retrieval_notes 
                recommendation,codes=self.recommendation(patient_notes)
                self.savepatientnotes(pid,'status',recommendation)
                self.savepatientnotes(pid,'patientimagingfilesready',True)
                if recommendation=='REVIEW':
                    patients_to_review.append(pid)
                if recommendation=='SUCCESS':
                    patients_passed.append(pid)
            except Exception as e:
                print(e)
                print(f'{pid} had an exception while working with data. ')
                patients_to_execlude.append(pid)
        return patients_to_execlude,patients_to_review,patients_passed
    
    
    

            
        
   
class ReadPatientImagingData:
    """This class contains functions that read the patient directory.It collects the patients related data such as the ct_image, masks, roi names, pixel spacing.
    
    """
    
    @staticmethod
    def load_patient_images(pid,adict,configfile='codesconfig_breast.json'):
        execlude='EXECLUDE'
        br=patientImaging(configfile)#at this stage it is the breast cancer dataset, can be changed as required.
        loading_notes=[]
        thect,getspacing,loading_notes=br.load_ct_nifti_2_numpyarray(adict,loading_notes)
        #print(adict)
        recommendation, codes= br.recommendation(loading_notes)
        if recommendation ==execlude:#if not execlude, go to next step
            print(loading_notes)
            br.savepatientnotes(pid,'loading_notes',loading_notes)
            return {}#empty dict
        
        list_of_masks,name_of_masks,roi_masks,loading_notes=br.load_nifti_masks(adict,loading_notes)
        recommendation, codes= br.recommendation(loading_notes)
        if recommendation ==execlude:#if not execlude, go to next step
            br.savepatientnotes(pid,'loading_notes',loading_notes)
            return {}#empty dict
        
        if 'RTDOSE' not in br.codes['required_modalities_for_patient']:
            StudyDate=adict['StudyDate']
            StructureSetDate=adict['StructureSetDate']
            patdict = {"ct_image": thect,
               "roi_names":name_of_masks,
               "roi_masks":roi_masks,
              "PixelSpacing":getspacing, 'StudyDate':StudyDate,
              "StructureSetDate": str(StructureSetDate)}
            patdict['version']=br.codes['version']
            return patdict
        
        
        doseGrids,loading_notes=br.load_doses_2_numpyarray(adict,loading_notes)
        recommendation, codes= br.recommendation(loading_notes)
        if recommendation ==execlude:#if not execlude, go to next step
            br.savepatientnotes(pid,'loading_notes',loading_notes)
            return {}#empty dict
        
        final_dosegrid,maxs,loading_notes=br.select_and_combine_dosegrids(doseGrids,loading_notes)
        recommendation, codes= br.recommendation(loading_notes)
        br.savepatientnotes(pid,'loading_notes',loading_notes)
        if recommendation ==execlude:#if not execlude, go to next step
            return {}#empty dict
        
        StudyDate=adict['StudyDate']
        StructureSetDate=adict['StructureSetDate']
        patdict = {"ct_image": thect, 
           "dose_data": final_dosegrid,
           "roi_names":name_of_masks,
           "roi_masks":roi_masks,
          "PixelSpacing":getspacing, 'StudyDate':StudyDate,
          "StructureSetDate": str(StructureSetDate)}
        
        patdict['version']=br.codes['version']
        return patdict
    
    
class ROIP:
    """A class to process the patient's organs at risk (OARs) and target volumes (TV)
    
    """
    
    def __init__(self,ptype='breast'):
        """Class intializer.
        
        """
        self.execlude=False
        self.ptype=ptype
        pass
    
    
    def load_data_from_file(self,patientsnotesdirectory,patientdirectory,pid):
        """A function that loads patients CT and masks from the directory.
        
        Parameters
        ----------
        patientsnotesdirectory : str 
            Patient notes directory
            
        patientdirectory: str
            Patient data directory
            
        pid: int
            Patient id
            

        """
        try:
            self.patientsnotesdirectory=patientsnotesdirectory#the link to the patients notes directory
            self.patientdirectory=patientdirectory+str(pid)# the link to the patient directory which contains all the files
            self.pid=pid
            filepath=f'{self.patientsnotesdirectory}{str(pid)}.json'#each patient should have a file that summarizes what happened in the data collection process.
            f = open(filepath,)
            file=json.load(f)
            #an attribute that shows if the patient data were collected successfully.
            patientimagingfilesready = file['patientimagingfilesready'] if 'patientimagingfilesready' in file else False
            if not patientimagingfilesready:
                print(f" {self.pid}: Patient cannot be used. Imaging files not ready")
                self.execlude=True
                return
            #if reading from files, the patient notes would contain a key list_of_values, which helps in determining each patient details.
            #this includes the patient ct directory, masks, etcs
            pdcp=patientImaging()
            adict=file['list_of_values']
            #load the nifti file as numpy array
            ct_image,getspacing,notes=pdcp.load_ct_nifti_2_numpyarray(adict,[])
            recommendation,codes=pdcp.recommendation(notes)
            execlude="EXECLUDE"
            if recommendation==execlude:
                print(f'{str(self.pid)}: patient cannot be used in the study. ERROR in collecting ct nifti')
                self.execlude=True
                return
            #load the nifti masks.
            list_of_masks,name_of_masks,roi_masks,notes=pdcp.load_nifti_masks(adict,notes)
            recommendation, codes= pdcp.recommendation(notes)
            if recommendation ==execlude:
                print(f'{str(self.pid)} cannot be used in the study. ERROR in collecting nifti masks')
                self.execlude=True
                return
    
            #Since the CT and the masks were saved using simpleITK, and will be loaded through sitk, I do not see any reason for handling the sizes
            # Resize the CT image and the masks using the pixel spacing parameter
            # Dividing the CT image dimensions by their respective pixel spacing 
            # ratio will standandise all CT images to a pixel spacing of 1 
            # make sure to handle such case: in sitk x axis is z direction, in pixel spacing x is x
            #sitk reads the imagefrom array different to shape. z will be the first
            #sitk_pixel_spacing_tag=[getspacing[2],getspacing[0],getspacing[1]]
            #not used so far
            #new_size = tuple([int(ct_image.shape[i]/sitk_pixel_spacing_tag[i]) for i in range(len(sitk_pixel_spacing_tag))])
            #self.new_size=new_size
            #self.PixelSpacing=getspacing
            
            sn=list(set(name_of_masks))
            if len(sn)<len(name_of_masks):
                print(f"{str(self.pid)}: Patient have multiple rois with the same name. Patient must be revised.")
            
            self.ct_image = ct_image
            self.roi_masks = roi_masks# as noticed, list_of_masks was not used as it is already used in roi_masks.
            self.roi_names = name_of_masks
        except Exception as e:
            print(e)
            print(f'{str(self.pid)}: patient cannot be used in the study')
            self.execlude=True
            
        
        
    def generate_slice_roi(self,roiname,maskname,dim,thenumber):
        """A function used to generate the central slice of an OAR or TV.
        
        Parameters
        ------------
        roiname: str
            name of the OAR or TV as it was in the plan
        
        maskname: str
            represents the key of the mask in the dictionary that contains the patients masks.
            
        dim: int
            The dimension on which the slice to to be created (x,y,z).
                            
        thenumber: int
            The number of the roi in the list of rois associated with the patient plan. the main reason behind using this is to avoid overriding some structures with duplicates being obtained.
    
        Returns
        -----------
        deta: str
            path to the generated numpy array that contains the positional features.
            
        ida: str
            path to the generated slice
        """
        if self.execlude:
            return
        try:
            arr = self.roi_masks[maskname]#roi masks is a dict of masks, with the first index in roi_names list being the first mask and so on.
            # Check if ROI mask exists
            if len(arr) == 0:
                return "empty mask","empty mask"
            volume=arr.ravel().sum()#volume of the mask.
            
            centroid=ndimage.measurements.center_of_mass(arr)#centroid of the mask
            centroid_x=centroid[0]
            centroid_y=centroid[1]
            centroid_z=centroid[2]
            #magnitude
            mag=math.sqrt(centroid_x*centroid_x +centroid_y*centroid_y+centroid_z*centroid_z)
            #angles cosine direction
            cos_x=centroid_x/mag
            cos_y=centroid_y/mag
            cos_z=centroid_z/mag
            
            # set the dimension length (usually zero which is the depth)
            z = arr.shape[dim]
            # Set max_slice and index to -1 initially
            max_slice = -1
            index = -1
            image=None
            # Find the index at which the central slice occurs for this image
            for i in range(z): 
                if dim==0:
                    slic = arr[i, :, :]
                if dim==1:
                    slic = arr[:, i, :]
                if dim==2:
                    slic = arr[:, :, i]
                #slic = list(slic.ravel())
                # Enumerate the number of 1's in this slice
                a = slic.ravel().sum()
                # If new maximum found, assign 'max' to it and track its index
                if a > max_slice:
                    max_slice = a
                    index = i
            #After selecting the index, lay the mask on the ct image to get biomarkers values.
            try:
                if dim==0:
                    image = np.multiply(self.roi_masks[maskname][index, :, :], self.ct_image[index, :, :])
                if dim==1:
                    image = np.multiply(self.roi_masks[maskname][:, index, :], self.ct_image[:, index, :])
                if dim==2:
                    image = np.multiply(self.roi_masks[maskname][:, :, index], self.ct_image[:, :, index])
                
            except Exception as e:
                print(e)
                f = open(f'{self.pid}_{roiname}.txt', "w")
                f.write(e)
                f.close()
                print(f'Masking multipication error, could not generate masked image for {self.patient_id}_{roiname}!!')
                return "exception","exception"

            
            #prepare to save data.
            e=['x','y','z']
            dimstr=e[dim]
            #create an array to save positional features
            details=np.array([centroid_x,centroid_y,centroid_z,mag,cos_x,cos_y,cos_z,volume,index])
            #create directories
            if not os.path.exists(f'{self.patientdirectory}/roidetails_{dimstr}/'):# a directory that save all the patient's details
                os.mkdir(f'{self.patientdirectory}/roidetails_{dimstr}/')
            if not os.path.exists(f'{self.patientdirectory}/roiimages_{dimstr}/'):# a directory that save all the patient's details
                os.mkdir(f'{self.patientdirectory}/roiimages_{dimstr}/')    
            
            deta=f'{self.patientdirectory}/roidetails_{dimstr}/{self.pid}--{thenumber}--{roiname}--{dimstr}--details.npy'
            np.save(deta,details)
            ida=f'{self.patientdirectory}/roiimages_{dimstr}/{self.pid}--{thenumber}--{roiname}--{dimstr}--images.npy'
            np.save(ida,image)
            return deta,ida
        except Exception as e:
            print("Exception with patient: "+str(self.pid)+ " roi: "+roiname)
            print(e)
            return "exception","exception"
        

    def generate_slices_patient_rois(self,dim):  
        """A function used to generate 2d images of slices with the highest number of contoured pixels, for all the ROI structures.
        Function load_data_from file should be executed before this function.
        This function can be used to review some patients OARs and TV
        
        Parameters
        ------------
        dim: int
            the targeted dimension (can be 0,1, or 2)
    

        
        """
        if self.execlude:
            return
        # Iterate through all ROI structures
        e=['x','y','z']
        dimstr=e[dim]
        numbers=[]
        details_location=[]
        ada_location=[]
        counter=0
        print(f'Generating 2d slices for patient {self.pid}. number of images expected {len(self.roi_names)}')
        for idx,roi in enumerate(self.roi_names):
            counter=counter+1  
            numbers.append(counter)#add the numbers
            maskname = 'mask' + str(idx)
            deta,ada=self.generate_slice_roi(roi,maskname,dim,counter)
            details_location.append(deta)
            ada_location.append(ada)
        print(f'Successfully generated 2d slices for patient {self.pid}')
        

                
        
    @staticmethod
    def load_patient_central_slices(PatId,notesdir='../../Breast_dosimetry_data/patientnotes/',dim='x'):
        """This function is used to prepare a dataframe that contains the patients rois and its corresponding images locations.
        
        
        Parameters
        ------------
        PatId: int
            patient id
            
        notesdir: str
            path to patients directory
            
        dim: str
            dimension (x,y, or z)
        
        Returns
        ---------
        df: pandas dataframe
            pandas dataframe that contains the patient ROIs and corresponding images/details paths.
        
        """
        try:
            filepath=f'{notesdir}{str(PatId)}.json'#each patient should have a file that summarizes what happened in the data collection process.
            f = open(filepath,)
            file=json.load(f)
        except Exception as e:
            print(e)
            print(f'{str(PatId)} has no notes in the specified directory.')
            df=pd.DataFrame()
            return df
            
        #an attribute that shows if the patient data were collected successfully.
        patientimagingfilesready = file['patientimagingfilesready'] if 'patientimagingfilesready' in file else False
        if not patientimagingfilesready:
            print(f'{str(PatId)} imaging data cannot be used.')
            df=pd.DataFrame()
            return df
        adict=file['list_of_values']
        patientdir=adict['thedir']
        imagesdir=f'{patientdir}roiimages_{str(dim)}/'
        detailsdir=f'{patientdir}roidetails_{str(dim)}/'
        if not os.path.exists(imagesdir):
            print('imaging directory does not exist.')
            df=pd.DataFrame()
            return df
        images=os.listdir(imagesdir)#all the generated slices
        details=os.listdir(detailsdir)      #all the generated details
        
        images_idx=[image.split("--")[1] for image in images]#get the number of each image
        images_idx=[int(e) for e in images_idx]
        #sort the two lists images and details based on sorted images_idx
        images_sorted=[x for _, x in sorted(zip(images_idx, images))]
        details_sorted=[x for _, x in sorted(zip(images_idx, details))]
        
        
        roi_names_sorted=[image.split("--")[2] for image in images_sorted]# get the roi names
        idx_sorted=[image.split("--")[1] for image in images_sorted]#get the index of each file.
        images_sorted=[imagesdir+image for image in images_sorted]#prepare the path of the image
        details_sorted=[detailsdir+detail for detail in details_sorted]#prepare the path of the details file.
        
        
        PatId=[int(PatId)]*len(roi_names_sorted)
        di={'pat_id1':PatId,'roi_name':roi_names_sorted,'roi_index':idx_sorted,'image_path':images_sorted,'detail_path':details_sorted}
        df=pd.DataFrame(di)
        return df
        
        

    @staticmethod
    def load_central_slices(notesdir='../../Breast_dosimetry_data/patientnotes/',pids=[],dim='x',categorize=True, datatype='breast'):
        """ This is a function that generates the patients list of OARs and TV.
        
        Parameters
        ------------
                
        notesdir: str
            path to patients notes directory
            
        pids: list
            if a list of patients is needed, not all. Otherwise keep empty.
            
        dim: str
            dimension (x,y, or z)
        
        categorize: bool
            a boolean function to categorize the roi names.
            
        Returns
        ---------
        df: pandas dataframe
            pandas dataframe that contains the patient ROIs and corresponding images/details paths.
            
        succ_patients: list
            A list of successfully loaded patients
            
        exec_patients: list
            A list of excluded patients.
            
        not_found:list
            patients whose notes were not found.
            
        
        """
        if categorize:
            if datatype=='breast':
                print("PLEASE NOTE THAT THE PATH TO THE BREAST CATEGORIZATION FUNCTION SHOULD BE PROVIDED.")
            else:
                print(f"THE LOGIC TO HANDLE {datatype} HAS NOT YET BEEN IMPLEMENTED.")
                return
        dataset=pd.DataFrame()#dataframe that will save all the patients details
        succ_patients=[]
        exec_patients=[]
        not_found=[]
        for PatId in pids:
            filename=notesdir+str(PatId) + '.json'
            if os.path.exists(filename):
                df=ROIP.load_patient_central_slices(PatId,notesdir,dim)
                if df.shape[0]>0:
                    if categorize:
                        sys.path.append('../../BreastCancerDataset/code/')
                        from BreastCancer import CatPat
                        #'patcategories','patprobabilities',
                        z=CatPat(PatId)
                        z.CategorizePatientVar(df['roi_name'].tolist())
                        df['roi_category']=z.patcategories
                        df['roi_probablity']=z.patprobabilities
                    dataset=pd.concat([dataset,df])
                    succ_patients.append(PatId)
                else:
                    exec_patients.append(PatId)
            else:
                not_found.append(PatId)
        return dataset,succ_patients,exec_patients,not_found
                
    
    
    
        
class DVH:
    """A class that computes the DVH features for each patient imaging files.
    
    """
    
    def __init__(self,pid):
        """Used to generate the DVH values for each category.
        

        Parameters
        ----------
        pid : int
            patient id


        """
        self.pid=pid
        self.flag_roi_name_appr_mask_not_found=False
        self.flag_note=""
        self.flag_volume_value_zero=False
        
        
    
    def compute_dvh_data(self,b,prescribed_dose):
        """This function takes a dictionary that contains the categories, dose data,
        masks, and generates the dvh values for each approved category in the patient records

        Parameters
        ----------
        b : Dict
            contains all the imaging details of the patient, and the mapped categories of the ROI names.
            
        prescribed_dose : float
            prescribed dose from clinical data



        """
        # Dose features values. I assume this is VGy
        doseLimit = 70.001
        binSize = 0.5
        dL=np.arange(binSize,doseLimit,binSize).tolist()#adding the 0.001 to include the 70 as a value
        vgy_header = ['VGy_'+str(i) for i in dL]
        
        #Dose features for V%x
        perc_limit = 130.0 #max value
        binSize = 0.5
        dpL = np.arange(binSize,perc_limit+0.0001,binSize).tolist()
        vp_header=['V%_'+str(i) for i in dpL]
        
        #voxel size for volume calculation
        #voxel_size=np.product(b['PixelSpacing'].tolist())
        perc_diff = 0.5
        dccvalues=np.arange(perc_diff,100.0001,perc_diff).tolist()
        d_header= ['D'+str(i) for i in dccvalues]
        
        complete_header=['patient_id','roi_name','volume','mean_dose','median_dose','min_dose','max_dose']
        complete_header.extend(vgy_header)#extend here, other places append
        if prescribed_dose is not None:
            complete_header.extend(vp_header)
        complete_header.extend(d_header)
        
        pat_dvh_list=[]
        flatten_dosegrid=b['dose_data'].flatten()#flatten the dose grid
        for i in b['roi_names']:#for each roi name
            theindex=b['roi_names'].index(i)
            arow=[]
            arow.append(self.pid)#add pid
            arow.append(i)#add the roi
            #to load the correct mask, will need the index in roi_names get the mask with maskINDEX
            mask=b['roi_masks']['mask'+str(theindex)]#get the mask
            #if the mask has a shape different to the dosegrid, we report this 
            #handling [] in masks.
            if isinstance(mask,np.ndarray) ==False:
                if isinstance(mask,list) ==True:
                    if len(mask)==0:
                        mask=np.array(mask)
                
            if not b['dose_data'].shape == mask.shape:
                self.flag_roi_name_appr_mask_not_found=True
                self.flag_note=self.flag_note + str(self.pid) +" dose data and mask have different shapes: ROI name ( "+ b['roi_names'][theindex] + "),approved category ( "+i +"), dose data "+ str(b['dose_data'].shape)+ ",mask shape: "+ str(mask.shape)+ ";"
            else:                
                flatten_mask=mask.flatten()#flatten the mask 1
                res=flatten_dosegrid[flatten_mask>0] 
                if res.size !=0:
                    arow.append(round(np.sum(flatten_mask),3))#volume * b['info']['pixelspacing'].prod()
                    arow.append(round(np.mean(res),3))#mean
                    arow.append(round(np.median(res),3))#median
                    arow.append(round(np.min(res),3))#min
                    arow.append(round(np.max(res),3))#max
                    #add VGy_binsize, VGy_binsize+binsize, Vgy_binsize_binsize+binsize etc  
                    for dosevalue in dL:
                        res_value_after_threshold=res[res>=dosevalue]#volume that received a dose value equal or greate to dose value (up to 70 Gy)
                        per_volume_m_dosevalue=(res_value_after_threshold.shape[0]/res.shape[0])*100
                        arow.append(round(per_volume_m_dosevalue,3))
                    
                    if prescribed_dose is not None:
                        #Vx%
                        for value in dpL:
                            #the prescribed dose is given as mG i think, 4240. Hence we should divide by 100 to get values similar to values in dose grid
                            dose_per=(value/100)*(prescribed_dose/100) #0.5 * prescribed_dose = dose value 
                            res_value_after_threshold=res[res>=dose_per]
                            per_volume_m_dosevalue=(res_value_after_threshold.shape[0]/res.shape[0])*100
                            arow.append(round(per_volume_m_dosevalue,3))
                    #D features dose received by x cc of the volume.
                    res.sort()
                    n=len(res)
                    for k in dccvalues:
                        #we need to make sure that the index is not equal to the len of the list, otherwise index error will be issued. 
                        ic=math.ceil((k/100)*n)
                        if ic !=n:# to make sure the length of the dataset will not be selected
                            arow.append(res[ic])
                        else:
                            #equal to the last index in the list
                            arow.append(res[-1])
                else:
                    #there could be very rare cases where when you apply the mask
                    #all the values in the volume would be zero
                    #To avoid that, we add 4 values of zero that represent mean median,min, and max
                    self.flag_volume_value_zero=True
                    self.flag_note=self.flag_note + str(self.pid) +" volume has zero dose values only: ROI name ( "+ b['roi_names'][theindex] + "),approved category ( "+i +"), dose data "+ str(b['dose_data'].shape)+ ",mask shape: "+ str(mask.shape)+ ";"
                    arow.append(0)#volume
                    arow.append(0)#mean
                    arow.append(0)#median
                    arow.append(0)#min
                    arow.append(0)#max
                    for dosevalue in dL:
                       arow.append(0)
                    if prescribed_dose is not None:
                        for value in dpL:
                            arow.append(0)
                    for d in dccvalues:
                        arow.append(0)
                #add to the list
                pat_dvh_list.append(arow)
        #create the dataframe
        dvh= pd.DataFrame(pat_dvh_list,columns=complete_header)
            
        self.dvh_dataframe=dvh
        return dvh
    
    @staticmethod
    def generatefigure(fi,df_pro,title,xaxistitle,yaxistitle):
        import plotly.graph_objs as go
        
        """A function that adds the Dose Volume Histogram (DVH) based on a list of params.
        
        Parameters
        ----------
        fi : str
            type of the dosimetry features (Vgy_, ...)
            
        df_pro: pandas dataframe
            dataframe of the patient ROIs, index should be the ROI names.
            
        title: str
            title of the figure
            
        xaxistitle: str
            title of the figure
            
        yaxistitle: str
            title of the figure
        
        Returns
        -------
        fig: plotly figure
            the generated figure
            
        """                    
        filter_col = [col for col in df_pro if col.startswith(fi) and len(col)<10]
        
        df=df_pro[filter_col]#select the columns V%_
        df=df.transpose()
        columns=df.columns.tolist()
        trace = []
        df[fi] = df.index#set the index as a column
        df=df.reset_index(drop=True)# delete the index and reset it
        df[fi] = df[fi].str[len(fi):]#remove the 
        df[fi] = pd.to_numeric(df[fi])#change to numeric
        for column in columns:
            trace.append(go.Scatter(x=df[fi], y=df[column], name=column, mode='lines',
                                    marker={'size': 8, "opacity": 0.8, "line": {'width': 0.5}}, ))
        fig= {"data": trace,
              "layout": go.Layout(
                  paper_bgcolor='rgb(255,255,255)',
                  plot_bgcolor='rgb(255,255,255)',
                  title=title,
                  legend={'bordercolor':'black','borderwidth':2},
                  colorway=['#030202','#FF0000','#FF8C00','#008000','#FF1493','#FF00FF','#fdae61', '#abd9e9', '#2c7bb6'],
                  yaxis={"title": yaxistitle,"showgrid": True,'gridcolor':'Grey',"showline":True,'linecolor':'black','mirror':True,'linewidth':1, 'tickmode':'linear','dtick':5},
                  xaxis={"title": xaxistitle,"showgrid": True,'gridcolor':'Grey',"showline":True,'linecolor':'black','mirror':True,'linewidth':1, 'tickmode':'linear','dtick':5}
                  )}
        return fig
                
        
