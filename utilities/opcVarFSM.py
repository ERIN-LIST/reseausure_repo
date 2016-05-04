# -*- coding: utf-8 -*-
# State Machine example Program
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

from statedefn import StateTable, event_handler, on_enter_function, on_leave_function
import logging

logger = logging.getLogger(__name__)

class opcVarFSM(object):

    # Quality state table
    qstate = StateTable("QualityState")

    def __init__(self, name, ccountMax = 3, pcountMax = 2):
        # must call init method of class's StateTable object. to initialize state variable
        self.qstate.initialize(self)
        self.mname = name
        self.ccountMax = ccountMax
        self.c_count = 0
        self.pcountMax = pcountMax
        self.p_count = 0

    def _initCCount(self):
        self.c_count = 1
    def _initPCount(self):
        self.p_count = 0

    # Decorate the Event Handler virtual functions -note qstate parameter
    @event_handler(qstate)
    def event_RGood(self): pass
    @event_handler(qstate)
    def event_RBad(self): pass
    @event_handler(qstate)
    def event_Reset(self): pass

    # define methods to handle events.
    ## At UptoDate State
    def _event_RG_UptoDate(self):
        logger.info( "%s: State %s, event RGood" % (self.mname,self.QualityState.name(),) )
    def _event_RB_UptoDate(self):
        self._initCCount()
        logger.error( "%s: State %s, event RBad (%s)" % (self.mname,self.QualityState.name(),self.c_count) )
    ## At FromCach State
    def _event_RG_FromCach(self):
        logger.info( "%s: State %s, event RGood" % (self.mname,self.QualityState.name(),) )
        self.c_count = 0
    def _event_RB_FromCach(self):
        self.c_count += 1
        logger.error( "%s: State %s, event RBad (%s)" % (self.mname,self.QualityState.name(),self.c_count) )
        # Guard implementation
        if self.c_count >= self.ccountMax:
            # initPCount
            self._initPCount()
            # Alarm
            logger.error( "Alarm: RBad counter reached limit (%s)" % self.ccountMax )
            # we decide here we want to go to state Problem, overrrides spec in state table below.
            # transition to next_state is made after the method exits.
            self.QualityState.next_state = self._Problem
    ## for Problem State
    def _event_RG_Problem(self):
        logger.info( "%s: State %s, event RGood" % (self.mname,self.QualityState.name(),) )
        self.p_count += 1
        # Guard implementation
        if self.p_count >= self.pcountMax:
            self.p_count = 0
            # Info
            logger.info( "Info: RGood counter reached limit (%s)" % self.pcountMax )
            # we decide here we want to go to state UptoDate, overrrides spec in state table below.
            # transition to next_state is made after the method exits.
            self.QualityState.next_state = self._UptoDate
    def _event_RB_Problem(self):
        logger.error( "%s: State %s, event RBad (%s)" % (self.mname,self.QualityState.name(),self.c_count) )
        self._initPCount()
    def _event_Reset(self):
        logger.warning( "%s: State %s, event Reset" % (self.mname,self.QualityState.name(),) )
        self.__init__(self.mname)


    # Associate the handlers with a state.
    # First arg is the name of the state.
    # Second argument is a list of methods.  One method for each event_handler decorated function.
    #  Order of methodsin the list correspond to order in which the Event Handlers were declared.
    # Third argument is to be come a list of the next states.
    # The first state created becomes the initial state.
    _UptoDate = qstate.state( "UptoDate",
                              (_event_RG_UptoDate, _event_RB_UptoDate, _event_Reset),
                              (None, "FromCach", None) )
    _FromCach = qstate.state( "FromCach",
                              (_event_RG_FromCach, _event_RB_FromCach, _event_Reset),
                              ("UptoDate", None, "UptoDate") )
    _Problem = qstate.state( "Problem",
                             (_event_RG_Problem, _event_RB_Problem, _event_Reset),
                             (None, None, "UptoDate") )


    # Declare a function that will be called when entering or leaving a qstate.
    @on_enter_function(qstate)
    def _enter_qstate(self):
        logger.info( "entering state %s of %s" % (self.QualityState.name(), self.mname) )
    @on_leave_function(qstate)
    def _leave_qstate(self):
        logger.info( "leaving state %s of %s" % (self.QualityState.name(), self.mname) )


