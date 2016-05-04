# -*- coding: utf-8 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """


#import os
import sys
import numpy as np
import logging
import logging.handlers
from datetime import timedelta


sys.path[0:0] = ['../ReadWriteDataTest',]
sys.path[0:0] = ['AlgSysStatefollowing\SMC',]
sys.path[0:0] = ['..',]





import Control.MPCAlgos as MPCAlgos
from handleConfig import readGPCConfig
from Create_Dict_of_OPCVar import Create_Dict_of_OPCVar

dbFile = 'data\IN_DB.sqlite'
iterator = Create_Dict_of_OPCVar(dbUrl=dbFile)
OutVarsDB,SysVarsDB,StateVarsDB = iterator.next()


ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logging.getLogger("Control.MPCAlgos").addHandler(ch)
logging.getLogger("Control.MPCAlgos").setLevel(logging.DEBUG)
GPCAlglogRF = logging.handlers.RotatingFileHandler(
                filename='GPCAlgo.log', mode='a',
                backupCount=10, maxBytes=1000000 )
GPCAlglogRF.setLevel(logging.DEBUG)
logging.getLogger("Control.MPCAlgos").addHandler(GPCAlglogRF)





#algo=MPCAlgos.Opti()

GPCConf = readGPCConfig('../ReadWriteDataTest/GPCAlgoConf.ini')
config = dict(zip(("Tree","Valid"),GPCConf))
MPCmode = config["Tree"]["MPC"]["mode"]
MPCmode = "Opti"
algo = MPCAlgos.__dict__[MPCmode](config['Tree']["MPC_"+MPCmode],
                                        sysVars = SysVarsDB,
                                        stateVars = StateVarsDB,
                                        )




OutVarsName = [  "North:Qout",
             "East:Qout",
             "West:Qout",
             "South:Qout"]

VOL = np.zeros((2,algo.NbRUB))
IN = np.zeros((1,algo.NbRUB))
OUT = np.zeros((1,algo.NbRUB))
OV = np.zeros((1,algo.NbRUB))
Qwwtp = np.array([np.nan, np.nan])


OUT_last2hours = np.zeros((11,algo.NbRUB))










Nloop = 0

for OutVarsDB,SysVarsDB,StateVarsDB in Create_Dict_of_OPCVar(dbUrl=dbFile):
    Nloop += 1
    print SysVarsDB["North_in"].dtLoc

    if Nloop < 8:
        OUT_last2hours = np.roll(OUT_last2hours, -1, axis=0)
        OUT_last2hours [-1,:]  =  np.array([SysVarsDB[ki].value/algo.unitConv['l/s'] for ki in OutVarsName])

        OUT = np.vstack((OUT, OUT_last2hours [-1,:] ))



        algo.Out_Real = OUT_last2hours [-1,:]




        VOL = np.vstack((VOL,np.zeros((1,algo.NbRUB))))
        IN = np.vstack((IN,np.zeros((1,algo.NbRUB))))
        OV = np.vstack((OV,np.zeros((1,algo.NbRUB))))
        Qwwtp = np.hstack((Qwwtp,np.nan))
        #Y.append attention c'est Y (p+1)


    else:


        print Nloop




        OPCDT = SysVarsDB.items()[0][1].dt + timedelta(seconds = 600)
        for idx, ti in enumerate(algo.ConfigTanks):
            vi = algo.Volumes_Real[idx]
            if vi :
                hVmap = algo._getVMap(ti)
                for hKi in hVmap:
                    hvm = np.array(zip(*hVmap[hKi]))
                    hi = np.interp(vi,hvm[1],hvm[0])
                    VarName = ti + ':' + hKi
                    SysVarsDB[VarName].setValue(VarName,hi,'Good',OPCDT.isoformat())
                    if hi==hvm[0][-1]:
                        vi -=hvm[1][-1]
                    else :
                        break
            else :
                hi = 0
            # TO DO : set also the overflow variables Lov
            outi = algo.Out_Real[idx] *6
            VarName = ti + ':Qout'
            SysVarsDB[VarName].setValue(VarName,outi,'Good',OPCDT.isoformat())



#        [OUT_command, IN_real, Vol_real, Ov_real, Y] = algo.run(SysVarsDB,OUT_last2hours,Nloop)
#        [OUT_command, IN_real, Vol_real, Ov_real, Y] = algo.run(SysVarsDB)
        # attention c'est Y (p+1)


        [OutCommDict, Y] = algo.run(SysVarsDB)


#----------Simulation----------------------------------------------------------

        RUB_IN_Real = np.array([SysVarsDB[ki + "_in"].value for ki in algo.ConfigTanks])    # m3/10min


        Ov_Real=np.zeros((algo.NbRUB,1))
        #--- add perturbation to mimic errors inherent in a real system
        algo.Out_Real = algo.OutComm
