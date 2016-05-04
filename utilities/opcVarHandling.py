# -*- coding: utf-8 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

from dateutil import tz, parser
from datetime import datetime
from collections import deque, namedtuple
import opcVarFSM

from Control.GPCVariablesConfig import OPCVarSpecif


class opcVar(object):

    class opcVarData():
        def __init__(self, value, quality, time):
            self.value = value
            self.quality = quality
            self.time = time
            try:
                self.dt = parser.parse(time).replace(tzinfo=tz.tzutc()) #time is supposed to be in UTC.
            except AttributeError as e:
                self.dt = None
                #GScToDo here a logging would be helpfill because the print will probably be lost.
                print "Not handled time format in opcVarData: %s" %(e,)

    class opcVarWriteData():
        def __init__(self, value, dt):
            self.value = value
            if isinstance(dt,str):
                dt = parser.parse(dt)
            if isinstance(dt, datetime):
                dt = dt.replace(microsecond = 0)
                if dt.tzinfo == None:
                    dt = dt.replace(tzinfo=tz.tzutc())
                else:
                    dt = dt.astimezone(tz.tzutc())
            else:
                raise ValueError("Unhandled Datetime format")
            self.dt = dt
    def __init__(self, name, value, quality, time):
        self.name = name
        self.cach = deque( maxlen = 4 ) # GScToDo: maxlen could be a variable specific parameter
        self.fsm = opcVarFSM.opcVarFSM(name) # GScToDo: ccountMax of FSM could be set here based on config
        try:
            if OPCVarSpecif[name]['Access'] == 'rw':
                self.fsmW = opcVarFSM.opcVarWFSM(name) # GScToDo: cWErrorMax of FSM could be set here based on config
        except KeyError:
            pass
        try:
            NK = float(OPCVarSpecif[name]['NK'])
        except KeyError:
            NK = 0
        self.convNK = 1/10**NK
        self.setValue(name, value, quality, time)

    def _reset(self):
        self.fsm.event_Reset()

    def setValue(self, name, value, quality, time):
        if name != self.name:
            raise NameError("Provided variable name (%s) does not match opcVar.name (%s)" % (name,self.name))
        if isinstance(value, (int,long)):
            value *= self.convNK
        if quality != 'Good':
            self.bad = self.opcVarData(value, quality, time)
            self.fsm.event_RBad()
        else:
            self.cach.appendleft(self.opcVarData(value, quality, time))
            self.fsm.event_RGood()

    def isWritable(self):
        try:
            self.fsmW
            return True
        except:
            return False
    def isWReady(self):
        if self.isWritable() and \
           self.fsmW.WriteState.name() in ["ToWrite","WritePending"]:
            return True
        return False
    def isWPending(self):
        if self.isWritable() and \
           self.fsmW.WriteState.name() == "WritePending":
            return True
        return False
    def isIdle(self):
        if self.isWritable() and \
           self.fsmW.WriteState.name() == "Idle":
            return True
        return False
    def isProblem(self):
        if self.isWritable() and \
           self.fsmW.WriteState.name() == "Problem":
            return True
        elif self.fsm.QualityState.name() == "Problem":
            return True
        return False
    def setWriteValue(self,value,dt=None,ImplicitTrig=False):
        if not self.isWritable(): return
        if dt == None: dt = datetime.utcnow()
        self.fsmW.event_NData(self.opcVarWriteData(value,dt))
        if ImplicitTrig and self.fsmW.WriteState.name() == "ToWrite":
            self.fsmW.event_WTrig()
        return self.wvalue
    def Write(self,success):
        if not self.isWReady(): return
        if self.fsmW.WriteState.name() == "ToWrite":
            self.fsmW.event_WTrig()
        if success == True:
            data = self.fsmW.event_WOK()
            self.setValue(self.name, data.value, 'Good', data.dt.strftime("%m/%d/%y %H:%M:%S"))
        else:
            self.fsmW.event_WError()

    @property
    def wvalue(self):
        try:
            if self.isWReady():
                #GSc-ToDo: conversion to target (OPC) datatype (int/float, ...)
                #          How could this be managed for each variable independently.
                return (self.name, self.fsmW.data.value/self.convNK)
            return None
        except:
            return

    @property
    def value(self):
        try:
            if self.fsm.QualityState.name() == "UptoDate":
                return self.cach[0].value
            elif self.fsm.QualityState.name() == "FromCach":
                #GScToDo: Implement some basic treatments.
                return self.cach[0].value
            else:
                return None
        except IndexError:
            return None
    @property
    def time(self):
        try:
            return self.cach[0].time
        except IndexError:
            return None
    @property
    def dt(self):
        try:
            return self.cach[0].dt
        except IndexError:
            return None
    @property
    def dtLoc(self):
        try:
            return self.dt.astimezone(tz.tzlocal())
        except IndexError:
            return None
    @property
    def usable(self):
        if self.fsm.QualityState.name() in ["UptoDate","FromCach"]:
            return True
        return False
    @property
    def quality(self):
        if self.fsm.QualityState.name() == "UptoDate":
            return "Good"
        elif self.fsm.QualityState.name() == "FromCach":
            return "Usable"
        else:
            return "Bad"
    def getCached(self,func=None):
        ret = namedtuple('OPCVarCached', ['Name','Value','Time','DateTime'])
        if func == None:
            return ret(self.name, self.value, self.time, self.dt)
        elif func == "Latest":
            try:
                c = self.cach[1]
                return ret(self.name, c.value, c.time, c.dt)
            except IndexError:
                return ret(self.name, None, None, None)
        elif func == "All":
            return self.cach
    def getWCach(self):
        if self.fsmW.wcash:
            return self.fsmW.CData
        return None
    def getDiff(self):
        if len(self.cach) <= 1:
            return None
        ret = namedtuple('OPCVarDiffs', ['Name','Diff','DateTime','LocalDT','TimeDiff'])
        ret = ret(self.name,[],self.dt,self.dtLoc,[])
        it = iter(self.cach)
        a = it.next()
        for b in it:
            ret.Diff.append(a.value-b.value)
            ret.TimeDiff.append(a.dt-b.dt)
            a = b
        return ret