class opcVarWFSM(object):
    # WriteOut state table
    wstate = StateTable("WriteState")

    def __init__(self, name, cWErrorMax = 3):
        # must call init method of class's StateTable object. to initialize state variable
        self.wstate.initialize(self)
        self.mname = name
        self.cWErrorMax = cWErrorMax
        self.wcash = False
        self.cWError = 0
        self.data = None

    # Decorate the Event Handler virtual functions -note wstate parameter
    @event_handler(wstate)
    def event_NData(self,data): pass
    @event_handler(wstate)
    def event_WTrig(self): pass
    @event_handler(wstate)
    def event_WOK(self): pass
    @event_handler(wstate)
    def event_WError(self): pass
    @event_handler(wstate)
    def event_Reset(self): pass

    # define methods to handle events.
    ## At Idle State
    def _event_NData_Idle(self,data):
        logger.info( "%s: State %s, event New Data" % (self.mname,self.WriteState.name(),) )
        self.data = data
    ## At ToWrite State
    def _event_NData_ToWrite(self,data):
        logger.info( "%s: State %s, event New Data\n -> Variable is overwritten (Old: %s -> New: %s)" % \
                     (self.mname,self.WriteState.name(),self.data,data) )
        self.data = data
    def _event_WTrig_ToWrite(self):
        logger.info( "%s: State %s, event Write Trigger" % (self.mname,self.WriteState.name()) )
    ## At WritePending State
    def _event_NData_WritePending(self,data):
        logger.info( "%s: State %s, event New Data" % (self.mname,self.WriteState.name()) )
        if self.wcash:
            logger.info( " -> Cash is overwritten (Old: %s -> New: %s)" % \
                         (self.CData,data) )
        self.wcash = True
        self.CData = data
    def _event_WError_WritePending(self):
        self.cWError += 1
        logger.error( "%s: State %s, event Write Error (%s)" % (self.mname,self.WriteState.name(),self.cWError) )
        if self.cWError < self.cWErrorMax:
            self.WriteState.next_state = self._WritePending
        else:
            self.cWError = 0
    def _event_WOK_WritePending(self):
        logger.info( "%s: State %s, event Write OK" % (self.mname,self.WriteState.name()) )
        self.cWError = 0
        ret = self.data
        # Guard implementation
        if self.wcash:
            # transition to next_state is made after the method exits.
            self.WriteState.next_state = self._ToWrite
            self.wcash = False
            self.data = self.CData
        else:
            self.data = None
        return ret
    ## for any State
    def _event_NData(self,data):
        logger.info( "%s: State %s, event New Data, !!Data is lost!!" % (self.mname,self.WriteState.name(),) )
    def _event_WTrig(self): pass
    def _event_WOK(self): pass
    def _event_WError(self): pass
    def _event_Reset(self):
        logger.info( "%s: State %s, event Reset" % (self.mname,self.WriteState.name(),) )
        self.__init__(self.mname)

    # Associate the handlers with a state.
    # - First arg is the name of the state.
    # - Second argument is a list of methods.  One method for each event_handler decorated function.
    #   Order of methods in the list correspond to order in which the Event Handlers were declared.
    # - Third argument is a list of the next states in the same order as for the methods.
    # The first state created becomes the initial state.
    _Idle = wstate.state( "Idle",
                          (_event_NData_Idle, _event_WTrig, _event_WOK, _event_WError, _event_Reset),
                          ("ToWrite", None, None, None, None) )
    _ToWrite = wstate.state( "ToWrite",
                             (_event_NData_ToWrite, _event_WTrig_ToWrite, _event_WOK, _event_WError, _event_Reset),
                             (None, "WritePending", None, None, "Idle") )
    _WritePending = wstate.state( "WritePending",
                                  (_event_NData_WritePending, _event_WTrig, _event_WOK_WritePending, _event_WError_WritePending, _event_Reset),
                                  (None, None, "Idle", "Problem", "Idle") )
    _Problem = wstate.state( "Problem",
                             (_event_NData, _event_WTrig, _event_WOK, _event_WError, _event_Reset),
                             (None, None, None, None, "Idle") )


    # Declare a function that will be called when entering or leaving a qstate.
    @on_enter_function(wstate)
    def _enter_qstate(self):
        logger.info( "entering state %s of %s" % (self.WriteState.name(), self.mname) )
    @on_leave_function(wstate)
    def _leave_qstate(self):
        logger.info( "leaving state %s of %s" % (self.WriteState.name(), self.mname) )


