# -*- coding: utf-8 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

import os, sys
import numpy as np
import pandas
import pandas.io.sql as sql
import sqlite3 as sqlite

sys.path[0:0] = ['..',]

from utilities.opcVarHandling import opcVar


def getDataFromDB(dbUrl):

    conn = sqlite.connect(dbUrl)





    Query = """SELECT Timestamp as datetime,
                    `North_K` as North_K_in,
                    `East_N` as East_N_in,
                    `East_NR` as East_NR_in,
                    `East_D` as East_D_in,
                    `North_B` as North_B_in,
                    `North_G` as North_G_in,
                    `West_E` as West_E_in,
                    `West_H` as West_H_in
                  FROM `EstimatedInflow`
                  WHERE Timestamp BETWEEN "2013/09/08 00:00" AND "2013/09/10 00:00"
                  ORDER BY datetime ASC"""



    df = sql.read_sql(Query, conn, index_col = 'datetime')


    if pandas.version.version in ['0.8.1']:
        df.index = [pandas.datetools.to_datetime(di)\
                    for di in df.index]
    else:
        tz = pandas.datetools.dateutil.tz
        df.index = [pandas.datetools.to_datetime(di).replace(tzinfo=tz.tzlocal())\
                    for di in df.index]


    df['North_in'] = df['North_B_in'] + df['North_G_in'] + df['North_K_in']
    df['East_in'] = df['East_N_in'] + df['East_NR_in'] + df['East_D_in']
    df['West_in'] = df['West_E_in'] + df['West_H_in']
    
    df['South:Qout']=0.0015+0*df['North_in']

    df['North:Qout']=0*df['North_in']
    df['East:Qout']=0*df['North_in']
    df['West:Qout']=0*df['North_in']

    df['South_in']=df['South:Qout']



    df[df<0]=0
    df = df*600 # [m3/s] --> [m3/10min]
    df = df.resample('10min',how='mean',label='right',closed='right')

    conn.close()







    return df





def Create_Dict_of_OPCVar(dbUrl = 'data\Infoworks.sqlite'):

    SYS_DummyVariables = ["North:Lb",
                         "East:Lb",
                         "West:Lb"
                         ]

    OUT_DummyVariables = []

    STATE_DummyVariables = []

    SYS_Variables = ["North_in",
                 "West_in",
                 "East_in",
                 "South_in",
                 "North:Qout",
                 "West:Qout",
                 "East:Qout",
                 "South:Qout",
                ]

    OUT_Variables = []

    STATE_Variables = []


    # Query the data from the Database and build a dataframe object.
    df = getDataFromDB(dbUrl=dbUrl)

    OUT_opcVarsDict = dict()
    SYS_opcVarsDict = dict()
    STATE_opcVarsDict = dict()

    # Initializing the OPC Variable dictionary.
    for valeur in OUT_DummyVariables+OUT_Variables:
        OUT_opcVarsDict[valeur]=opcVar(valeur,None,'Good',"2000-01-01 00:00")
    for valeur in SYS_DummyVariables+SYS_Variables:
        SYS_opcVarsDict[valeur]=opcVar(valeur,np.NAN,'Good',"2000-01-01 00:00")
    for valeur in STATE_DummyVariables+STATE_Variables:
        STATE_opcVarsDict[valeur]=opcVar(valeur,None,'Good',"2000-01-01 00:00")


    # Loop over the data samples to update the OPC variables
    for ind,ser in df.iterrows():
        tz = pandas.datetools.dateutil.tz
        if ind.tzinfo != None:
            opcDT = ind.to_pydatetime().astimezone(tz.tzutc()).replace(tzinfo=None).isoformat(' ')
        else:
            opcDT = ind.to_pydatetime().replace(tzinfo=tz.tzlocal()).astimezone(tz.tzutc()).replace(tzinfo=None).isoformat(' ')

        for valeur in OUT_DummyVariables+SYS_DummyVariables+STATE_DummyVariables:
            varValue = np.NAN
            if valeur == " XXX.S0_tUpdate": # This variable needs a usable value for some of the algo implementations
                varValue = 600 # Use the standard value (10min).

            if valeur[-3:] == ":Lb":
                varValue=0

            if valeur[-4:] == ":Lov":
                varValue=0

            if valeur in OUT_DummyVariables:
                OUT_opcVarsDict[valeur].setValue(valeur,varValue,'Good',opcDT)
            if valeur in SYS_DummyVariables:
                SYS_opcVarsDict[valeur].setValue(valeur,varValue,'Good',opcDT)
            if valeur in STATE_DummyVariables:
                STATE_opcVarsDict[valeur].setValue(valeur,varValue,'Good',opcDT)




        for valeur in OUT_Variables+SYS_Variables+STATE_Variables:
            if not(np.isnan(ser[valeur])):
                Qual='Good'
            else:
                Qual='Bad'
                ser[valeur]=0;Qual='Good'

            NK=0

            if valeur in OUT_Variables:
                OUT_opcVarsDict[valeur].setValue(valeur,10**(-NK)*ser[valeur],Qual,opcDT) # Changed to avoid numpy array data in the opc value.
            elif valeur in SYS_Variables:
                SYS_opcVarsDict[valeur].setValue(valeur,10**(-NK)*ser[valeur],Qual,opcDT) # Changed to avoid numpy array data in the opc value.




        yield OUT_opcVarsDict, SYS_opcVarsDict, STATE_opcVarsDict