#            algo.Out_Real = algo.OutComm * (0.9+0.2*np.random.rand(algo.NbRUB,1)) # Out real = Outcomm +/- 10%
        for idx, val in enumerate(algo.ConfigTanks):
            algo.Volumes_Real[idx] += RUB_IN_Real[idx] - algo.Out_Real[idx]

        for k in xrange( algo.NbRUB ):
            if algo.Volumes_Real[k] < 0 :
                algo.Out_Real[k] = float((algo.Volumes_Real[k] + algo.Out_Real[k]))
                algo.Volumes_Real[k] = 0
            if algo.Volumes_Real[k] + Ov_Real[k] > algo.VolMax[k] :
                Ov_Real[k] = float(algo.Volumes_Real[k] - algo.VolMax[k])
                algo.Volumes_Real[k] = algo.VolMax[k]
            if (np.isnan(algo.VolMax[k])) and (algo.Volumes_Real[k] !=0) :
                algo.Out_Real[k] = algo.Out_Real[k] + algo.Volumes_Real[k] # = RUB_IN_Real[k]
                algo.Volumes_Real[k] = 0








#        OPCDT = SysVarsDB.items()[0][1].dt + timedelta(seconds = 600)
#        for idx, ti in enumerate(algo.ConfigTanks):
#            vi = algo.Volumes_Real[idx]
#            if vi :
#                hVmap = algo._getVMap(ti)
#                for hKi in hVmap:
#                    hvm = np.array(zip(*hVmap[hKi]))
#                    hi = np.interp(vi,hvm[1],hvm[0])
#                    VarName = ti + ':' + hKi
#                    SysVarsDB[VarName].setValue(VarName,hi,'Good',OPCDT.isoformat())
#                    if hi==hvm[0][-1]:
#                        vi -=hvm[1][-1]
#                    else :
#                        break
#            else :
#                hi = 0
#------------------------------------------------------------------------------



        OUT_command = algo.Out_Real/algo.unitConv['l/s']
        IN_real = RUB_IN_Real/algo.unitConv['l/s']
        Vol_real = algo.Volumes_Real
        Ov_real = Ov_Real/algo.unitConv['l/s']
        Y = Y/algo.unitConv['l/s']















        OUT_last2hours = np.roll(OUT_last2hours, -1, axis=0)
        OUT_last2hours [-1,:]  =  np.array([OUT_command[idx] for idx, val in enumerate(algo.ConfigTanks)]).flatten()

        OUT = np.vstack((OUT, OUT_last2hours [-1,:] ))

        VOL = np.vstack((VOL,Vol_real.T))
        IN = np.vstack((IN,IN_real))
        OV = np.vstack((OV,Ov_real.T))
        if not np.isnan(Y[0]):
            Qwwtp = np.hstack((Qwwtp,np.array([Y])[0][0]))
        else :
            Qwwtp = np.hstack((Qwwtp,np.array([Y[0]])))






OutMax = np.array([algo.CSOT_cf[x]['Qmax'] for x in algo.ConfigTanks])
OutMax = OutMax*algo.unitConv['l/s']



import pickle

pickle.dump((VOL,IN,OUT,OV,Qwwtp,OutMax/algo.unitConv['l/s'],algo.VolMax,algo.ConfigTanks,algo.Yref/algo.unitConv['l/s'],algo.MaxWWTP/algo.unitConv['l/s']), open( "2013098-9_115_Hp8_49_50_HomogOutlier.p", "wb" ) )

Qwwtp = Qwwtp[:-1]
Qwwtp = Qwwtp.reshape(len(Qwwtp),1)
DummyCol = 0*Qwwtp
VOL=VOL[1:]
ToXL = np.hstack((VOL,DummyCol,IN,DummyCol,OUT,DummyCol,OV,DummyCol,Qwwtp))




OutMax = OutMax/algo.unitConv['l/s']
VolMax = algo.VolMax
Tank = algo.ConfigTanks
Qwwtp_Ref = algo.Yref/algo.unitConv['l/s']
Qwwtp_MAX = algo.MaxWWTP/algo.unitConv['l/s']
VOL=np.delete(VOL,0,axis=0)
OVT=np.delete(OV*0.6,0,axis=0)
INT=np.delete(IN*0.6,0,axis=0)
OUTT=np.delete(OUT*0.6,0,axis=0)
QwwtpT=np.delete(Qwwtp*0.6,0,axis=0)

import matplotlib.pyplot as plt

plt.figure()
for k in xrange(algo.NbRUB):
    if k==0:
        ax1 = plt.subplot(2,3,k+1)
    else:
        plt.subplot(2,3,k+1, sharex=ax1)
    hl11=plt.plot(OUT[:,k], label='Outflow')
    hl12=plt.plot(float(OutMax[k])/VolMax[k]*VOL[:,k], label='Volume')
    if np.max(OV[:,k])!=0:
        hl13=plt.plot(float(OutMax[k])/np.max(OV[:,k])*OV[:,k], label='Overflow')
    hl14=plt.plot(OutMax[k]*np.ones(OUT.shape),'--r')
    plt.title(Tank[k])
#    plt.legend(loc=2)


plt.subplot(2,3,6, sharex=ax1)
hl11=plt.plot(Qwwtp, label='Global effluent')
hl12=plt.plot(Qwwtp_Ref*np.ones(Qwwtp.shape),'--g', label='reference')
hl13=plt.plot(Qwwtp_MAX*np.ones(Qwwtp.shape),'--r')



plt.show()
