""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

import re
from datetime import *
from dateutil import tz
import logging

try:
    from ReadNeededDataTest.ReadData_useOPC import AlgData_OPC
except:
    AlgData_OPC = None

from Control.GPCVariablesConfig import GPC_Stations, GPCOutVars


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

h = NullHandler()
logging.getLogger("TriggerHandling").addHandler(h)


class ReadTrigger(object):
    TrigSizePct = 10
    gitter = 20

    def __init__(self, mode, S0_tUpdate = 900):
        self._testmode = False
        self._mode = mode
        if mode in ['test',]:
            self._testmode = True
        self.logger = logging.getLogger("TriggerHandling.ReadTrigger")
        self.S0_tUpdate = S0_tUpdate
        self.lastT = None
        self.DT = max(1, self.S0_tUpdate * self.TrigSizePct/(2*100)) # should be multiple of second >= 1[sec]
        self.lastDT = self.DT
        self.job = None
        self._waitForTrigger = False
        if AlgData_OPC and mode == 'OPCTrigger':
            self.TrigOPC = AlgData_OPC(variables={'RTrig':["S0_tUpdateTrig",]})
            self.TrigOPC.logger = self.logger
        else:
            self.TrigOPC = None
            self.gitter = 0
    def setLogger(self,logger):
        self.logger = logger
        if isinstance(self.TrigOPC, AlgData_OPC):
            self.TrigOPC.logger = logger
    def isSync(self):
        if self.DT < 2:
            return True
        return False
    def isJobAlife(self):
        #implement a method to return the life state of the scheduled job.
        if self.job == None or self.job.next_run_time == None:
            return False
        else:
            return True
    def updateTrigParam(self,S0_tUpdate=None):
        if S0_tUpdate:
            self.S0_tUpdate = S0_tUpdate
        if not self._testmode:
            self.lastDT = self.DT
            self.DT = max(1,self.DT/2)
    def getMaxRuns(self):
        if self.lastT:
            return 2*self.lastDT/self.DT + 2*self.gitter/self.DT + 1
        else:
            return self.S0_tUpdate / self.DT + 1
    def getNextRT(self):
        if self.lastT:
            NextT = self.lastT + timedelta(seconds=self.S0_tUpdate-2*self.lastDT-self.gitter)
        else:
            NextT = datetime.now() + timedelta(seconds=1)
        return NextT
    def waitForTrigg(self,actif):
        self._waitForTrigger = actif
    def getRTrigJob(self):
        if self.TrigOPC:
            return self._getRTrigOPC()
        elif self._testmode == True:
            return self._getRTrigTest()
        else:
            return self._getRTrig()
    def _getRTrig(self):
        if self._waitForTrigger == True:
            self.lastT = datetime.now()
            return True
        return False

    def _getRTrigTest(self):
        self.jobRuns += 1
        self.logger.debug( "ReadTriggerJob Executed: %s at %s" % (self.jobRuns, datetime.now()) )
        if self.jobRuns < 3:
            return False
        else:
            self.lastT = datetime.now()
            return True
    def _getRTrigOPC(self):
        self.TrigOPC.readOPC()
        S0TrigOPC = self.TrigOPC.opcVarsDict["VictoryClient.S0_tUpdateTrig"]
        if S0TrigOPC.quality == "Good":
            S0_tUpdateTrig = S0TrigOPC.value
            S0_tUpdateTrigOld = S0TrigOPC.getCached("Latest")[1]
            # Only the positive slope is of importance.
            try:
                slop = S0_tUpdateTrig - S0_tUpdateTrigOld
            except:
                slop = 0

            if slop > 0:
                self.lastT = S0TrigOPC.dtLoc
                return True
            else:
                return False
        else:
            return False


