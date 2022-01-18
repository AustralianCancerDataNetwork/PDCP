Example
=================

This folder contains an example used to create and process a breast patients cohort, where four modalities are expected:

- CT
- RTSTRUCT
- RTDOSE
-RTPLAN


Each python module with a keyword _step_ in code represents a step for generating the required cohort. 

The purpose of this example was to show the possibility of including interceptors along the data processing pipeline. 
Interceptors were defined as independent scripts used to process the data dependent on the task,
e.g. a breast cohort at a data centre might contain RTDOSES that are rejected or not used in treatment.
An interceptor was created to remove such records from each patient imaging summaries.