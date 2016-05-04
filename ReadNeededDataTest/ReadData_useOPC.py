""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """


from apscheduler.scheduler import Scheduler
from datetime import datetime, timedelta
from time import sleep
import logging
import logging.handlers

import OpenOPC

if __name__ == '__main__':
    import sys, os
    sys.path[0:0] = [os.path.split(os.path.abspath(os.path.curdir))[0:1][0],]

    #print sys.path

from utilities.opcVarHandling import opcVar
from Control.GPCVariablesConfig import GPC_VarsSpec, GPC_Stations

class AlgData_OPC(object):

    Variables = {'OPC_Group':'GPCSysVariables' }
    Variables.update(GPC_VarsSpec)
    writeLockLimit = 10
    TimeoutErrorLimit = 15

    def __init__(self, opcserver='CoDeSys.OPC.02',
                 variables = None, opcclient_name = None):
        if variables != None:
            if isinstance(variables,(list,tuple)):
                #Group is missing
                variables = {'DummyGPCAlgGroupX':variables}
            self.Variables = variables
        if opcclient_name == None:
            opcclient_name = '.'.join(['OPCClient',self.Variables.keys()[0]])
        self._init_OPC(opcserver=opcserver, opcclientName=opcclient_name)
        self.logger = logging.getLogger('opcVarsData')


    def _init_OPC(self, opcserver='CoDeSys.OPC.02', opcclientName='OPCClient.GPCSys'):
        try:
            # opc client instance can not be stored here as this will be run in the main thread during initialisation.
            # opc connection will faile later if run from the scheduler job (which will be in an other thread)
            opc = OpenOPC.client()
        except:
            raise ValueError('OPC-Client could not be instantiated')
        if opcserver in opc.servers():
            self.opcServer = opcserver
            try:
                opc.connect(self.opcServer)
            except:
                raise ValueError('OPC-Server: "%s" could not be connected'%(self.opcServer,))
            if self.Variables.has_key('OPC_Group'):
                opcGrp = self.Variables['OPC_Group']
                opcVMap = {}
                opcVars = set()
                opcServVars = set()
                for sti in self.Variables.keys():
                    if sti in ["OPC_Group",]: continue
                    stg = lambda  vi: ''.join(vi.split('_',2)[:2])
                    vmapi = dict([(sti+':.'+vi['OPC'],GPC_Stations[stg(vi['OPC'])]+':'+vi['GPC']) for vi in self.Variables[sti]])
                    opcVMap.update(vmapi)
                    opcVars.update(vmapi.keys())
                    opcServVars.update(opc.list(sti+"*", flat=True))
                opcVMap.update(dict([reversed(i) for i in opcVMap.items()]))
            else:
                opcGrp = self.Variables.keys()[0]
                opcVars = set([opcGrp+':.'+vi for vi in self.Variables[opcGrp]])
                opcServVars = set(opc.list(opcGrp+"*", flat=True))
            if opcVars <= opcServVars:
                self.opcGrp = opcGrp
                self.opcVars = opcVars
                self.opcVarsDict = dict()
                try: #only if variable mapping available store it
                    self.opcVMap = opcVMap
                    self.gpcVars = [opcVMap[vi] for vi in opcVars]
                except:
                    self.gpcVars = self.opcVars
            else:
                raise ValueError('Not all needed Variables are listed by the OPC Server\n missing: %s' % (opcVars - opcServVars,))
            self.opcclientName = opcclientName
            self.readLock = False
            self.writeLock = False
            self.connTrys = 0
            self.connMaxTrys = 3 #Could come from config
            opc.close()
        else:
            raise ValueError('OPC Server is not accessible: %s' % opcserver)

    def _connect_OPC(self):
        try:
            self.opc
        except AttributeError:
            # opc client instance can now be stored as this is done within the job thread.
            # later cals will be issued from the same thread.
            try:
                self.opc = OpenOPC.client(client_name=self.opcclientName)
            except OpenOPC.OPCError as e:
                raise ValueError('OpenOPC.OPCError: %s\n Error during OPC client instantiation' % e)
        try:
            self.opc.info() #This raises an exception if the OPC-Server is not connected.
            conn = True
        except:
            conn = False
        if not conn:
            self.opc.connect(self.opcServer)
            sleep(0.3) #To be sure connection is done on OPC server side.

    def _close_OPC(self):
        self.opc.close()
        sleep(0.5) #To be sure disconnection is done on OPC server side.

    def readOPC(self,opcVars=None,_recN=0):
        #_recN = current recursion call number so do not use on initial call.
        if self.writeLock: #Do not read during write process is active.
            sleep(0.5)
            if _recN > self.writeLockLimit:
                return ("VarsError","ReadOPC reached the 'writeLock' recursion limit (10) -> give up (see log)")
            return self.readOPC(opcVars=opcVars,_recN=_recN+1) # recursive call.
        self.readLock = True
        try:
            for connTrys in xrange(self.connMaxTrys):
                try:
                    self._connect_OPC()
                    break
                except OpenOPC.OPCError as e:
                    self._close_OPC()
                    self.logger.debug("OpenOPC.OPCError: %s\n -> retry" % e)
                    sleep(0.5)
            else:
                self.logger.debug("OpenOPC.OPCError: %s\n -> give up" % e)
                return ("VarsError","OpenOPC.OPCError  -> give up (see log)")

            try:
                if opcVars == None:
                    opcVars = list(self.opcVars)
                opcIn = self.opc.read(opcVars)
                self.opc.close()
            except OpenOPC.TimeoutError as e:
                self.logger.debug("AlgData_OPC.readOPC() - (%s): OpenOPC.TimeoutError (%s): %s\n -> try again" % (datetime.now(), _recN, e))
                self._close_OPC()
                sleep(0.5)
                if _recN > self.TimeoutErrorLimit:
                    return ("VarsError","ReadOPC reached the 'TimeoutError' recursion limit (15) -> give up (see log)")
                return self.readOPC(opcVars=opcVars,_recN=_recN+1)
            except OpenOPC.OPCError as e:
                self._close_OPC()
                if e.message.split(":")[0].strip() == "Connect":
                    self.logger.debug("OpenOPC.OPCError: %s" % e)
                    return ("VarsError","OpenOPC.OPCError on Connection level (see log)")
                else:
                    self.logger.debug("OpenOPC.OPCError: %s\n -> opcIn set to (name,None,Bad,utcnow)" % e)
                    dt = datetime.utcnow().replace(microsecond = 0).isoformat(' ')
                    opcIn = [(vi,None,'Bad',dt) for vi in opcVars]
        finally:
            self.readLock = False

        for oi in opcIn:
            self.logger.debug( "ReadIn from OPC - (%s)" % (oi,) )
            try:
                key = self.opcVMap[oi[0]]
            except AttributeError:
                key = oi[0]
            if key in self.opcVarsDict:
                self.opcVarsDict[key].setValue(*oi)
            else:
                self.opcVarsDict[key] = opcVar(*oi)

    def writeOPC(self, tagValuePairs=None, allStored=False, toOPC=False):
        if tagValuePairs == None and allStored == False:
            return None
        if isinstance(tagValuePairs, (list, tuple)) and \
           not isinstance(tagValuePairs[0], (list, tuple)):
            tagValuePairs = [tagValuePairs,]
        elif tagValuePairs == None:
            tagValuePairs = [] #Change to empty list, important for the for loop

        opcVars = []
        for pi in tagValuePairs:
            try:
                key = self.opcVMap[pi[0]]
            except AttributeError:
                key = pi[0]
            try:
                vi = self.opcVarsDict[key]
                if vi.setWriteValue(pi[1]) != None:
                    opcVars.append(vi)
            except KeyError, e:
                self.logger.debug("Unknown OPC-Variable: %s\n KeyError: %s" % (key,e))
        if allStored:
            opcVars = self.getWritableVars()
            toOPC = True #otherwise allStored does not make any sense.

        if toOPC:
            return self._writeToOPC(opcVars)
        else:
            return True

    def getWritableVars(self,gpcVars=None):
        if gpcVars == None:
            gpcVars = list(self.gpcVars)
        wVars = [self.opcVarsDict[vi] for vi in gpcVars if self.opcVarsDict.get(vi,None) and self.opcVarsDict[vi].isWReady()]
        return wVars

    def _writeToOPC(self,gpcVars):
        WStatus = None
        if gpcVars == None or len(gpcVars) == 0:
            return []
        if self.writeLock or self.readLock:
            sleep(0.5)
            return self._writeToOPC(gpcVars)
        else:
            self.writeLock = True

        try:
            opcTVPairs = []
            for pi in gpcVars:
                #vi = self.opcVarsDict[pi]
                opcTVPairs.append(pi.wvalue)
            try:
                self._connect_OPC()
                WStatus = self.opc.write(opcTVPairs)
                sleep(0.8)
                self._close_OPC()
                for i,vi in enumerate(gpcVars):
                    #WStatus is specific per Variable -> tuple (name, status) per variable.
                    if WStatus[i][1] == "Success":
                        vi.Write(True)
                    else:
                        vi.Write(False)
            except OpenOPC.OPCError as e:
                self.logger.debug("OPCError: %s",e)
                sleep(1)
                self._close_OPC()
                for vi in gpcVars:
                    vi.Write(False)
        finally:
            self.writeLock = False
        return WStatus

    def isWAllIdle(self,gpcVars=None):
        if gpcVars == None:
            gpcVars = list(self.gpcVars)
        wVars = [self.opcVarsDict[vi].isIdle() for vi in gpcVars if self.opcVarsDict.get(vi,False) and self.opcVarsDict[vi].isWritable()]
        if all(wVars):
            return True
        return False
    def isWAnyProblem(self,gpcVars=None):
        if gpcVars == None:
            gpcVars = list(self.gpcVars)
        wVars = [self.opcVarsDict[vi] for vi in gpcVars if self.opcVarsDict.get(vi,None) and self.opcVarsDict[vi].isProblem()]
        if wVars == []:
            return False
        return True

    def process(self):
        """This method is to be used by the overall runtime routines (Scheduler)"""
        # Build Info for debugging/logging purpose
        #to be redirected to logging system in order to keep this in a file

        self.readOPC()
        for ki, vi in self.opcVarsDict.iteritems():
            self.logger.info('"%s";"%s";"%s"' % (vi.name,vi.time,vi.value))


if __name__ == '__main__':
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    #== Setup logger for the apscheduler module
    schedlogRF = logging.handlers.RotatingFileHandler(
                    filename='apscheduler.log', mode='a',
                    backupCount=5, maxBytes=100000 )
    schedlogRF.setLevel(logging.DEBUG)
    schedlogRF.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logging.getLogger("apscheduler").addHandler(ch)
    logging.getLogger("apscheduler").addHandler(schedlogRF)

    #== Setup logger for the opcVarFSM module
    opcVarlogRF = logging.handlers.RotatingFileHandler(
                    filename='opcVarFSM.log', mode='a',
                    backupCount=5, maxBytes=100000 )
    opcVarlogRF.setLevel(logging.DEBUG)
    opcVarlogRF.setFormatter(formatter)
    opcLogger = logging.getLogger("opcVarFSM")
    opcLogger.setLevel(logging.INFO)
    opcLogger.addHandler(ch)
    opcLogger.addHandler(opcVarlogRF)

    #== Setup logger for the opcVarFSM module
    opcVarDataRF = logging.handlers.RotatingFileHandler(
                    filename='opcVars.dat', mode='a',
                    backupCount=20, maxBytes=5000000 )
    opcVarDataRF.setLevel(logging.DEBUG)
    opcLogger = logging.getLogger("opcVarsData")
    opcLogger.setLevel(logging.INFO)
    opcLogger.addHandler(opcVarDataRF)

    # Instantiate the finite state machine for system state following
    sm = AlgData_OPC(opcclient_name="GPC_Read.OPCClient",
                     # opcserver='OPCManager.DA.XML-DA.Server.DA', ## Only for local (CRP simulation tests)
                     )

    # Instantiate scheduler
    sched = Scheduler()
    d = datetime.now() + timedelta( seconds = 1 )
    BZx = sched.add_interval_job( sm.process,
                                  start_date=d,
                                  seconds=10*60,
                                  #max_runs=10,
                                  #args=[aFSM.fsm,]
                                 )

    # Start the scheduler
    sched.start()

    while sched.get_jobs() != []:
        print "%s While Loop - alive" % datetime.now()
        sleep(2*60)
    else:
        print "Scheduler goes down"
        sched.shutdown(wait=False)
        logging.shutdown()
        print "Scheduler has shutdowned"