class opcTrigVarFSM(object):
    # WriteOut state table
    tstate = StateTable("TriggerState")

    def __init__(self, name, cSMax = 3, cRMax = 3):
        # must call init method of class's StateTable object. to initialize state variable
        self.tstate.initialize(self)
        self.mname = name
        self.cSMax = cSMax
        self.cRMax = cRMax
        self.s_count = 0
        self.r_count = 0

    def _initSCount(self):
        self.s_count = 1
    def _incSCount(self):
        self.s_count += 1
    def _initRCount(self):
        self.r_count = 1
    def _incRCount(self):
        self.r_count += 1

    # Decorate the Event Handler virtual functions -note tstate parameter
    @event_handler(tstate)
    def event_TSet(self): pass
    @event_handler(tstate)
    def event_SOK(self): pass
    @event_handler(tstate)
    def event_TReset(self): pass
    @event_handler(tstate)
    def event_ROK(self): pass
    @event_handler(tstate)
    def event_Reset(self): pass

    # define methods to handle events.
    ## At Idle State
    def _event_TSet_Idle(self):
        logger.info( "%s: State %s, event TSet (command rising edge)" % (self.mname,self.TriggerState.name(),) )
        self._initSCount()
    ## At ToSet State
    def _event_TSet_ToSet(self):
        self._incSCount()
        if self.s_count >= self.cSMax:
            logger.info( "%s: State %s, event TSet(%s) (rising edge not possible) - fall back to Idle" % (self.mname,self.TriggerState.name(),self.s_count) )
            self.TriggerState.next_state = self._Idle
        else:
            logger.info( "%s: State %s, event TSet(%s) (command rising edge)" % (self.mname,self.TriggerState.name(),self.s_count) )
    def _event_SOK_ToSet(self):
        logger.info( "%s: State %s, event SOK (rising edge done)" % (self.mname,self.TriggerState.name(),) )
    ## At Set State
    def _event_TReset_Set(self):
        logger.info( "%s: State %s, event TReset (command trailing edge)" % (self.mname,self.TriggerState.name(),) )
        self._initRCount()
    def _event_TSet_Set(self):
        logger.info( "%s: State %s, event TSet (command rising edge) - need TReset first" % (self.mname,self.TriggerState.name(),) )
        self._initRCount()
    def _event_Reset_Set(self):
        logger.info( "%s: State %s, event Reset (re-initalize the FSM)" % (self.mname,self.TriggerState.name(),) )
        self.__init__(self.mname)
    ## At ToReset State
    def _event_TReset_ToReset(self):
        self._incRCount()
        if self.r_count >= self.cRMax:
            logger.info( "%s: State %s, event TReset(%s) (trailing edge not possible) - fall back to Set" % (self.mname,self.TriggerState.name(),self.r_count) )
            self.TriggerState.next_state = self._Set
        else:
            logger.info( "%s: State %s, event TReset(%s) (command trailing edge)" % (self.mname,self.TriggerState.name(),self.r_count) )
    def _event_ROK_ToReset(self):
        logger.info( "%s: State %s, event ROK (trailing edge done)" % (self.mname,self.TriggerState.name(),) )
    ## At ToResetToSet State
    def _event_TSet_ToResetToSet(self):
        self._incRCount()
        if self.r_count >= self.cRMax:
            logger.info( "%s: State %s, event TSet(%s) (trailing edge not possible) - fall back to Set" % (self.mname,self.TriggerState.name(),self.r_count) )
            self.TriggerState.next_state = self._Set
        else:
            logger.info( "%s: State %s, event TSet(%s) (command rising edge) - need TReset first" % (self.mname,self.TriggerState.name(),self.r_count) )
    def _event_ROK_ToResetToSet(self):
        logger.info( "%s: State %s, event ROK (trailing edge done) - (command rising edge)" % (self.mname,self.TriggerState.name(),) )
        self._initSCount()
    ## for any State
    def _event_TSet(self): pass
    def _event_SOK(self): pass
    def _event_TReset(self): pass
    def _event_ROK(self): pass
    def _event_Reset(self): pass

    # Associate the handlers with a state.
    # - First arg is the name of the state.
    # - Second argument is a list of methods.  One method for each event_handler decorated function.
    #   Order of methods in the list correspond to order in which the Event Handlers were declared.
    # - Third argument is a list of the next states in the same order as for the methods.
    # The first state created becomes the initial state.
    _Idle = tstate.state( "Idle",
                          (_event_TSet_Idle, _event_SOK, _event_TReset, _event_ROK, _event_Reset, ),
                          ("ToSet", None, None, None, None, ) )
    _ToSet = tstate.state( "ToSet",
                          (_event_TSet_ToSet, _event_SOK_ToSet, _event_TReset, _event_ROK, _event_Reset, ),
                          (None, "Set", None, None, None, ) )
    _Set = tstate.state( "Set",
                          (_event_TSet_Set, _event_SOK, _event_TReset_Set, _event_ROK, _event_Reset_Set, ),
                          ("ToResetToSet", None, "ToReset", None, "Idle", ) )
    _ToReset = tstate.state( "ToReset",
                          (_event_TSet, _event_SOK, _event_TReset_ToReset, _event_ROK_ToReset, _event_Reset, ),
                          (None, None, None, "Idle", None, ) )
    _ToResetToSet = tstate.state( "ToResetToSet",
                          (_event_TSet_ToResetToSet, _event_SOK, _event_TReset, _event_ROK_ToResetToSet, _event_Reset, ),
                          (None, None, None, "ToSet", None, ) )


    # Declare a function that will be called when entering or leaving a tstate.
    @on_enter_function(tstate)
    def _enter_tstate(self):
        logger.info( "entering state %s of %s" % (self.TriggerState.name(), self.mname) )
    @on_leave_function(tstate)
    def _leave_tstate(self):
        logger.info( "leaving state %s of %s" % (self.TriggerState.name(), self.mname) )





