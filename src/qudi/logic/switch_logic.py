# -*- coding: utf-8 -*-

__all__ = ['SwitchLogic']

from PySide2 import QtCore

from qudi.core.module import LogicBase
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import RecursiveMutex

# qudi logic measurement modules must inherit qudi.core.module.LogicBase or other logic modules.
class SwitchLogic(LogicBase):
    """ Logic module for interacting with the hardware switches.
    This logic has the same structure as the SwitchInterface but supplies additional functionality:
        - switches can either be manipulated by index or by their names
        - signals are generated on state changes

    switchlogic:
        module.Class: 'switch_logic.SwitchLogic'
        options:
            watchdog_interval: 1  # optional
            autostart_watchdog: True  # optional
        connect:
            switch: <switch name>
    """

    # connector for one switch, if multiple switches are needed use the SwitchCombinerInterfuse
    switch = Connector(interface='SwitchInterface')

    _watchdog_interval = ConfigOption(name='watchdog_interval', default=1.0, missing='nothing')
    _autostart_watchdog = ConfigOption(name='autostart_watchdog', default=False, missing='nothing')

    sigSwitchesChanged = QtCore.Signal(dict)
    sigWatchdogToggled = QtCore.Signal(bool)

    # directly wrapped attributes from hardware module
    __wrapped_hw_attributes = frozenset({'switch_names', 'number_of_switches', 'available_states'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()

        self._watchdog_active = False
        self._watchdog_interval_ms = 0
        self._old_states = dict()

    def on_activate(self):
        """ Activate module
        """
        self._old_states = self.states
        self._watchdog_interval_ms = int(round(self._watchdog_interval * 1000))

        if self._autostart_watchdog:
            self._watchdog_active = True
            QtCore.QMetaObject.invokeMethod(self, '_watchdog_body', QtCore.Qt.QueuedConnection)
        else:
            self._watchdog_active = False

    def on_deactivate(self):
        """ Deactivate module
        """
        self._watchdog_active = False

    def __getattr__(self, item):
        if item in self.__wrapped_hw_attributes:
            return getattr(self.switch(), item)
        raise AttributeError(f'SwitchLogic has no attribute with name "{item}"')

    @property
    def device_name(self):
        """ Name of the connected hardware switch as string.

        @return str: The name of the connected hardware switch
        """
        return self.switch().name

    @property
    def watchdog_active(self):
        return self._watchdog_active

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        with self._thread_lock:
            try:
                states = self.switch().states
            except:
                if self._watchdog_active:
                    self.toggle_watchdog(False)
                    self.log.exception(f'Error during query of all switch states. '
                                       f'Deactivating watchdog to avoid constant errors.')
                else:
                    self.log.exception(f'Error during query of all switch states.')
                states = dict()
            return states

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        with self._thread_lock:
            try:
                self.switch().states = state_dict
            except:
                self.log.exception('Error while trying to set switch states.')

            states = self.states
            if states:
                self.sigSwitchesChanged.emit({switch: states[switch] for switch in state_dict})

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        with self._thread_lock:
            try:
                state = self.switch().get_state(switch)
            except:
                self.log.exception(f'Error while trying to query state of switch "{switch}".')
                state = None
            return state

    @QtCore.Slot(str, str)
    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        with self._thread_lock:
            try:
                self.switch().set_state(switch, state)
            except:
                self.log.exception(
                    f'Error while trying to set switch "{switch}" to state "{state}".'
                )
            curr_state = self.get_state(switch)
            if curr_state is not None:
                self.sigSwitchesChanged.emit({switch: curr_state})

    @QtCore.Slot(bool)
    def toggle_watchdog(self, enable):
        """

        @param bool enable:
        """
        enable = bool(enable)
        with self._thread_lock:
            if enable != self._watchdog_active:
                self._watchdog_active = enable
                self.sigWatchdogToggled.emit(enable)
                if enable:
                    QtCore.QMetaObject.invokeMethod(self,
                                                    '_watchdog_body',
                                                    QtCore.Qt.QueuedConnection)

    @QtCore.Slot()
    def _watchdog_body(self):
        """ Helper function to regularly query the states from the hardware.

        This function is called by an internal signal and queries the hardware regularly to fire
        the signal sig_switch_updated, if the hardware changed its state without notifying the logic.
        The timing of the watchdog is set by the ConfigOption watchdog_interval in seconds.
        """
        with self._thread_lock:
            if self._watchdog_active:
                curr_states = self.states
                diff_state = {switch: state for switch, state in curr_states.items() if
                              state != self._old_states[switch]}
                self._old_states = curr_states
                if diff_state:
                    self.sigSwitchesChanged.emit(diff_state)
                QtCore.QTimer.singleShot(self._watchdog_interval_ms, self._watchdog_body)

