# -*- coding: utf-8 -*-
"""
Plot the DVHs
"""
import json
import sys,os
import plotly.io as pio
import pandas as pd

sys.path.insert(0, os.path.abspath('../../PDCP/code/'))
from PDCP import DVH

configfile='codesconfig_HN.json'
with open(configfile, "r") as read_file:
    conf = json.load(read_file)

datadirectory=conf['datadirectory']
with open(configfile, "r") as read_file:
    conf = json.load(read_file)

for pid in spatients:
    dosimetrydir=f'{datadirectory}{str(pid)}/dosimetrydata/'
    dosefile=f'{dosimetrydir}/{str(pid)}_.csv'
    df_pro=pd.read_csv(dosefile)
    df_pro.index=df_pro['roi_name']
    fi='VGy_'
    title="VGy"
    xaxistitle="Dose [Gy]"
    yaxistitle='Volume'
    fig=None
    fig=DVH.generatefigure(fi,df_pro,title,xaxistitle,yaxistitle)
    pio.write_image(fig,f'{str(pid)}.png',format='png')