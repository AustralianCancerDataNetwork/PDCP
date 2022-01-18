# -*- coding: utf-8 -*-
"""
Example for modifying values in the notes .


"""
import os
import json
adir='D:/AH/pdcptest_oct21/patientnotes/'

for file in os.listdir(adir):
    filename=f'{adir}{file}'
    with open(filename) as json_file:
        data = json.load(json_file)
    if 'list_of_values' in data:
        for i in ['thedir', 'ct_directory', 'rtdoses_directory', 'rtdoses_directory_nifti', 'rtstruct_directory', 'masks_directory', 'nifti_directory']:
            data['list_of_values'][i]=data['list_of_values'][i].replace("../","D:/AH/pdcptest_oct21/")
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)
    

