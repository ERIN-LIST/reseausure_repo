# -*- coding: utf-8 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

import sys
import logging
from datetime import datetime
import re
from collections import defaultdict
from copy import deepcopy

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

logging.getLogger(__name__).addHandler(NullHandler())
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Dummy(object):
    def __init__(self,*args,**kwargs):
        pass
    def updateConf(self,*args,**kwargs):
        pass
    def updateCSOTConf(self,*args,**kwargs):
        pass
    def run(self,*args,**kwargs):
        pass



import numpy as np
import numpy.ma as ma
np.set_printoptions(precision=3,linewidth=200)
import cvxpy

from utilities.GPCStateUtilities import getSysGPCState
#from CheckNetworkConfig import CheckNetworkConfig



class Opti(object):
    """
    Algo class to control CSO tanks with the proposed global predictive control approach.
    Currently the network is composed of 3 CSO tanks plus one WWTP!
        #1 : North
        #2 : East
        #3 : West

    and others catchment drained by a separate system
        #1 : South
    
    This network structure is still hard coded
    """

    #-----------------------------------------------------------------------------#
    #-------------------------Network Config--------------------------------------#
    #-----------------------------------------------------------------------------#

    # Network config HARD CODED
    # ID, Source, Sink, Status, FlowType, Volume (m3), Qmaintenance(l/s), Qmax (l/s) , FlowTimeToSink (min), OvSensitivity


    #TO DO : set or update Qmax, Qmaintenance and FlowTimeToSink
#    CSOT_cf = { 'KAHe':{'Source':set(['North','East','West']),'Sink':'','Status':'','FlowType':'',
#                        'Volume':np.NaN, 'Qmaintenance':np.NaN, 'Qmax':np.NaN, 'FlowTimeToSink':0, 'OvSensitivity':np.NaN},
#                'East':{'Source':'catchment', 'Sink':'KAHe', 'Status':'c', 'FlowType':'Pumped', 'h_OnOffRef':'Lb',
#                        'Volume':570, 'h_Pon':115, 'h_Poff':95, 'Qmaintenance':14, 'Qmax':40, 'FlowTimeToSink':76, 'OvSensitivity':1},
#                'North':{'Source':'catchment', 'Sink':'KAHe', 'Status':'c', 'FlowType':'Gravity',
#                        'Volume':390, 'Qmaintenance':23, 'Qmax': 130,  'FlowTimeToSink':51, 'OvSensitivity':1},
#                'West':{'Source':'catchment', 'Sink':'KAHe', 'Status':'c', 'FlowType':'Gravity',
#                        'Volume':280, 'Qmaintenance':15, 'Qmax':100, 'FlowTimeToSink':32, 'OvSensitivity':5},
#                'South':{'Source':'catchment', 'Sink':'KAHe', 'Status':'uc', 'FlowType':'Gravity',
#                           'Volume':np.NaN, 'Qmaintenance':1.5, 'Qmax':4, 'FlowTimeToSink':8, 'OvSensitivity':np.NaN},
#                }
    CSOT_cf = { 'KAHe':{'Source':set(['North','East','West']),'Sink':'','Status':'','FlowType':'',
                        'Volume':np.NaN, 'Qmaintenance':np.NaN, 'Qmax':np.NaN, 'FlowTimeToSink':0, 'OvSensitivity':np.NaN},
                'East':{'Source':'catchment', 'Sink':'KAHe', 'Status':'c', 'FlowType':'Pumped', 'h_OnOffRef':'Lb',
                        'Volume':570, 'h_Pon':115, 'h_Poff':95, 'Qmaintenance':14, 'Qmax':150, 'FlowTimeToSink':76, 'OvSensitivity':1},
                'North':{'Source':'catchment', 'Sink':'KAHe', 'Status':'c', 'FlowType':'Gravity',
                        'Volume':390, 'Qmaintenance':23, 'Qmax': 80,  'FlowTimeToSink':51, 'OvSensitivity':1},
                'West':{'Source':'catchment', 'Sink':'KAHe', 'Status':'c', 'FlowType':'Gravity',
                        'Volume':280, 'Qmaintenance':15, 'Qmax':220, 'FlowTimeToSink':32, 'OvSensitivity':5},
                'South':{'Source':'catchment', 'Sink':'KAHe', 'Status':'uc', 'FlowType':'Gravity',
                           'Volume':np.NaN, 'Qmaintenance':1.5, 'Qmax':4, 'FlowTimeToSink':8, 'OvSensitivity':np.NaN},
                }
    #ToDo: update the h/V map to more realistic data for all the structures
    # GSC: Kaund and Bued have a volume in the upstream sewer that needs to be considered.
    #      --> This can be done with an partial linear adaptation of the hVmapping.
    CSOT_hVmap = {'East':[(95,0),(115,9),(155,58),(170,74),(412,CSOT_cf['East']['Volume'])],
                  'North':[(20,0),(80,40),(350,CSOT_cf['North']['Volume'])],
                  'West':[(0,0),(300,CSOT_cf['West']['Volume'])],
                  }


    # The QMax for the pipes are in [m3/10Min] ToDo: homogenize the configuration to a single unit.
