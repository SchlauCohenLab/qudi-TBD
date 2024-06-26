# -*- coding: utf-8 -*-
"""
This file contains the qudi switch state QWidgets for the GUI module SwitchGui.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

from PySide2 import QtWidgets, QtCore, QtGui
from qudi.util.widgets.toggle_switch import ToggleSwitch


class SwitchRadioButtonWidget(QtWidgets.QWidget):
    """
    """

    sigStateChanged = QtCore.Signal(str)

    def __init__(self, parent=None, switch_states=('Off', 'On')):
        assert len(switch_states) >= 2, 'switch_states must be tuple of at least 2 strings'
        assert all(isinstance(s, str) and s for s in switch_states), \
            'switch state must be non-empty str'
        super().__init__(parent=parent)
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.switch_states = tuple(switch_states)
        self._state_colors = (None, None)
        self.radio_buttons = {state: QtWidgets.QRadioButton() for state in switch_states}
        self._labels = {state: QtWidgets.QLabel(state) for state in switch_states}
        button_group = QtWidgets.QButtonGroup(self)
        for ii, (state, button) in enumerate(self.radio_buttons.items()):
            button.setLayoutDirection(QtCore.Qt.RightToLeft)
            button_group.addButton(button, ii)
            label = self._labels[state]
            label.setTextFormat(QtCore.Qt.RichText)
            label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            layout.addWidget(button)
            layout.addWidget(label)
        layout.addStretch()
        button_group.buttonToggled.connect(self.__button_toggled_cb)

    def __button_toggled_cb(self, button, checked):
        """

        @param button:
        @param checked:
        """
        if checked:
            for state, radio in self.radio_buttons.items():
                if button is radio:
                    self.sigStateChanged.emit(state)
                    self._update_colors()

    @property
    def switch_state(self):
        for state, button in self.radio_buttons.items():
            if button.isChecked():
                return state

    @switch_state.setter
    def switch_state(self, state):
        self.set_state(state)

    @QtCore.Slot(str)
    def set_state(self, state):
        assert state in self.switch_states, f'Invalid switch state: "{state}"'
        button = self.radio_buttons[state]
        if not button.isChecked():
            button.blockSignals(True)
            button.setChecked(True)
            button.blockSignals(False)
            self._update_colors()

    def setFont(self, font):
        for label in self._labels.values():
            label.setFont(font)

    def set_state_colors(self, unchecked=None, checked=None):
        assert unchecked is None or isinstance(unchecked, QtGui.QColor), \
            'arguments must be QColor object or None'
        assert checked is None or isinstance(checked, QtGui.QColor), \
            'arguments must be QColor object or None'
        self._state_colors = (unchecked, checked)
        self._update_colors()

    def _update_colors(self):
        for state, button in self.radio_buttons.items():
            label = self._labels[state]
            color = self._state_colors[int(button.isChecked())]
            if color is None:
                label.setText(state)
            else:
                label.setText(f'<font color={color.name()}>{state}</font>')


class ToggleSwitchWidget(QtWidgets.QWidget):
    """
    """

    sigStateChanged = QtCore.Signal(str)

    def __init__(self, parent=None, switch_states=('Off', 'On'), thumb_track_ratio=1,
                 scale_text_in_switch=True, text_inside_switch=True):
        super().__init__(parent=parent)
        assert len(switch_states) == 2, 'switch_states must be tuple of exactly 2 strings'
        assert all(isinstance(s, str) and s for s in switch_states), \
            'switch state must be non-empty str'
        self.switch_states = tuple(switch_states)
        self._state_colors = (None, None)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.toggle_switch = ToggleSwitch(state_names=switch_states,
                                          thumb_track_ratio=thumb_track_ratio,
                                          scale_text=scale_text_in_switch,
                                          display_text=text_inside_switch)
        self.toggle_switch.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Preferred)
        if text_inside_switch:
            self.labels = None
            layout.addWidget(self.toggle_switch)
        else:
            self.labels = (QtWidgets.QLabel(switch_states[0]), QtWidgets.QLabel(switch_states[1]))
            self.labels[0].setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.labels[0].setTextFormat(QtCore.Qt.RichText)
            self.labels[1].setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.labels[1].setTextFormat(QtCore.Qt.RichText)
            layout.addWidget(self.labels[0])
            layout.addWidget(self.toggle_switch)
            layout.addWidget(self.labels[1])

        self.toggle_switch.sigStateChanged.connect(self._update_colors)
        self.toggle_switch.sigStateChanged.connect(self.sigStateChanged)

    def setFont(self, font):
        super().setFont(font)
        if self.labels:
            self.labels[0].setFont(font)
            self.labels[1].setFont(font)

    @property
    def switch_state(self):
        return self.toggle_switch.current_state

    @switch_state.setter
    def switch_state(self, state):
        self.set_state(state)

    @QtCore.Slot(str)
    def set_state(self, state):
        assert state in self.switch_states, f'Invalid switch state: "{state}"'
        self.toggle_switch.setChecked(bool(self.switch_states.index(state)))
        self._update_colors()

    def set_state_colors(self, unchecked=None, checked=None):
        assert unchecked is None or isinstance(unchecked, QtGui.QColor), \
            'arguments must be QColor object or None'
        assert checked is None or isinstance(checked, QtGui.QColor), \
            'arguments must be QColor object or None'
        self._state_colors = (unchecked, checked)
        self._update_colors()

    def _update_colors(self):
        if self.labels is not None:
            checked = self.toggle_switch.isChecked()
            color = self._state_colors[int(not checked)]
            if color is None:
                self.labels[0].setText(self.switch_states[0])
            else:
                self.labels[0].setText(f'<font color={color.name()}>{self.switch_states[0]}</font>')
            color = self._state_colors[int(checked)]
            if color is None:
                self.labels[1].setText(self.switch_states[1])
            else:
                self.labels[1].setText(f'<font color={color.name()}>{self.switch_states[1]}</font>')
