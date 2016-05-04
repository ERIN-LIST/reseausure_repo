#
# Support for State Machines.  ref - Design Patterns by GoF
#  Many of the methods in these classes get called behind the scenes.
#
#  Notable exceptions are methods of the StateVar class.
#
#  See example programs for how this module is intended to be used.
#

class StateMachineError(Exception):
    def __init__(self, args = None):
        self.args = args

class StateVar(object):
    def __init__(self, initial_state):
        self._current_state = initial_state
        self.next_state = initial_state            # publicly settable in an event handling routine.

    def set_state(self, owner, new_state):
        '''
        Forces a state change to new_state
        '''
        self.next_state = new_state
        self.__to_next_state(owner)

    def __to_next_state(self, owner):
        '''
        The low-level state change function which calls leave state & enter state functions as
        needed.

        LeaveState and EnterState functions are called as needed when state transitions.
        '''
        if self.next_state is not self._current_state:
            if hasattr(self._current_state, "leave"):
                self._current_state.leave(owner)
            elif hasattr(self, "leave"):
                self.leave(owner)
            self._current_state =  self.next_state
            if hasattr(self._current_state, "enter"):
                self._current_state.enter(owner)
            elif hasattr(self, "enter"):
                self.enter(owner)

    def __fctn(self, func_name):
        '''
        Returns the owning class's method for handling an event for the current state.
        This method not for public consumption.
        '''
        vf = self._current_state.get_fe(func_name)
        return vf

    def name(self):
        '''
        Returns the current state name.
        '''
        return self._current_state.name

class STState(object):
    def __init__(self, state_name):
        self.name = state_name
        self.fctn_dict = {}

    def set_events(self, event_list, event_hdlr_list, next_states):
        dictionary = self.fctn_dict
        if not next_states:
            def set_row(event, method):
                dictionary[event] = [method, None]
            map(set_row, event_list, event_hdlr_list)
        else:
            def set_row2(event, method, next_state):
                dictionary[event] = [method, next_state]
            map(set_row2, event_list, event_hdlr_list, next_states)
        self.fctn_dict = dictionary

    def get_fe(self, fctn_name):
        return self.fctn_dict[fctn_name]

    def map_next_states(self, state_dict):
        ''' Changes second dict value from name of state to actual state '''
        for de in self.fctn_dict.values():
            next_state_name = de[1]
            if next_state_name:
                if next_state_name in state_dict:
                    de[1] = state_dict[next_state_name]
                else:
                    raise StateMachineError('Invalid Name for next state: %s' % next_state_name)


class StateTable(object):
    '''
    Magical class to define a state machine, with the help of several decorator functions
    which follow.
    '''
    def __init__(self, declname):
        self.machine_var = declname
        self._initial_state = None
        self._state_list = {}
        self._event_list = []
        self.need_initialize = 1

    def initialize(self, parent):
        '''
        Initializes the parent class's state variable for this StateTable class.
        Must call this method in the parent' object's __init__ method.  You can have
        Multiple state machines within a parent class. Call this method for each
        '''
        statevar= StateVar(self._initial_state)
        setattr(parent, self.machine_var, statevar)
        if hasattr(self, "enter"):
            statevar.enter = self.enter
        if hasattr(self, "leave"):
            statevar.leave = self.leave
        #Magic happens here - in the 'next state' table, translate names into state objects.
        if  self.need_initialize:
            for xstate in list(self._state_list.values()):
                xstate.map_next_states(self._state_list)
            self.need_initialize = 0

    def def_state(self, event_hdlr_list, name):
        '''
        This is used to define a state. the event handler list is a list of functions that
        are called for corresponding events. name is the name of the state.
        '''
        state_table_row = STState(name)
        if len(event_hdlr_list) != len(self._event_list):
            raise StateMachineError('Mismatch between number of event handlers and the methods specified for the state.')

        state_table_row.set_events(self._event_list, event_hdlr_list, None)

        if self._initial_state is None:
            self._initial_state = state_table_row
        self._state_list[name] = state_table_row
        return state_table_row

    def state(self, name, event_hdlr_list, next_states):
        state_table_row = STState(name)
        if len(event_hdlr_list) != len(self._event_list):
            raise StateMachineError('Mismatch between number of event handlers and the methods specified for the state.')
        if next_states is not None and len(next_states) != len(self._event_list):
            raise StateMachineError('Mismatch between number of event handlers and the next states specified for the state.')

        state_table_row.set_events(self._event_list, event_hdlr_list, next_states)

        if self._initial_state is None:
            self._initial_state = state_table_row
        self._state_list[name] = state_table_row
        return state_table_row

    def __add_ev_hdlr(self, func_name):
        '''
        Informs the class of an event handler to be added. We just need the name here. The
        function name will later be associated with one of the functions in a list when a state is defined.
        '''
        self._event_list.append(func_name)

# Decorator functions ...
def event_handler(state_class):
    '''
    Declare a method that handles a type of event.
    '''
    def wrapper(func):
        state_class._StateTable__add_ev_hdlr(func.__name__)
        def obj_call(self, *args, **keywords):
            state_var = getattr(self, state_class.machine_var)
            funky, next_state = state_var._StateVar__fctn(func.__name__)
            if next_state is not None:
                state_var.next_state = next_state
            rv = funky(self, *args, **keywords)
            state_var._StateVar__to_next_state(self)
            return rv
        return obj_call
    return wrapper

def on_enter_function(state_class):
    '''
    Declare that this method should be called whenever a new state is entered.
    '''
    def wrapper(func):
        state_class.enter = func
        return func
    return wrapper

def on_leave_function(state_class):
    '''
    Declares that this method should be called whenever leaving a state.
    '''
    def wrapper(func):
        state_class.leave = func
        return func
    return wrapper