#    QmaxConst_cf = []
#    QmaxConst_cf.append([{'North':20, 'East':45} ,80])
#    QmaxConst_cf.append([{'North':34, 'East':59, 'South':15 } ,120]) 
    QmaxConst_cf = []
    QmaxConst_cf.append([{'North':20, 'East':45} ,120])
    QmaxConst_cf.append([{'North':34, 'East':59, 'West':15 } ,144]) 




    def __init__(self,conf,sysVars=None,stateVars=None):

        self.verbose_solver = False
        if conf.get('SolverVerbos',0) > 0:
            self.verbose_solver = True

        self.QmaxConst = deepcopy(self.QmaxConst_cf)

        UnControlledTank = [k for k in self.CSOT_cf.iterkeys() if self.CSOT_cf[k]['Status'] in ['m','uc']]
        self.ControlledTank = [k for k in self.CSOT_cf.iterkeys() if self.CSOT_cf[k]['Status']=='c']
        self.ConfigTanks = [x for x in self.CSOT_cf.iterkeys() if self.CSOT_cf[x]['Status'] in ['c','m','uc']]


        #-----------------------------------------------------------------------------#
        #-------------------------Parameters------------------------------------------#
        #-----------------------------------------------------------------------------#
        # TO DO : get default from config

        # control time period
        self.t_update = conf['ControlTimeperiod'] #[s]; ToDo: This should come from the caller somehow (can change over time)
        self.unitConv = {'l/s':float(self.t_update)/1000.} # "*" [l/s] -> [m3/control-period] ; "/" [m3/control-period] -> [l/s]
        self.unitConv['m3/h'] = float(self.t_update)/3600. # "*" [m3/h] -> [m3/control-period] ; "/" [m3/control-period] -> [m3/h]

        # extend CSOT_cf with calculated volume limits for switching controllable <-> controlled
        # Update CSOT_cf Qmaintenance with sysVars if existing.
        for ti in self.ConfigTanks:
            CSOTi_cf = self.CSOT_cf[ti]
            # 1. Update if existing Qmaintenance and hPon/off first because they are used in Cbl/C switching
            for opcVi,cfKi in [["Qmaintenance","Qmaintenance"],["hPon","h_Pon"],["hPoff","h_Poff"]]:
                #Check config key existence
                if not cfKi in CSOTi_cf:
                    continue
                vari = ':'.join((ti,opcVi))
                #Check opcVariable existence
                if vari in sysVars:
                    value = sysVars[vari].value
                    if value != None:
                        unitConv = 1.0
                        if cfKi in ("Qmaintenance",):
                            unitConv = self.unitConv['m3/h'] / self.unitConv['l/s']
                        CSOTi_cf[cfKi] = value * unitConv

            # Extent or (re)init volume and InEst limits for Cbl/C switching
            if ti in self.ControlledTank:
                self._init_CblC_Config(ti,CSOTi_cf)

        # Parameters used in the subgoals definition
        cOP = conf['ParamOptiProb']
        ArtOptOv = -10.0;
        self.Yref = cOP['YRef'] #[l/s]; ToDo: should come from system variables (parameter to be modified by user)
        self.Yref=self.Yref*self.unitConv['l/s'] #[m3/control-period]

        self.MaxWWTP= cOP['MaxWWTP'] #[l/s]; ToDo: should come from system variables (parameter to be modified by user)
        self.MaxWWTP=self.MaxWWTP*self.unitConv['l/s'] #[m3/control-period]


        self.NbRUB = len(self.ControlledTank+UnControlledTank)

        #self.InflowForecast = True #No Assumption
        self.InflowForecast = False #Assumption constant

        #-----------------------------------------------------------------------------#
        #-----------------------------------------------------------------------------#


        #-----------------------------------------------------------------------------#
        #-------------------------Parameters------------------------------------------#
        #-----------------------------------------------------------------------------#
        self.VolMax = np.array([self.CSOT_cf[x]['Volume'] for x in self.ConfigTanks])
        self.OutMax = np.array([self.CSOT_cf[x]['Qmax'] for x in self.ConfigTanks])
        self.OutMax = self.OutMax*self.unitConv['l/s']
        self.StepDelayed = np.array([self.CSOT_cf[x]['FlowTimeToSink'] for x in self.ConfigTanks])
        self.StepDelayed = (self.StepDelayed/(float(self.t_update)/60)).round()
        self.MaxLag = int(np.max(self.StepDelayed)) #  number of GPC iterations over the Control horizon
        self.NbXPart = self.NbRUB*self.MaxLag

        for k in self.QmaxConst:
            for ik,iv in k[0].iteritems():
                k[0][ik]=iv/((self.t_update)/60)

        OutMIN = 0;

        QMaint = np.array([self.CSOT_cf[x]['Qmaintenance'] for x in self.ConfigTanks])
        QMaint = QMaint*self.unitConv['l/s']
        self.QMaint_extend = np.ravel( np.tile(np.c_[QMaint],self.MaxLag))
        #-----------------------------------------------------------------------------#
        #-----------------------------------------------------------------------------#


        #-----------------------------------------------------------------------------#
        #-------------------------Variables Initialisation----------------------------#
        #-----------------------------------------------------------------------------#
        # TO DO :  Give some values (current volumes, few history values for outflows)
        #Init the default values for the alogrithm history
        self._init_AlgHistory()

        self.RUB_inEST = np.zeros((self.NbRUB,1))
        self.Ov = np.zeros((self.NbRUB,1))
        self.Ov_Real = np.zeros((self.NbRUB,1))
        self.OutComm = np.zeros((self.NbRUB,1))
        if sysVars:
            self.updateAlgHistory(sysVars)
            self.OutComm = self.RUB_OUT_Real[[-1],:].T

        self.Volumes = self.Volumes_Real
        #-----------------------------------------------------------------------------#
        #-----------------------------------------------------------------------------#










        #-----------------------------------------------------------------------------#
        #-------------------------Problem Formulation---------------------------------#
        #-----------------------------------------------------------------------------#
        #--- unchanged matrices between 2 successive steps ---------------------------#
        #--- as long as the network structure or parameters does not change ----------#


        #--- Decision Variables-----------------------#
        # NbTanks*MaxLag first variables represent the water volume over the prediction horizon grouped by tanks
        # The following NbTanks*MaxLag variables represent the outflow volume over the prediction horizon grouped by tanks
        # The last NbTanks*MaxLag variables represent the overflow volume over the prediction horizon grouped by tanks
        self.x = cvxpy.Variable(3*self.NbXPart,1,name='x')




        #--- Matrix C (from the Equality Constraint : Cx = D )-----------------------#
        C_Vol=np.identity(self.NbXPart)-np.diag(np.ones(self.NbXPart-1),-1)
        k=np.arange(self.MaxLag+1,self.NbXPart,self.MaxLag)
        C_Vol[k-1,k-2]=0

        C_Out=np.identity(self.NbXPart)
        self.TkinCascade =[[ idx , self.ConfigTanks.index(self.CSOT_cf[val]['Sink']) ] for idx, val in enumerate(self.ConfigTanks) if self.CSOT_cf[val]['Sink'] not in 'KAHe' ]
        for i in range(len(self.TkinCascade)):
            tku = self.TkinCascade[i][0]
            tkd = self.TkinCascade[i][1]
            Ctemp = -np.eye(self.MaxLag)
            C_Out[tkd*self.MaxLag:(tkd+1)*self.MaxLag , tku*self.MaxLag:(tku+1)*self.MaxLag] \
            = np.hstack(( Ctemp[:,self.StepDelayed[tku]:] , np.zeros((self.MaxLag,self.StepDelayed[tku])) ))


        C_Ov=np.identity(self.NbXPart)

        self.C = np.hstack([C_Vol,C_Out,C_Ov])
        del(C_Vol,C_Out,C_Ov)


        self.EQCxD_L = self.C*self.x



        #--- CostFunction : min |Ax-B|-------------------------#
        Av = np.array([])
        for i in range(self.NbRUB):
                Av_temp = np.tile(-self.VolMax[i]*np.identity(self.MaxLag),(1,self.NbRUB)) #use positive coeff and multiply by (-1) only at the end ?
                Av = np.concatenate([x for x in [Av,Av_temp] if x.size > 0])
                del(Av_temp)

        self.Aout = np.array([])
        for i in range(self.NbRUB):
                if self.CSOT_cf[self.ConfigTanks[i]]['Sink'] == 'KAHe':
                    Atemp = np.identity(self.MaxLag)
                    if self.StepDelayed[i]>1:
                        Aout1 = np.zeros((self.StepDelayed[i]-1,self.MaxLag))
                        Aout2 = np.zeros((self.MaxLag-(self.StepDelayed[i]-1),self.MaxLag))
