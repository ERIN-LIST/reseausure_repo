""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

if __name__ == '__main__':
    import config

import logging
from time import sleep, time
from collections import deque

from JobScheduler.JobManagement_GSc import jobManagement, jobNormal
from ReadNeededDataTest.ReadData_useOPC import AlgData_OPC
from handleConfig import readGPCConfig
from Control.GPCVariablesConfig import GPCStateVars

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

h = NullHandler()
logging.getLogger("handleLifeCounter").addHandler(h)


class MPCzLifeJob(jobNormal):
    '''
    This class builds the job that handles the MPC life counter.
    This counter needs to be updated on OPC-Server level at regular bases
    '''
    zLifeVN = ""
    Variables = {'OPC_Group':'GPCLifeVariables' }
    for sti,vars in GPCStateVars.iteritems():
        Variables[sti] = filter(lambda x: x['GPC']=="GPCLife", vars)
    _lenTSs = 5

    def __init__(self,jobId,cxt):
        jobNormal.__init__(self,jobId)
        self.cxt = cxt
        self.sleep = None
        self.nextTS = None
        self._nextTSs = deque([],maxlen=self._lenTSs)
        self.runCnt = 0
        self.GPC_zLife = 0
        self.logger = logging.getLogger("handleLifeCounter.MPCzLifeJob")
    def _init_OPC(self, opcclientName='OPCClient.GPCLife'):
        opcserver = self.cxt.config["Tree"]["Global"]["OPCServer"]
        self.LifeOPC = AlgData_OPC(variables = self.Variables,
                                   opcclient_name = opcclientName,
                                   opcserver = opcserver)
        self.LifeOPC.logger = self.logger
        # Also Initialize the next runtime time steps
        ct = time()
        LCT = self._get_LifeCycle()
        self._nextTSs.clear()
        for i in xrange(self._lenTSs):
            self._nextTSs.append(ct+(i+1)*LCT)
    def _get_LifeCycle(self):
        try:
            LConf = self.cxt.config["Tree"]["GPCLife"]
            sr = self.cxt.S0_tUpdate*LConf['pctGPCSamp']/100
            sleepD = max(sr,LConf['minSampling'])
        except AttributeError:
            sleepD = 10
        return sleepD
    def _setNextTS(self):
        try:
            self.nextTS = self._nextTSs.popleft()
            self._nextTSs.append(self._nextTSs[-1]+self._get_LifeCycle())
        except IndexError:
            # Probably not life yet
            self.sleep = self._get_LifeCycle()
    def Error(self,fsm):
        self.logger.error( "%s: in Error", self.logHeader())
    def doPrep(self,fsm):
        self.logger.debug( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        if self.isGPCLife():
            self._init_OPC()
    def doRun(self,fsm):
        self.logger.debug( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        LData = self.LifeOPC
        LData.readOPC()
        diff = dict([(ki,vi.value == self.GPC_zLife) for ki, vi in LData.opcVarsDict.iteritems()])
        if not all(diff.values()):
            VarNotUpdated = [ki for ki,tf in diff.iteritems() if not tf]
            self.logger.info( "%s last life opc-write process had some issues %s" % \
                              (self.logHeader(), VarNotUpdated) )
        self.GPC_zLife = (self.GPC_zLife+1) % (1<<16)
        LVars = self.fillLifeVars()
        try:
            WStatus = LData.writeOPC(LVars.items(), toOPC=True)
            if len(WStatus) != len(LVars):
                self.logger.warning( "%s OPC Status size different from VarList size (%s, %s)" % (self.logHeader(), len(WStatus), len(LVars)) )
            tfSuccess = [ri[1] == "Success" if (isinstance(ri,tuple) and len(ri) >= 2) \
                         else False for ri in WStatus]
            if not all(tfSuccess):
                self.logger.warning( "%s some un-successful OPC-Writeouts %s" % (self.logHeader(), WStatus) )
            else:
                dt = LData.opcVarsDict[LData.gpcVars[0]].dt
                self.logger.info( "%s (%s) Life counters incremented (%s)" % \
                                  (self.logHeader(), dt, LVars.items()) )
        except StandardError as e:
            self.logger.error("StandardError: %s",e)
        self.runCnt +=1
    def doCheckPending(self,fsm):
        self.logger.info( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        self._setNextTS()
    def doPending(self,fsm):
        self.logger.debug( "%s in transit to %s" % (self.logHeader(), fsm.next_state) )
        self.runCnt = 0
        if self.nextTS == None and self.sleep == None:
            self._setNextTS()
    def doResume(self,fsm):
        self.logger.debug( "%s in transit to %s" % (self.logHeader(), fsm.next_state) )
        try: #Check the initialization of the OPC variables
            self.LifeOPC
        except AttributeError:
            if self.isGPCLife():
                self._init_OPC()
        self.sleep = None
        self.nextTS = None
    def isDone(self,fsm):
        return False
    def tobePending(self,fsm):
        if self.runCnt >= 1:
            return True
        elif getattr(self, "LifeOPC", None) == None:
            self.logger.info( "%s GPC is not aLife", self.logHeader())
            return True
        self.logger.info( "%s GPC is aLife", self.logHeader())
        return False
    def tobeResumed(self,fsm):
        if not self.isGPCLife():
            return False
        elif self.runCnt == 0:
            return True
        return False

    def getGPCState(self):
        gpc = self.cxt
        state=gpc.getFSMState()
        if not state['Trans']:
            return state['State']
        else:
            sleep(0.05)
            return self.getGPCState()

    def isGPCLife(self):
        try:
            gpcState = self.getGPCState()
        except:
            gpcState = "GPCMap.INIT"
        if gpcState in ["GPCMap.getRTrig",
             "GPCMap.readOPCVars",
             "GPCMap.checkSysStates",
             "GPCMap.runMPC",
             "GPCMap.writeOPCVars",]:
            if self.cxt.config["Tree"]["GPCLife"]["toBlank"]:
                return False
            else:
                return True
        return False

    def fillLifeVars(self):
        LData = self.LifeOPC
        sysGPCState = getattr(self.cxt, 'SysGPCState', {})
        d = {}
        for k,v in LData.opcVarsDict.iteritems():
            sti = k.split(':')[0]
            if sysGPCState.get(sti,None) in ['offline',None] and v.quality != 'Good':
                continue
            d[v.name] = self.GPC_zLife
        return d


from random import randint, choice
from utilities.opcVarHandling import opcVar
class dummy():
    def __init__(self):
        self.opcVarsDict = {"U1110:.GPCLife": opcVar("U1110:.U_1110_GPC_Alive",1,'Good','2012-10-01 12:00:00')}
    def readOPC(self,opcVars=None):
        pass
    def writeOPC(self,args):
        return choice(['Success',None,'Error'])
class Context():
    def __init__(self):
        self.S0_tUpdate = 180
        self.MPCInData = dummy()
        GPCConf = readGPCConfig(config.GPCConfFile)
        self.config = dict(zip(("Tree","Valid"),GPCConf))
    def getFSMState(self,trans=False,state="GPCMap.INIT"):
        possible = [[False,"GPCMap.getRTrig"],
                    [True,None],
                    [False,"GPCMap.checkSysStates"],
                    [False,"GPCMap.GPCisOffline"],]
        idx = randint(0,len(possible)-1)

        return dict(zip(['Trans','State'],possible[idx]))
class GPC_jobManagement(jobManagement):
    def __init__(self,cxt):
        jobManagement.__init__(self)
        self.cxt = cxt
    def getPending(self,fsm):
        pass

if __name__ == '__main__':
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logging.getLogger("handleLifeCounter").addHandler(ch)
    logging.getLogger("handleLifeCounter").setLevel(logging.DEBUG)

    sm = Context()
    jM = GPC_jobManagement(None)
    jM.fsm.memory['Buffer'].append([(1,sm),MPCzLifeJob])
    while jM.fsm.current_state != 'END':
        jM.fsm.process(None)
        if jM.fsm.current_state == 'Idle':
            sleep(0.5)

