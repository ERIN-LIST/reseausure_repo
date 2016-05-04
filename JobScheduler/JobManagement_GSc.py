# -*- coding: utf-8 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

from FSM_NS import ObjFSM
from time import time

class jobSimple():
    """
    job class with a simple integrated state machine (INIT - RUN - END).
    """
    def __init__(self,jobId):
        self.id = jobId
        #Specify the state machine states and transitions with conditions and actions
        self.fsm = ObjFSM('INIT', [])
        self.fsm.set_default_transition(self.Error, 'INIT')
        self.fsm.add_transition_any('INIT', None, 'RUN')
        self.fsm.add_transition_any('RUN', self.run, 'END')
        self.fsm.add_transition_any('END', None, 'END')

    def Error(self,fsm):
        print 'J-Error'

    def run(self,fsm):
        print "Simple Job %s runs in State %s" % (self.id,fsm.current_state)

from random import choice
class jobNormal():
    """
    job class with an standard integrated state machine.
    INIT - RUN - RUN - PENDING - RUN - END
    """
    def __init__(self,jobId):
        self.id = jobId
        #Specify the state machine states and transitions with conditions and actions
        self.fsm = ObjFSM('INIT', [])
        self.fsm.set_default_transition(self.Error, 'INIT')
        self.fsm.add_transition_any('INIT', self.doPrep, 'RUN')
        self.fsm.add_transition_any('RUN', self.doRun, 'RUN')
        self.fsm.add_transition(self.isDone, 'RUN', self.doPost, 'END')
        self.fsm.add_transition(self.tobePending, 'RUN', self.doPending, 'PENDING')
        self.fsm.add_transition_any('PENDING', self.doCheckPending, 'PENDING')
        self.fsm.add_transition(self.tobeResumed,'PENDING', self.doResume, 'RUN')
        self.fsm.add_transition_any('END', None, 'END')

    def doRandChoice(self):
        self.rand = choice(['PENDING','RUN','DONE'])
    def Error(self,fsm):
        print 'J-Error'
    def doPrep(self,fsm):
        self.doRandChoice()
    def doRun(self,fsm):
        print "Normal Job %s runs in State %s" % (self.id,fsm.current_state)
        self.doRandChoice()
    def doPost(self,fsm):
        print "Normal Job %s done -> END" % (self.id,)
        pass
    def doCheckPending(self,fsm):
        print "Normal Job %s runs in State %s" % (self.id,fsm.current_state)
        self.doRandChoice()
    def doPending(self,fsm):
        print "Normal Job %s goes to PENDING" % (self.id)
    def doResume(self,fsm):
        print "Normal Job %s resumes from PENDING -> RUN" % (self.id)
    def isDone(self,fsm):
        if self.rand == 'DONE':
            return True
        return False
    def tobePending(self,fsm):
        if self.rand == 'PENDING':
            return True
        return False
    def tobeResumed(self,fsm):
        if self.rand in ['DONE','RUN']:
            return True
        return False
    def logHeader(self):
        try:
            return self.logHeaderStr
        except:
            self.logHeaderStr = "Job %s (ID %s):" % (self.__class__.__name__,self.id)
            return self.logHeaderStr


class jobManagement():
    """
    Class organizing the management of different jobs:
    - insert new jobs to be treated
    - treat the queued jobs until there termination defined by there "END" state.
    """

    jobDict = {'s':jobSimple, 'n':jobNormal}

    def __init__(self):
        #Specify the state machine states and transitions with conditions and actions
        self.fsm = ObjFSM('INIT', memory = {'Queue':[],'Buffer':[],'Sleep':[]})
        self.fsm.set_default_transition(self.Error, 'INIT')
        self.fsm.add_transition_any('INIT', self.getPending, 'CheckPENDING')
        self.fsm.add_transition(self.isSleeping,'CheckPENDING', self.awake,'CheckPENDING')
        self.fsm.add_transition(self.isPending,'CheckPENDING', self.add2queue,'ExecPENDING')
        self.fsm.add_transition(self.isEmpty,'CheckPENDING', None,'Idle')
        self.fsm.add_transition(self.isEnd,'CheckPENDING', None,'END')
        self.fsm.add_transition_any('CheckPENDING', None, 'INIT')
        self.fsm.add_transition(self.getNext,'ExecPENDING', self.runJob,'ExecPENDING')
        self.fsm.add_transition_any('ExecPENDING', None, 'INIT')
        self.fsm.add_transition_any('Idle',None,'INIT')

    def Error(self,fsm):
        print "JM-Error"

    def getPending(self,fsm):
        """
        activity method to get the pending jobs from input or persistent storage.
        """
        inputstr = raw_input ('Enter ID: ')
        if inputstr == '':
            fsm.memory['Buffer'].append('End')
        else:
            for stri in inputstr.split(','):
                stri = stri.split(':')
                if len(stri) == 1:
                    stri.append('s') #Default job-type is "simple"
                if len(stri) == 2:
                    jid,jtype = stri
                else:
                    self.Error(fsm)
                if jid.isalnum() and jtype in ['s','n']:
                    fsm.memory['Buffer'].append([int(jid),self.jobDict[jtype]])
                else:
                    self.Error(fsm)
    def isSleeping(self,fsm):
        if len(self._getSleepingToBeAwaken(fsm)) != 0:
            return True
        return False
    def isPending(self,fsm):
        if len(fsm.memory['Buffer']) != 0 and fsm.memory['Buffer'][0] != 'End':
            return True
        return False
    def isEmpty(self,fsm):
        if len(fsm.memory['Buffer']) == 0:
            return True
        return False
    def isEnd(self,fsm):
        if len(fsm.memory['Buffer']) != 0 and fsm.memory['Buffer'][0] == 'End':
            return True
        return False
    def awake(self,fsm):
        sAwake = self._getSleepingToBeAwaken(fsm)
        for si in sAwake:
            #print "Job %s is awakened" % si['Job']
            fsm.memory['Buffer'].append(si['Job'])
            fsm.memory['Sleep'].remove(si)
    def add2queue(self,fsm):
        endIdx = None
        if fsm.memory['Buffer'][-1] == 'End':
            endIdx = -1
        fsm.memory['Queue'].extend(fsm.memory['Buffer'][0:endIdx])
        fsm.memory['Buffer'][0:endIdx] = []
    def getNext(self,fsm):
        try:
            curr = fsm.memory['Queue'].pop(0)
            fsm.memory['Active'] = curr
            return True
        except IndexError:
            return False
    def runJob(self,fsm):
        j = fsm.memory['Active']
        if not isinstance(j,tuple(self.jobDict.values())):
            if isinstance(j[0], (tuple, list)):
                j = j[1](*j[0])
            else:
                j = j[1](j[0])
        j.fsm.process(None)
        if j.fsm.current_state == 'PENDING':
            if getattr(j, "nextTS", None):
                #print "Job %s goes to sleep" % j
                fsm.memory['Sleep'].append({'Job':j,'Event':j.nextTS})
            elif getattr(j, "sleep", None):
                #print "Job %s goes to sleep" % j
                fsm.memory['Sleep'].append({'Job':j,'Event':time()+j.sleep})
            else:
                fsm.memory['Buffer'].append(j)
        elif j.fsm.current_state != 'END':
            fsm.memory['Queue'].append(j)
    def _getSleepingToBeAwaken(self,fsm):
        tNow = time()
        return [si for si in fsm.memory['Sleep'] if si['Event'] < tNow]


def main():
    jM = jobManagement()
    jmFSM = jM.fsm

    while jmFSM.current_state != 'END':
        jmFSM.process(None)

if __name__ == '__main__':
    main()