#                        Aout_temp = np.vstack([Aout1,Aout2])
                        Aout_temp = np.vstack([Aout1,np.identity(self.MaxLag),Aout2])
                    else:
                        Aout_temp = np.vstack([np.identity(self.MaxLag),np.zeros((self.MaxLag,self.MaxLag))])
                else :#tanks in cascade
                    Aout_temp = np.zeros((2*self.MaxLag,self.MaxLag))
                self.Aout = np.concatenate([x for x in [self.Aout,Aout_temp] if x.size > 0],1)
                del(Aout_temp)

        A_Ov = np.identity(self.NbXPart)

        Zsq = np.zeros((self.NbXPart,self.NbXPart))
        Zrect = np.zeros((2*self.MaxLag,self.NbXPart))
        self.A=np.vstack([np.hstack([Av,Zsq,Zsq]), np.hstack([Zrect,self.Aout,Zrect]), np.hstack([Zsq,Zsq,A_Ov])])
        del(Av,A_Ov,Zsq,Zrect)



        self.A0 = np.array([])
        for i in range(self.NbRUB):
            if self.CSOT_cf[self.ConfigTanks[i]]['Sink'] == 'KAHe':
                Atemp = np.identity(self.MaxLag)
            else :#tanks in cascade
                Atemp = np.zeros((self.MaxLag,self.MaxLag))
            if self.StepDelayed[i]:
                A01 = np.flipud(Atemp[:,(self.MaxLag+2-self.StepDelayed[i]-1):] )
            else :
                A01 = np.flipud(Atemp[:,(self.MaxLag+2-self.StepDelayed[i]-1+1):] )
            self.A0 = np.concatenate([x for x in [self.A0,A01] if x.size > 0],1)
            del(A01,Atemp)

        self.A0 = np.vstack((self.A0,np.zeros((self.MaxLag,self.A0.shape[1]))))


        self.Bv = np.zeros((self.NbXPart,1))
        self.B_Ov = ArtOptOv*np.ones((self.NbXPart,1))

        # weighting coefficients
        self._update_CFWeight(conf['CostFunctionWeights'])


        #-----------------------------------------------------------------------------#
        #-------------------------Constraints-----------------------------------------#

        #--- constraints on Vol, Out, Ov--------------------------------#
        #--- x >= l --------------------------------#
        l_Vol = np.zeros([self.NbXPart,1])
        l_Out = OutMIN*np.ones([self.NbXPart,1])
        l_Ov = np.zeros([self.NbXPart,1])
        LowerLimit = np.vstack([l_Vol,l_Out,l_Ov])
        LowerLimit.flatten() # DF it probably exists a simple way to do that
        del(l_Vol,l_Out,l_Ov)
        #--- x <= u --------------------------------#
        u_Vol = np.tile(self.VolMax,(self.MaxLag,1))
        u_Out = np.tile(self.OutMax,(self.MaxLag,1))
        UpperLimit = np.hstack([u_Vol,u_Out])
        UpperLimit = UpperLimit.T.reshape((self.NbXPart*2,1)) # DF it probably exists a simple way to do that
        del(u_Vol,u_Out)




        #--- Hard constraints: l<=x<=u ---
        self.constr_cf = ma.hstack([self.x[kk] >= LowerLimit[kk] for kk in range(3*self.NbXPart)])
        for kk in range(2*self.NbXPart) :
            self.constr_cf = ma.hstack((self.constr_cf, self.x[kk] <= UpperLimit[kk]))


        ### ----- Debug output ----
        #print 'Constrains block - 1'




        #--- Maximum InFlow to the WWTP over the prediction horizon ---
        #---'Constrains block - 2'
        TS2 = np.zeros((2*self.MaxLag,self.x.size[0]))
        TS2[:,self.NbXPart:2*self.NbXPart]=self.Aout
        for k in range(self.NbRUB):
            ColIdx = self.NbXPart-1+(k+1)*self.MaxLag
            RowIdx = np.where(TS2[:,ColIdx]==1)[0]
            if RowIdx:
                TS2[RowIdx[0]:-1,ColIdx] = 1
        self.LEQ2_L = TS2*self.x


        #--- Maximum Flow in pipes prediction horizon ---
        #---'Constrains block - 3.1'
        IND_U = np.reshape(np.c_[self.NbXPart:2*self.NbXPart],(self.MaxLag,self.NbRUB),order='F')
        NbQMaxConst = len(self.QmaxConst)
        self.TS31 = np.zeros((0,self.x.size[0]))
        self.TS32 = np.zeros((0,self.x.size[0]))
        self.Qmax31 = np.zeros((0,1))
        self.TanksName31 = []
        for k in xrange( NbQMaxConst ):
            U_Ind = np.array([self.ConfigTanks.index(kk) for kk in self.QmaxConst[k][0].keys() if kk in self.ConfigTanks])
            if U_Ind.size == 0: continue
            IND_Utmp = IND_U[:,U_Ind] #new addition
            U_Delay = np.array([self.QmaxConst[k][0][self.ConfigTanks[kk]] for kk in U_Ind])
            Qmax = self.QmaxConst[k][1]

            Ninputs = U_Ind.size

            IndNode = np.tile(IND_U[-1,U_Ind],(2*self.MaxLag,1))
            for kk in xrange(Ninputs):
                IndNode[U_Delay[kk]+np.arange(self.MaxLag),kk] = IND_Utmp[:,kk]
            IndNode = IndNode[U_Delay.max()+range(self.MaxLag),:]
            IndNode = IndNode.astype(int)

            for Ii in IndNode:
                if len(Ii) == 0:
                    continue
                ts = np.zeros((1,self.x.size[0]))
                ts[0,Ii] = 1
                self.TS31 = np.vstack((self.TS31, ts))
                self.Qmax31 = np.vstack( (self.Qmax31, Qmax) )

            self.TanksName31 = self.TanksName31 + [set(self.QmaxConst_cf[k][0].keys())]*IndNode.shape[0]

            #---'Constrains block - 3.2
            Maxgap = U_Delay.max() - U_Delay.min()
            U_Delay = U_Delay - U_Delay.min()
            if Maxgap > 0:
                LHS = np.tile(np.c_[1:Maxgap+1],(Ninputs,1)).T - np.tile(U_Delay,(Maxgap,1))
                for kk in xrange(Maxgap):
                    FL = LHS[kk,:] > 0
                    xidx = np.diag(IND_U[np.ix_(LHS[kk,FL]-1,U_Ind[FL])])
                    ts = np.zeros((1,self.x.size[0]))
                    ts[0,xidx] = 1
                    self.TS32 = np.vstack((self.TS32, ts))

                ### ----- Debug output ----
                #print 'Constrains block - 3.2 k=%s/%s %s' % (k,NbQMaxConst,NM)

        if self.TS32.shape[0] > 0 :
            self.LEQ32_L = self.TS32*self.x
        else :
            self.LEQ32_L = None


        for kk in range(self.Qmax31.size) :
            self.constr_cf = ma.hstack((   self.constr_cf , self.TS31[kk,:].reshape(1,self.NbXPart*3)*self.x <= self.Qmax31[kk]   ))

        self.updateStructOptPB()

        #-----------------------------------------------------------------------------#
        #-----------------------------------------------------------------------------#

    def _init_CblC_Config(self,sti,CSOTi_cf):
        """
        Extent or (re)init CSOT config with volume and InEst limits for Cbl/C switching
        """
        if CSOTi_cf['FlowType']=='Pumped':
            LOnOffRef = CSOTi_cf.get('h_OnOffRef','Lb') #If not specified use default 'Lb' VMap
            hvm = np.array(zip(*self._getVMap(sti)[LOnOffRef]))
            vonoff = {}
            for onoff in ['Pon','Poff']:
                vi = np.interp(CSOTi_cf['h_'+onoff],hvm[0],hvm[1])
                vonoff['V_'+onoff] = vi
            DeltaVponoff = vonoff['V_Pon']-vonoff['V_Poff']
            CSOTi_cf['VLim_Cbl'] = vonoff['V_Pon']+0.5*DeltaVponoff
            CSOTi_cf['VLim_C'] = vonoff['V_Pon']-0.9*DeltaVponoff
            CSOTi_cf['InEst_Cbl'] = 1.5 * CSOTi_cf['Qmaintenance']*self.unitConv['l/s']
            CSOTi_cf['InEst_C'] = 0.9 * CSOTi_cf['Qmaintenance']*self.unitConv['l/s']
        elif CSOTi_cf['FlowType'] == 'Gravity':
            CSOTi_cf['VLim_Cbl'] = 0.06*CSOTi_cf['Volume']
            CSOTi_cf['VLim_C'] = 0.04*CSOTi_cf['Volume']
            CSOTi_cf['InEst_Cbl'] = 1.0 * CSOTi_cf['Qmaintenance']*self.unitConv['l/s']
            CSOTi_cf['InEst_C'] = 0.9 * CSOTi_cf['Qmaintenance']*self.unitConv['l/s']
        else:
            raise ValueError("Unhandled CSOT FlowType configured: %s"%ti)


    def _init_AlgHistory(self,OUT_last2hours=None):
        #init Outflow history
        if OUT_last2hours:
            self.OUT_last2hours = OUT_last2hours
        else:
            SName,QMaint = zip(*[(ki,self.CSOT_cf[ki]['Qmaintenance']) for ki in self.ConfigTanks])
            self._OUT_last2hours = np.ones([self.MaxLag-1,1])*np.array(QMaint)*self.unitConv['l/s']
            self.OUT_last2hours = self._OUT_last2hours.view(dtype={'names':SName, 'formats':['f8',]*len(SName)})
        #init Volume history
        self._Vol_Real_hist = np.zeros((2,self.NbRUB))
        self.Volumes_Real = self._Vol_Real_hist[-1,:].reshape(self.NbRUB,1)

    def _update_CFWeight(self,cfW):
        ScV = cfW['VolumeHomogenity']
        ScY = cfW['NetworkOutflowRef']
        ScOv = cfW['OverflowMin']

        if 'HomogenityHorizonProfile' not in cfW or cfW['HomogenityHorizonProfile'] == 'Constant':
            CF_Weight_V = ScV*np.ones((self.NbXPart,1))
        elif cfW['HomogenityHorizonProfile'] == 'Linear':
            Weigth_V_function = np.arange(0,1,1./self.MaxLag)+1./self.MaxLag
            CF_Weight_V = ScV*np.tile(Weigth_V_function,self.NbRUB).reshape(self.NbXPart,1)
        else:
            logger.error('Config parameter "HomogenityHorizonProfile" is set to an unsupported value: %s\n -> Default is used' % (cfW['HomogenityHorizonProfile'],))
            CF_Weight_V = ScV*np.ones((self.NbXPart,1))

        CF_Weight_Out = np.vstack((ScY*np.ones((self.MaxLag,1)),np.zeros((self.MaxLag,1))))

        self.OvSensitivity = cfW['OvSensitivity']
        if self.OvSensitivity:
                ScOV = ScOv*np.array([self.CSOT_cf[x]['OvSensitivity'] for x in self.ConfigTanks])
                CF_Weight_Ov=np.tile(ScOV,(self.MaxLag,1))
                CF_Weight_Ov=CF_Weight_Ov.T.reshape(self.NbXPart,1)
        else :
                CF_Weight_Ov = ScOv*np.ones((self.NbXPart,1))

        self.CF_Weight = np.vstack([CF_Weight_V, CF_Weight_Out, CF_Weight_Ov])

    def _getData(self,sysVars,VarKey):
        struct_cf = set(self.CSOT_cf.keys())
        sti = VarKey.split(':')[0]
        if sti in struct_cf:
            return sysVars[VarKey].value
        else:
            pass #ToDo logging of this situation

    def updateConf(self,conf):
        if self.t_update != conf['ControlTimeperiod']:
            logger.warning('Changing "ControlTimeperiod" is currently not supported')

        cOP = conf['ParamOptiProb']
        self.Yref = cOP['YRef']*self.unitConv['l/s']
        self.MaxWWTP= cOP['MaxWWTP']*self.unitConv['l/s']
        # weighting coefficients
        self._update_CFWeight(conf['CostFunctionWeights'])

        if conf.get('SolverVerbos',0) > 0:
            self.verbose_solver = True
        else:
            self.verbose_solver = False

    def updateCSOTConf(self,gpcSysState,conf,sysVars):
        def updateQMaintenance(self,sti,opcValue):
            self.CSOT_cf[sti]['Qmaintenance'] = opcValue * self.unitConv['m3/h'] / self.unitConv['l/s']
            idx = self.ConfigTanks.index(sti)
            self.QMaint_extend[range(idx,idx+self.MaxLag)] = self.CSOT_cf[sti]['Qmaintenance']

        #ToDo-GSc: parameters conf and sysVars are only needed until MPCAlgo can correctly handle reconfigurations without a complete initialization.
        update = defaultdict(list)
        #Check for Qmaintenance|hPon|hPoff change
        MaintFilt = re.compile(".*(Qmaintenance|hPon|hPoff)$")
        for ki in filter(MaintFilt.match, sysVars.keys()):
            sti = ki.split(':')[0]
            if ki in sysVars:
                Diff = sysVars[ki].getDiff()
                # Only rewrite config if value has changed
                if Diff != None and Diff.Diff[0] != 0:
                    if ki.endswith("Qmaintenance"):
                        updateQMaintenance(self, sti, sysVars[ki].value)
                        update["Qmaintenance"].append(sti)
                    elif ki.endswith("hPon"):
                        self.CSOT_cf[sti]['h_Pon'] = sysVars[ki].value
                        update["hPon/off"].append(sti)
                    elif ki.endswith("hPoff"):
                        self.CSOT_cf[sti]['h_Poff'] = sysVars[ki].value
                        update["hPon/off"].append(sti)
            else:
                logger.error('This should be impossible: %s not in sysVars' % (ki,))
        #Check for State change
        for sti in gpcSysState:
            if self.CSOT_cf.has_key(sti):
                CSOTi_cf = self.CSOT_cf[sti]
                if gpcSysState[sti] in ['offline','maintenance'] and CSOTi_cf['Status'] == 'c':
                    CSOTi_cf['Status'] = 'm'
                    update['Status'].append(sti)
                elif gpcSysState[sti] in ['controllable',] and CSOTi_cf['Status'] == 'm':
                    CSOTi_cf['Status'] = 'c'
                    update['Status'].append(sti)
                    update['CblC'].append(sti) # not always needed but sometimes so do it to be sure.
                elif gpcSysState[sti] == 'controlled' and CSOTi_cf['Status'] == 'm':
                    #This should newer happon! But is possible if by default sti is configured to 'm' and a restart of GPC is done in a situation where sti was "controlled"
                    logger.error("MPCAlgo-error: CSOT_cf[%s] is 'm' but SysGPCState is %s" % (sti,gpcSysState[sti]))
                    CSOTi_cf['Status'] = 'c'
                    update['Status'].append(sti)
        if not set(["Qmaintenance", "hPon/off", "CblC"]).isdisjoint(update):
            for sti in set(update["Qmaintenance"]+update["hPon/off"]+update["CblC"]):
                self._init_CblC_Config(sti, self.CSOT_cf[sti])
        if not set(["Qmaintenance", "Status"]).isdisjoint(update):
            #--- Update Matrix -----------------------#
            self.ControlledTank = [k for k in self.CSOT_cf.iterkeys() if self.CSOT_cf[k]['Status']=='c']
            self.updateStructOptPB()
        for ki in update:
            if update[ki] != []:
                logger.debug("updateCSOTConf: %s - %s" % (ki,update[ki]))


    def updateAlgHistory(self,sysVars):
        OutFilt = re.compile(".*Qout$")
        OutVars = filter(OutFilt.match, sysVars.keys())

        # Update the Outflow history data.
        self._OUT_last2hours = np.roll(self._OUT_last2hours,-1,axis=0)
        self.OUT_last2hours = self._OUT_last2hours.view(self.OUT_last2hours.dtype)
        for ki in OutVars:
            sti = ki.split(':')[0]
            if sti not in self.OUT_last2hours.dtype.fields:
                #There may be structures existing in sysVars but are not used in Opti()
                continue
            outi = self._getData(sysVars, ki)
            if outi == None:
                outi = self.CSOT_cf[sti]['Qmaintenance'] * self.unitConv['l/s']
            else:
                outi *= self.unitConv['m3/h']
            self.OUT_last2hours[sti][-1] = outi
        self.RUB_OUT_Real = self.OUT_last2hours[self.ConfigTanks].view((np.float64,len(self.ConfigTanks))).reshape([-1,len(self.ConfigTanks)])
        # Update the Volume history data.
        self._Vol_Real_hist = np.roll(self._Vol_Real_hist,-1,axis=0)
        self.Volumes_Real = self._Vol_Real_hist[-1,:].reshape(self.NbRUB,1)
        self.setVolumes(sysVars)
        self.setOv(sysVars)

    def _getVMap(self,csot):
        hVmap = self.CSOT_hVmap[csot]
        if not isinstance(hVmap,dict):
            hVmap = {'Lb':hVmap}
        return hVmap

    def setVolumes(self,sysVars):
        for ti in self.ControlledTank:
            idx = self.ConfigTanks.index(ti)
            hVmap = self._getVMap(ti)
            vi = 0
            for hKi in hVmap:
                ki = ":".join([ti,hKi])
                hi = self._getData(sysVars, ki)
                hvm = np.array(zip(*hVmap[hKi]))
                vi += np.interp(hi,hvm[0],hvm[1])
            self.Volumes_Real[idx] = vi
    def setOv(self,sysVars):
        for ti in self.ControlledTank:
            idx = self.ConfigTanks.index(ti)
            hMax = self._getVMap(ti)['Lb'][-1][0]
            ki = ":".join([ti,'Lb'])
            hi = self._getData(sysVars, ki)
            ov = np.interp(hi,[hMax,hMax+10],[0,50]) #10cm over hMax, MaxOv = 50
            self.Ov_Real[idx] = ov

    def calcRUBInEst(self,RUB_IN_Real):
        if self.InflowForecast:
            #RUB_intemp =
            RUB_intemp = np.tile(RUB_IN_Real.T,(self.MaxLag,1)) #for example
            self.RUB_inEST = RUB_IN_Real
            # to be completed in case of Tanks in cascade (see Matlab code)
            return RUB_intemp.T.reshape((self.NbXPart,1))
        else: #No Assumption means used constant current inflows
            #discrepancy between the real Inflow during the last period and the expected one
            RUB_intemp = np.zeros((self.MaxLag,self.NbRUB)) # to be completed in case of Tanks in cascade (see Matlab code)
            self.TkinCascade
            for i in range(len(self.TkinCascade)):
                tku = self.TkinCascade[i][0]
                tkd = self.TkinCascade[i][1]
                RUB_intemp[:self.StepDelayed[tku],tkd] += self.RUB_OUT_Real[-self.StepDelayed[tku]:,tku]


            Discrepancy = self.Volumes_Real-self.Volumes + \
                          self.RUB_OUT_Real[[-1],:].T-self.OutComm + \
                          self.Ov_Real-self.Ov
            self.RUB_inEST = self.RUB_inEST+Discrepancy
            feasCheck = -self.Volumes_Real/self.MaxLag > self.RUB_inEST
            if feasCheck.any():
                # Adapt RUB_inEST to guaranties the optimization problem feasability
                self.RUB_inEST = np.where(feasCheck,
                     -self.Volumes_Real/self.MaxLag, self.RUB_inEST)
                listLimited = [self.ConfigTanks[i] for i,tfi in enumerate(feasCheck) if tfi]
                logger.debug("RUB_inEst was limited to Volumes_Real for the Tanks: %s" % (listLimited,))
            #BUGFIX #Discrepancy = np.tile(self.RUB_inEST,(self.MaxLag,1))
