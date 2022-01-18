# -*- coding: utf-8 -*-
"""
a script to check patients who had error in the data collection process.

@author: 60183647
"""


#This was used to select the ids with errors while returing the images summaries.

import os
pids=[]
for file in os.listdir('../imagesummaries/'):
    if 'ERROR' in file:
        pids.append(file.split("_")[0])

pids=[int(p) for p in pids]