def main_read():
    vTest = opcVarFSM("Test")

    vTest.event_Reset()
    vTest.event_RGood()
    vTest.event_RBad()
    vTest.event_RGood()
    vTest.event_RBad()
    vTest.event_RBad()
    vTest.event_RGood()
    vTest.event_RBad()
    vTest.event_RBad()
    vTest.event_Reset()
    vTest.event_RBad()
    vTest.event_RBad()
    vTest.event_RBad()
    vTest.event_RBad()
    vTest.event_Reset()
    vTest.event_RBad()
    vTest.event_RGood()
    vTest.event_RGood()

def main_write():
    vTest = opcVarWFSM("Test")

    vTest.event_NData(1)
    vTest.event_WTrig()
    vTest.event_WOK()
    vTest.event_NData(1)
    vTest.event_NData(2)
    vTest.event_WTrig()
    vTest.event_NData(3)
    vTest.event_WOK()
    vTest.event_WTrig()
    vTest.event_WOK()
    vTest.event_WTrig() #should be ignored
    vTest.event_WOK() #should be ignored
    vTest.event_NData(4)
    vTest.event_WTrig()
    vTest.event_WError()
    vTest.event_WOK()
    vTest.event_NData(5)
    vTest.event_WTrig()
    vTest.event_WError()
    vTest.event_WError()
    vTest.event_WError()
    vTest.event_Reset()

def main_trigger():
    vTest = opcTrigVarFSM("Test")

    vTest.event_TSet()
    vTest.event_SOK()
    vTest.event_TReset()
    vTest.event_ROK()
    vTest.event_TSet()
    vTest.event_SOK()
    vTest.event_TSet()
    vTest.event_ROK()
    vTest.event_SOK()
    vTest.event_Reset()
    vTest.event_TSet()
    vTest.event_TSet()
    vTest.event_TSet()
    vTest.event_TSet()
    vTest.event_SOK()
    vTest.event_TSet()
    vTest.event_TSet()
    vTest.event_TSet()
    vTest.event_TReset()
    vTest.event_TReset()
    vTest.event_TReset()
    vTest.event_Reset()


if __name__ == "__main__":

    Sh = logging.StreamHandler()
    Sh.setLevel(logging.DEBUG)
    localLog = logging.getLogger(__name__)
    localLog.addHandler(Sh)
    localLog.setLevel(logging.INFO)

    #main_read()
    #main_write()
    main_trigger()
