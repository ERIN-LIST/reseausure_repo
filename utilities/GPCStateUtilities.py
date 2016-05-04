# -*- coding: utf-8 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

import re
from collections import defaultdict

from Control.GPCVariablesConfig import GPC_Stations


def getLifeVars(opcvar):
    """Returns the gpc internal variable names as a list
    - The parameter opcvar need to be a dictionary of opcVars."""
    reLifeFilter = re.compile(".*(LifeH|LifeM)$")
    gpcLifeVars = filter(reLifeFilter.match, opcvar.keys())
    return gpcLifeVars


def buildLifeDiff(opcvar,varList=[]):
    d = defaultdict(int)
    if varList == []:
        varList = opcvar.keys()
    for ki in varList:
        vi = opcvar[ki]
        if ki == vi.name:
            sti = ki.split(':.')[0]
        else:
            sti = ki.split(':')[0]
        if ki.endswith('Stunde') or ki.endswith('LifeH'): mult = 60
        elif ki.endswith('Minute') or ki.endswith('LifeM'): mult = 1
        else: raise ValueError('Unhandled counter type')
        if vi.getDiff() == None:
            diff = None
        else:
            diff = vi.getDiff().Diff[0]
            if diff < 0 and mult == 60: diff += 24
            elif diff < 0 and mult == 1: diff += 60
        try:
            d[sti] += diff * mult
        except TypeError:
            d[sti] = None
    return d

def buildLifeCounter(opcvar,varList=[]):
    d = defaultdict(int)
    if varList == []:
        varList = opcvar.keys()
    for ki in varList:
        vi = opcvar[ki]
        if ki == vi.name:
            sti = ki.split(':.')[0]
        else:
            sti = ki.split(':')[0]
        if ki.endswith('Stunde') or ki.endswith('LifeH'): mult = 60
        elif ki.endswith('Minute') or ki.endswith('LifeM'): mult = 1
        else: raise ValueError('Unhandled counter type')
        try:
            if vi.quality == 'Good':
                d[sti] += vi.value * mult
            else: d[sti] = None
        except TypeError:
            d[sti] = None
    return d

def getSysGPCState(stateVars):
    """
    Returns the system GPC State of each configured station as a dictionary
      station: one of {'offline','maintenance','controllable','controlled'}
    - The parameter stateVars need to be a dictionary of opcVars with the system state variables.
    """
    gpcLifeVars = getLifeVars(stateVars)
    zLifeC = buildLifeCounter(stateVars,gpcLifeVars)
    zLife = buildLifeDiff(stateVars,gpcLifeVars)
    Sys_zLife = {}
    for sti in zLife:
        if zLifeC[sti] == None:
            Sys_zLife[sti] = False
        elif zLife[sti] > 0 or zLife[sti] == None:
            # zLife[sti] == None should only occure after GPC initialization or after a reset.
            Sys_zLife[sti] = True
        else:
            Sys_zLife[sti] = False
    SysGPCState = {}
    gpcStates = {-1:'offline',0:'maintenance',1:'controllable',2:'controlled'}
    for sti in GPC_Stations.values():
        viState = None
        if Sys_zLife.get(sti,None):
            vi = ':'.join((sti,"GPCState"))
            viState = stateVars.get(vi,0) # Default=0 means station is life but has no GPCState variable.
            if viState != 0:
                viState = viState.value
        SysGPCState[sti] = gpcStates.get(viState,gpcStates[-1]) # Default=-1 means station is not life.
    return SysGPCState