#            return np.tile(self.RUB_inEST,(1,self.MaxLag)).flatten().reshape(self.D.shape)
            return (RUB_intemp.flatten('F') + np.tile(self.RUB_inEST,(1,self.MaxLag)).flatten()).reshape(self.D.shape)






    def updateStructOptPB(self):
        print self.ControlledTank

        #--- Matrix A -----------------------#
        self.VolMaxGPC = np.sum(np.array([self.CSOT_cf[x]['Volume'] for x in self.ControlledTank]))
        A_temp = self.A.copy()
        A_temp[:self.NbXPart , :self.NbXPart] /= float(self.VolMaxGPC)
        A_temp[:self.NbXPart , :self.NbXPart] += np.identity(self.NbXPart)

#        a_mask = ma.array(cvxpy.matrix(A_temp*self.CF_Weight),mask=False)
        A_temp = np.nan_to_num(A_temp)
        a_mask = ma.array(A_temp*self.CF_Weight,mask=False)

        self.Uncont_TF = np.array([x not in self.ControlledTank for x in self.ConfigTanks])
        self.Uncont_TF = np.kron(self.Uncont_TF,np.ones(self.MaxLag))
        Index_UnCont = np.nonzero(self.Uncont_TF)[0]

        a_mask.mask[:self.NbXPart,0] = self.Uncont_TF # Hom
        a_mask.mask[-self.NbXPart:,0] = self.Uncont_TF # Ov
        a_mask = ma.mask_rows(a_mask)

        a_mask[np.ix_(np.arange(self.NbXPart), Index_UnCont)] = ma.masked# Hom

        Vect = ~a_mask.any(axis=1).mask
        a_mask = a_mask.compress(Vect.flatten(),axis=0)


        self.AX = a_mask.filled(0)*self.x # other method : AvX and concatenate with self AoutAovX

        self.maskB = ~Vect

        self.constr = self.constr_cf # need deep copy ?

        # Mask the constraints where only uncontrolled tanks are involved
        self.constr.mask[:5*self.NbXPart] = np.tile(self.Uncont_TF,(1,5))

        UnControlledTank = set(self.ConfigTanks)-set(self.ControlledTank)
        Constr31TF = [not(x-UnControlledTank) for x in self.TanksName31]
        self.constr.mask[5*self.NbXPart:] = Constr31TF

        self.constr = list(self.constr.compressed())

        TS1 = np.zeros((len(Index_UnCont),self.NbXPart))
        Z = zip(np.arange(len(Index_UnCont)),Index_UnCont)
        for tup in Z :
            TS1[tup]=1
        # The uncontrolled tanks outflows are assumed to be constant and equals to the QMaintenace flows over the prediction horizon
        self.constr.append( TS1*self.x[self.NbXPart:2*self.NbXPart,0] ==  self.QMaint_extend[Index_UnCont] .T )

        # The uncontrolled tanks overflows are assumed to be 0 over the prediction horizon
        self.constr.append( TS1*self.x[2*self.NbXPart:,0] == np.zeros((np.sum(TS1),1))  )



