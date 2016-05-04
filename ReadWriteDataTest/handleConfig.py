# -*- coding: utf-8 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

from JobScheduler.JobManagement_GSc import jobNormal
from os import path
import time
import logging
from collections import namedtuple
from configobj import ConfigObj
from validate import Validator


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

h = NullHandler()
logging.getLogger("handleConfig").addHandler(h)

def readGPCConfig(confF):
    """Uses ConfigObj to read and validate the specified config file"""
    cval = False
    p,f = path.split(confF)
    r,e = path.splitext(f)
    specF = path.join(p,r+'.spec')
    if path.exists(specF):
        cspec = ConfigObj(specF,list_values=False)
        c = ConfigObj(confF, configspec=cspec)
        cval = c.validate(Validator())
    else:
        c = ConfigObj(confF, configspec=cspec)
    return c,cval

class readConfigJob(jobNormal):
    confFileType = namedtuple('confFile','path mtime rtime')
    def __init__(self,jobId,cxt):
        jobNormal.__init__(self,jobId)
        self.cxt = cxt
        self.sleep = None
        self.confFile = None
        self.cxt.configJob = self
        self.newConfFile = None
        self.logger = logging.getLogger("handleConfig.readConfigJob")

    def Error(self,fsm):
        self.logger.error( "%s: in Error", self.logHeader())
    def doPrep(self,fsm):
        self.logger.debug( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        self.checkConfig()
    def doRun(self,fsm):
        self.logger.info( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        self.confFile = self.confFileType(path=self.newConfFile,
                                          mtime=path.getmtime(self.newConfFile),
                                          rtime=None)
        self.newConfFile = None
        self.getConfig()
    def doCheckPending(self,fsm):
        self.logger.info( "%s runs in State %s" % (self.logHeader(), fsm.current_state) )
        self.checkConfig()
        if not self.newConfFile == None:
            self.sleep = None
    def doPending(self,fsm):
        self.logger.debug( "%s in transit to %s" % (self.logHeader(), fsm.next_state) )
    def doResume(self,fsm):
        self.logger.debug( "%s in transit to %s" % (self.logHeader(), fsm.next_state) )
    def isDone(self,fsm):
        return False
    def tobePending(self,fsm):
        if self.newConfFile == None:
            try:
                self.sleep = self.cxt.S0_tUpdate
            except AttributeError:
                self.sleep = 10
            return True
        return False
    def tobeResumed(self,fsm):
        if not self.newConfFile == None:
            self.sleep = None
            return True
        return False

    def checkConfig(self):
        if path.exists(self.cxt.configFile):
            try:
                if self.confFile.path != self.cxt.configFile or\
                   self.confFile.mtime != path.getmtime(self.cxt.configFile):
                    self.newConfFile = self.cxt.configFile
                else:
                    pass
            except AttributeError:
                self.newConfFile = self.cxt.configFile
        else:
            pass
    def getConfig(self):
        self.logger.debug( "%s read configFile [%s]" % (self.logHeader(), self.confFile.path) )
        GPCConf = readGPCConfig(self.confFile.path)
        self.cxt.doUpdateConfig(GPCConf)
        self.confFile = self.confFile._replace(rtime=time.time())
        self.logger.debug( "%s configTree [%s]; configValid [%s]" % (self.logHeader(), GPCConf[0],GPCConf[1]) )
    def isConfigRead(self):
        try:
            if self.confFile.rtime:
                return True
            return False
        except AttributeError:
            return False