class WriteTrigger(object):
    TrigSizePct = ReadTrigger.TrigSizePct
    maxRuns = 3
    def __init__(self, tobeTriggered, tobeReseted = None, S0_tUpdate = 900, opcserver='CoDeSys.OPC.02', test = False):
        self.logger = logging.getLogger("TriggerHandling.WriteTrigger")
        self.S0_tUpdate = S0_tUpdate
        self.DT = max(1, self.S0_tUpdate * self.TrigSizePct/100) # should be multiple of second >= 1[sec]
        self.job = None
        self.run = 0
        self._state = ['Init',]
        variables = {'OPC_Group':'GPCTriggerVariables' }
        for ti in tobeTriggered:
            sti,vti = ti.split(':.')
            variables[sti] = [vi for vi in GPCOutVars[sti] if vi['GPC'].startswith('Qout')]
        self.TrigOPC = AlgData_OPC(variables = variables, opcserver = opcserver)
        self.TrigOPC.logger = self.logger
        self.TrigVState = dict([(vi,'Init') for vi in self.TrigOPC.gpcVars if re.match(".*QoutTrig$", vi)])
        self.tobeReseted = tobeReseted
        if tobeReseted not in [None, []]:
            variables = {'OPC_Group':'GPCResetVariables' }
            OPC_Stations = dict([list(reversed(sti)) for sti in GPC_Stations.items()])
            for ti in tobeReseted:
                sti,vti = ti.split(':') # tobeReseted uses the GPC internal variable names separated by ":" only.
                sti = OPC_Stations[sti] # need to use the OPC-station name
                substi = sti
                if sti in ['U1111', 'U1112']:
                    sti = 'U1110'
                stiOPC = substi[0]+'_'+substi[1:]
                variables[sti] = [vi for vi in GPCOutVars[sti] if vi['GPC'] == vti and vi['OPC'].startswith(stiOPC)]
            self.ResetTrigOPC = AlgData_OPC(variables = variables, opcserver = opcserver)
            self.ResetTrigOPC.readOPC()

    def setLogger(self,logger):
        self.logger = logger
        self.TrigOPC.logger = logger
    def isJobAlife(self):
        #return the life state of the scheduled job.
        if self.job == None or self.job.next_run_time == None:
            return False
        else:
            return True
    def _setAllTrigers(self):
        self.resetFirst = []
        for vti in self.TrigVState.keys():
            TrigOPC = self.TrigOPC.opcVarsDict[vti]

            if TrigOPC.value == 0 and self.TrigVState[vti] == 'Init':
                ## GSc-ToDo: Use the write-variable state machine here to avoid local var-state self.TrigVState.
                if not TrigOPC.isWPending():
                    TrigOPC.setWriteValue(1)
            elif TrigOPC.value == 1 and self.TrigVState[vti] == 'Set':
                pass
            else:
                self.logger.error("GPC WriteTrigger: %s was not reset correctly (state: %s). Try to Reset trigger first" % (TrigOPC.name,self._state))
                ## GSc-ToDo: can not be left in this state because further algo control actions become impossible.
                self.resetFirst.append(vti)
                TrigOPC.setWriteValue(0)

    def _resetAllTrigers(self):
        for vti in self.TrigVState.keys():
            TrigOPC = self.TrigOPC.opcVarsDict[vti]

            if TrigOPC.value == 1 and self.TrigVState[vti] == 'Set':
                ## GSc-ToDo: Use the write-variable state machine here to avoid local var-state self.TrigVState.
                if not TrigOPC.isWPending():
                    TrigOPC.setWriteValue(0)
            elif TrigOPC.value == 0 and self.TrigVState[vti] == 'Reset':
                pass
            else:
                self.logger.error("GPC WriteTrigger: %s was not correctly set (state: %s)." % (TrigOPC.name,self._state))
        if self.tobeReseted not in [None, []]:
            for vi in self.ResetTrigOPC.opcVarsDict.values():
                vi.setWriteValue(0)

    def _handleOPC(self,state):
        try:
            # Write the triggers out.
            if state == 'Reset' and self.tobeReseted not in [None, []]:
                WStatusTBR = self.ResetTrigOPC.writeOPC(allStored=True, toOPC=True)
            WStatus = self.TrigOPC.writeOPC(allStored=True, toOPC=True)
            if WStatus in [True, None, []]:
                self.logger.error("OPCWriteError: writeOPC returns: %s" % (WStatus,))
                return
            nbrW = len(WStatus)
            opcResDict = dict([(ri[0],ri[1] == "Success") for ri in WStatus])
            tfSuccess = opcResDict.values()
            for opcvi,tfi in opcResDict.iteritems():
                if not tfi: continue
                vti = self.TrigOPC.opcVMap[opcvi]
                if vti not in self.resetFirst:
                    self.TrigVState[vti] = state

            if not all(tfSuccess):
                # not all triggers set/reset - handle the one set/reset an continue if possible.
                nbrErr = nbrW - sum(tfSuccess)
                if self.run > self.maxRuns:
                    self.state = "%sError" % (state,)
                    self.logger.warning( "%s OPC-Write ends with state %s" % ("GPC WriteTrigger:", WStatus) )
            else:
                if self.resetFirst == []:
                    # All triggers are successful set/reset.
                    self.state = state
                    self.run = 0
                    self.logger.info( "%s %s done for: %s" % \
                                      ("GPC WriteTrigger", state, opcResDict.keys()) )
                else:
                    k = set(opcResDict.keys())
                    krf = set([self.TrigOPC.opcVMap[opcvi] for opcvi in self.resetFirst])
                    self.logger.info( "ResetFist done for: %s" % \
                                      (list(krf & k),) )
                    self.logger.info( "%s %s done for: %s" % \
                                      ("GPC WriteTrigger", state, list(k-krf)) )
                return
        except StandardError as e:
            self.state = "Error"
            self.logger.error("StandardError: %s",e)

    def setTrigOPC(self):
        self.TrigOPC.readOPC()
        self._setAllTrigers()
        self._handleOPC('Set')
        self.run +=1
    def resetTrigOPC(self):
        self.TrigOPC.readOPC()
        self._resetAllTrigers()
        self._handleOPC('Reset')
        self.run +=1
    def isInProcess(self):
        if self.state in ['Init','Set']:
            return True
        return False
    @property
    def state(self):
        return self._state[0]
    @state.setter
    def state(self,value):
        return self._state.insert(0,value)
    def process(self):
        cState = self.state
        if cState == 'Init':
            self.setTrigOPC()
        elif cState == 'Set':
            self.resetTrigOPC()
        elif cState == 'Reset':
            pass
        else:
            self.logger.error("Error in GPC-WriteTrigger: current state %s !\n -> State history: %s", self._state[0], self._state)