#        for ind in Index_UnCont:
#            del self.EQCxD_L.data[ind]
#        AA = self.EQCxD_L
#        AA.__mul__(cvxpy.matrix(np.zeros((1,132))))
#
#        AA.data[6]=[]

#self.EQCxD_L = cvxpy.matrix(self.C)*self.x
#AA = (self.EQCxD_L).variables
#del AA[8:]


    def run(self,sysVars,stateVars=None,outVars=None,RUB_IN_Real=None):
        try:

            #TO DO
            #-----------------------------------------------------------------------------#
            #-------------------------Data import and pretreatment------------------------#
            #-----------------------------------------------------------------------------#
            self.updateAlgHistory(sysVars)

            #-----------------------------------------------------------------------------#
            #-----------------------------------------------------------------------------#



            #--- Matrix D -----------------------#
            self.D = np.zeros((self.NbXPart,1))
            self.D[ ::self.MaxLag] = self.Volumes_Real


            # Assumption on CSOTs' inflow over the prediction horizon
            InEst = self.calcRUBInEst(RUB_IN_Real)
            self.D += InEst

            #--- Matrix B -----------------------#

            self.Upast = np.flipud(self.RUB_OUT_Real[-self.MaxLag:,:])
            self.Upast = self.Upast.T[np.where((np.tile(self.StepDelayed,(self.MaxLag-1,1)) - np.tile(np.c_[np.arange(self.MaxLag-1)+1],(1,self.NbRUB))).T >0)]
            self.Upast = np.c_[self.Upast]

            Bout = self.Yref*np.ones((2*self.MaxLag,1))-np.dot(self.A0,self.Upast)

            self.B=np.vstack([self.Bv,Bout,self.B_Ov])
            self.b_mask = ma.array(self.B*self.CF_Weight,mask=self.maskB)




        except StandardError as e:
            logger.debug( "StandardError: %s", e )
            logger.debug(sys.exc_info())




        try:
            np_formatter = np.get_printoptions()['formatter']
            np.set_printoptions(formatter={'float_kind':lambda x: "%.2f" % x})

            [OUTcommand,Y] = self.SolveOptPB()  # Out in [m3/cp], Y in [m3/cp]

            # OUTcommand, Y, self.RUB_inEST, self.Volumes self.Ov, self.ControlledTank

            BStr = "#MPCLogg (%s)\n" % (datetime.now(),)
            OutStr = '{%s}' % ', '.join(["'%s':%.2f" % (ki,OUTcommand[ki]) for ki in self.ControlledTank])
            UnControledIdx = [self.ConfigTanks.index(ci) for ci in self.ConfigTanks if ci not in self.ControlledTank]
            logger.debug(BStr+"Keys=%(CommKeys)s;\nOut = %(Out)s;\nResOut = %(ResOut).2f;\nYEst = %(YEst)s;\nInEst = %(InEst)s;\nVol = %(Vol)s;\nOv = %(Ov)s;\nOutComm = %(OutComm)s;",
                         {'InEst':self.RUB_inEST.T, 'YEst':Y.T, 'Out':self.RUB_OUT_Real, 'ResOut': self.RUB_OUT_Real[-1,UnControledIdx].sum(),
                          'Vol':self.Volumes_Real.T, 'OutComm':OutStr, 'Ov': self.Ov_Real.T, 'CommKeys':self.ConfigTanks})
            np.set_printoptions(formatter=np_formatter)

            C_Switch = defaultdict(list)
            if stateVars != None: #Do this only ones and access later.
                SysGPCState = getSysGPCState(stateVars)
            Ctanks = [(self.ConfigTanks.index(x),x) for x in self.ControlledTank]
            for i,ti in Ctanks:
                if outVars != None:
                    ki = ":".join([ti,"QoutSpN"])
                    # Unit of OPC "QoutSpN" needs to be [m3/h]
                    outVars[ki].setWriteValue(OUTcommand[ti]/self.unitConv['m3/h'])

                if stateVars != None:
                    # Handle the station state switch controlable <-> controled
                    gpcSte = SysGPCState[ti]
                    CSOTi_cf = self.CSOT_cf[ti]
                    # in state controllable
                    if gpcSte == 'controllable' and \
                       (self.RUB_inEST[i,0]>CSOTi_cf['InEst_Cbl'] or\
                        self.Volumes_Real[i,0]>CSOTi_cf['VLim_Cbl']):
                        C_Switch['C-abl -> C'].append(ti)
                        ki = ":".join([ti,"GPCOnTrig"])
                        outVars[ki].setWriteValue(1)
                    # in state controlled
                    elif gpcSte == 'controlled' and \
                       (self.RUB_inEST[i,0]<CSOTi_cf['InEst_C'] and\
                        self.Volumes_Real[i,0]<CSOTi_cf['VLim_C']):
                        C_Switch['C -> C-abl'].append(ti)
                        ki = ":".join([ti,"GPCOffTrig"])
                        outVars[ki].setWriteValue(1)
            if len(C_Switch)>0:
                CSStr = '; '.join(["%s = %s%s%s"%(si,'%(',si,')s') for si in C_Switch])
                logger.debug("#C-Switch: "+CSStr % C_Switch)








            return OUTcommand, Y

        except StandardError as e:
            logger.debug( "StandardError: %s", e )
            logger.debug(sys.exc_info())









    def SolveOptPB(self): #To Do : add input arguments if needed

        Constr = self.constr[:]


        #--- Maximum InFlow to the WWTP over the prediction horizon ---
        MaxWWTP_Ms = None
        for k in xrange(2*self.MaxLag):
            ii = np.array([int(ki) for ki in (self.Aout[k,:] > 0).astype(int).nonzero()[0]+self.NbXPart])
            if len(ii) > 0:
                MaxWWTP_M = self.MaxWWTP - np.dot(self.A0[k,:],self.Upast)
                # This value must be greater than the imposed sum of flow from Uncontrolled Tank
                Q_UnCont = np.sum(self.QMaint_extend [  ii[self.Uncont_TF[ii-self.NbXPart] == 1] - self.NbXPart ])
                MaxWWTP_M = np.where(MaxWWTP_M < Q_UnCont, Q_UnCont, MaxWWTP_M)
                # MaxWWTP_M = np.max([0,MaxWWTP_M])
                if MaxWWTP_Ms != None :
                    MaxWWTP_Ms = np.vstack( (MaxWWTP_Ms ,MaxWWTP_M) )
                else :
                    MaxWWTP_Ms = MaxWWTP_M
            else :
                MaxWWTP_Ms = np.vstack( (MaxWWTP_Ms ,0) )
        MaxWWTP_Ms = np.where(MaxWWTP_Ms< 10e-2, 0, MaxWWTP_Ms)
        Constr.append( self.LEQ2_L <= MaxWWTP_Ms  )
        ### ----- Debug output ----
        #print 'Constrains block - 2'



        if self.LEQ32_L :
            IND_U = np.reshape(np.c_[self.NbXPart:2*self.NbXPart],(self.MaxLag,self.NbRUB),order='F')
            Qmax32 = None
            NbQMaxConst = len(self.QmaxConst)
            for k in xrange( NbQMaxConst ):
                U_Ind = np.array([self.ConfigTanks.index(kk) for kk in self.QmaxConst[k][0].keys() if kk in self.ConfigTanks])
                if U_Ind.size == 0: continue
                U_Delay = np.array([self.QmaxConst[k][0][self.ConfigTanks[kk]] for kk in U_Ind])
                Qmax = self.QmaxConst[k][1]

                Maxgap = U_Delay.max() - U_Delay.min()
                U_Delay = U_Delay - U_Delay.min()
                Ninputs = U_Ind.size

                if Maxgap > 0:
                    LHS = np.tile(np.c_[1:Maxgap+1],(Ninputs,1)).T - np.tile(U_Delay,(Maxgap,1))
                    RHS = LHS - 1
                    for kk in xrange(Maxgap):
                        FL=LHS[kk,:] > 0
                        FR=RHS[kk,:] < 0
                        xidx = np.diag(IND_U[np.ix_(LHS[kk,FL]-1,U_Ind[FL])])
                        i = self.RUB_OUT_Real.shape[0]+1
                        QMkk = Qmax - np.sum( np.diag( self.RUB_OUT_Real[np.ix_(i+RHS[kk,FR]-1,U_Ind[FR])] ) )
                        # This value must be greater than the imposed sum of flow from Uncontrolled Tank
                        Q_UnCont = np.sum(self.QMaint_extend [  xidx[self.Uncont_TF[xidx-self.NbXPart] == 1] - self.NbXPart ])
                        QMkk = np.where(QMkk < Q_UnCont, Q_UnCont, QMkk)

                        Qmax32 = np.vstack( (Qmax32, QMkk) )

            Qmax32 = Qmax32[1:]
            Qmax32 = np.where(Qmax32< 10e-2, 0, Qmax32)
            Constr.append( self.LEQ32_L <= Qmax32)
        ### ----- Debug output ----
        #print 'Constrains block - 3.2'

#        CXD_mask = ma.array( cvxpy.eq( self.EQCxD_L , cvxpy.matrix(self.D) ) )
#        CXD_mask.mask = self.Uncont_TF
#        Constr.append( CXD_mask.compressed()[0] )
        Constr.append( self.EQCxD_L == self.D )
#        NM=NM+1


        Obj = cvxpy.Minimize(cvxpy.norm2(self.AX-self.b_mask.compressed().T ))
        p = cvxpy.Problem(Obj,Constr)
#        NM=NM+3
    #        p.show()
        #p.options = {'reltol': 1e-06, 'maxiters': 100, 'abstol': 1e-07, 'feastol': 1e-06} #Default configuration
        #p.options['abstol'] = 1e-3                             # Change solver configuration
        #p.options['reltol'] = 1e-2
        #p.options['feastol'] = 1e-3
    #        p.options['maxiters'] = 200
#        e = 0

        try :
            res = p.solve()
        except :
            try :
#                res= p.solve(verbose=True)
#                res = p.solve(verbose=True, solver = 'ECOS')
#                res = p.solve(verbose=True, solver = 'SCS')
                res = p.solve(verbose=True, solver='CVXOPT')
            except StandardError as err :#e.g. "domain error" when problem is poorly scaled
                logger.debug( "StandardError: %s", err )
                res = np.nan

# TO DO : redo the problem showing with the new cvxpy module
#        # Build p.show() as string for logging
#        if self.verbose_solver or not np.isfinite(res):
#            if p.action == cvxpy.defs.MINIMIZE:
#                pshowStr = '\nminimize '
#            else:
#                pshowStr = '\nmaximize '
#            pshowStr += str(p.objective)+'\n'
#            pshowStr += 'subject to\n'
#            pshowStr += str(p.constraints)
#
#            logger.debug("==== Opt-Problem ====\n%s\n==== Solution ====\n%s", pshowStr, self.x.value)


        OutDict={}
        # ToDo: Handle the nan results of the solver by (rerun the solver with less precission, overwrite with ???)
        if not np.isfinite(res):
            #GSc-ToDo: logginG
            for idx, val in enumerate(self.ConfigTanks):
                OutDict[val] = np.nan
            Y = np.ones([self.MaxLag,1])*np.nan
            self.Volumes = self.Volumes_Real
            self.OutComm = np.where(self.RUB_inEST< np.c_[self.OutMax],self.RUB_inEST, np.c_[self.OutMax])
        else:
            # ToDo: Handle small neg results (numerical precission of the solver) by (set to zero)

            # OutKp1
            xval = self.x.value[ self.NbXPart : 2*self.NbXPart : self.MaxLag]
            for idx, val in enumerate(self.ConfigTanks):
                self.OutComm[idx] = float(max(0,xval[idx]))
                if val in self.ControlledTank :
                    OutDict[val] = self.OutComm[idx,0]

            Y = np.dot(self.Aout,self.x.value[ self.NbXPart : 2*self.NbXPart ]) \
                + np.dot(self.A0,self.Upast)
            Y=Y[:self.MaxLag]

            VolumesKp1 = self.x.value[ : self.NbXPart : self.MaxLag]
            OvTemp =  self.x.value[ 2*self.NbXPart : 3*self.NbXPart : self.MaxLag]
            for k in xrange( self.NbRUB ):
                if VolumesKp1[k]+OvTemp[k]> self.VolMax[k] :
                    OvTemp[k] = VolumesKp1[k]+OvTemp[k]-self.VolMax[k]
                    VolumesKp1[k] = self.VolMax[k]
                else:
                    VolumesKp1[k] = VolumesKp1[k]+OvTemp[k]
                    OvTemp[k] = 0;

            self.Volumes = VolumesKp1
            self.Ov = OvTemp



            logger.debug("\n===Understanding the optimal solution===")

            idx_cont = np.array([self.ConfigTanks.index(val) for val in self.ControlledTank])
            NbCont = len(self.ControlledTank)
            Homogtgt_prct = 100 * np.sum(self.Volumes_Real[idx_cont]) / self.VolMaxGPC
            Vol_cont_prct = 100 * self.Volumes_Real[idx_cont].T / self.VolMax[idx_cont]
            OV_est = np.sum( np.reshape(self.x.value[ 2*self.NbXPart :],(self.NbRUB,self.MaxLag)), axis=1)[idx_cont]

            Cost =  np.power(self.AX.value.flatten()-self.b_mask.compressed(),2).T
            C1 = np.sum( np.reshape(Cost[0:NbCont*self.MaxLag],(NbCont,self.MaxLag)), axis=1)
            C2 = np.sum(Cost[NbCont*self.MaxLag:-NbCont*self.MaxLag])

            C_ArtOv = np.sum( np.reshape( np.power(self.b_mask.compressed().T[-NbCont*self.MaxLag:],2) ,(NbCont,self.MaxLag)), axis=1)
            C3 = np.sum( np.reshape(Cost[-NbCont*self.MaxLag:],(NbCont,self.MaxLag)), axis=1)
            SC1 = np.sum(np.array(C1).T[0])
            SC3 = np.sum(np.array(C3).T[0])

            CFW = self.CF_Weight.flatten()
            W_Vol = CFW[0:self.MaxLag]
            W_ov = CFW[-self.NbXPart::self.MaxLag][idx_cont].T
            W_Y = CFW[self.NbXPart]


            logger.debug( "#MPCLogg (%s)" % (datetime.now(),) )
            logger.debug( "Controlled Tanks: %s" % (self.ControlledTank,) )

            logger.debug( "OUTResults :     %s" % (self.OutComm[idx_cont].T[0],)  )

            logger.debug( "Homogeneity (TARGET = %s %%) :     %s" % (Homogtgt_prct, Vol_cont_prct,)  )
            logger.debug( "Ov_est :     %s" % (OV_est.T,)  )
            logger.debug( "Yest (TARGET = %s ) :     %s" % (self.Yref, Y.T,)  )

            logger.debug("---Cost function [Weights]---")
            logger.debug("   VoHomogenity :   %s" % (W_Vol,) )
            logger.debug("   Overflow :       %s    (artificial offset : %s)" % (W_ov[0],  C_ArtOv.T[0], ) )
            logger.debug("   Global Outflow : %s" % (W_Y,) )

            logger.debug("---Cost function [Values]---")
            logger.debug("   VolHomogenity :  %s      %s" % (SC1, np.array(C1).T[0],) )
            logger.debug("   Overflow :       %s      %s" % (SC3, np.array(C3).T[0],) )
            logger.debug("   Global Outflow : %s" % (C2,) )


            logger.debug("============================= \n")


        return OutDict, Y
