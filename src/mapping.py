# -*- coding: utf-8 -*-
"""
WiiPad, a simple user-space driver for Wii/WiiU controllers
Copyright (C) 2014  Arturo Casal

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import uinputdefs

# Axis -> Axis
# Side_Axis -> Side_Axis
# Side_Axis -> Button
# Axis -> Button
# Button -> Button
# Button -> Axis
# Button -> Side_Axis (default = 0, if push X, axis = +FULL, if push Y, axis = -FULL)

# Souce axis can be inverted

# Descriptors
class ABS_Params():
	def __init__(self, _min=0, _max=0, _fuzz=0, _flat=0):
		self.min = _min
		self.max = _max
		self.fuzz = _fuzz
		self.flat = _flat

class WiimoteDescription():
	BTN_A = 0
	BTN_B = 1
	BTN_1 = 2
	BTN_2 = 3
	BTN_MINUS = 4
	BTN_HOME = 5
	BTN_PLUS = 6
	BTN_LEFT = 7
	BTN_RIGHT = 8
	BTN_UP = 9
	BTN_DOWN = 10
	BTN_SHAKE = 11
	ACCEL_X = 12
	ACCEL_Y = 13
	ACCEL_Z = 14
	SIZE = 15
	
	axis = [False]*SIZE
	axis[ACCEL_X] = True
	axis[ACCEL_Y] = True
	axis[ACCEL_Z] = True
	
	abs_params = {
		ACCEL_X : ABS_Params(_min=-500, _max=500, _fuzz=2, _flat=4),
		ACCEL_Y : ABS_Params(_min=-500, _max=500, _fuzz=2, _flat=4),
		ACCEL_Z : ABS_Params(_min=-500, _max=500, _fuzz=2, _flat=4)
	}

class NunchukDescription(WiimoteDescription):
	BTN_C = WiimoteDescription.SIZE
	BTN_Z = BTN_C + 1
	AXIS_X = BTN_C + 2
	AXIS_Y = BTN_C + 3
	BTN_NSHAKE = BTN_C + 4
	ACCEL_NX = BTN_C + 5
	ACCEL_NY = BTN_C + 6
	ACCEL_NZ = BTN_C + 7
	SIZE = BTN_C + 8
	
	axis = WiimoteDescription.axis+[False]*(SIZE-WiimoteDescription.SIZE)
	axis[AXIS_X] = True
	axis[AXIS_Y] = True
	axis[ACCEL_NX] = True
	axis[ACCEL_NY] = True
	axis[ACCEL_NZ] = True
	
	abs_params = dict(WiimoteDescription.abs_params.items() + {
		AXIS_X : ABS_Params(_min=-120, _max=120, _fuzz=2, _flat=4),
		AXIS_Y : ABS_Params(_min=-120, _max=120, _fuzz=2, _flat=4),
		ACCEL_NX : ABS_Params(_min=-500, _max=500, _fuzz=2, _flat=4),
		ACCEL_NY : ABS_Params(_min=-500, _max=500, _fuzz=2, _flat=4),
		ACCEL_NZ : ABS_Params(_min=-500, _max=500, _fuzz=2, _flat=4)
	}.items())
	
class ClassicControllerDescription():
	BTN_A = 0
	BTN_B = 1
	BTN_X = 2
	BTN_Y = 3
	BTN_MINUS = 4
	BTN_HOME = 5
	BTN_PLUS = 6
	BTN_LEFT = 7
	BTN_RIGHT = 8
	BTN_UP = 9
	BTN_DOWN = 10
	BTN_TL = 11
	BTN_TR = 12
	BTN_ZL = 13
	BTN_ZR = 14
	AXIS_X = 15
	AXIS_Y = 16
	AXIS_RX = 17
	AXIS_RY = 18
	AXIS_LT = 19
	AXIS_RT = 20
	SIZE = 21
	
	axis = [False]*SIZE
	axis[AXIS_X] = True
	axis[AXIS_Y] = True
	axis[AXIS_RX] = True
	axis[AXIS_RY] = True
	axis[AXIS_LT] = True
	axis[AXIS_RT] = True
	
	abs_params = {
		AXIS_X : ABS_Params(_min=-30, _max=30, _fuzz=1, _flat=1),
		AXIS_Y : ABS_Params(_min=-30, _max=30, _fuzz=1, _flat=1),
		AXIS_RX : ABS_Params(_min=-30, _max=30, _fuzz=1, _flat=1),
		AXIS_RY : ABS_Params(_min=-30, _max=30, _fuzz=1, _flat=1),
		AXIS_LT : ABS_Params(_min=-30, _max=30, _fuzz=1, _flat=1),
		AXIS_RT : ABS_Params(_min=-30, _max=30, _fuzz=1, _flat=1)
	}
	
class ProControllerDescription():
	BTN_A = 0
	BTN_B = 1
	BTN_X = 2
	BTN_Y = 3
	BTN_MINUS = 4
	BTN_HOME = 5
	BTN_PLUS = 6
	BTN_LEFT = 7
	BTN_RIGHT = 8
	BTN_UP = 9
	BTN_DOWN = 10
	BTN_TL = 11
	BTN_TR = 12
	BTN_ZL = 13
	BTN_ZR = 14
	AXIS_X = 15
	AXIS_Y = 16
	AXIS_RX = 17
	AXIS_RY = 18
	BTN_THUMBL = 19
	BTN_THUMBR = 20
	SIZE = 21
	
	axis = [False]*SIZE
	axis[AXIS_X] = True
	axis[AXIS_Y] = True
	axis[AXIS_RX] = True
	axis[AXIS_RY] = True
	
	abs_params = {
		AXIS_X : ABS_Params(_min=-0x400, _max=0x400, _fuzz=4, _flat=100),
		AXIS_Y : ABS_Params(_min=-0x400, _max=0x400, _fuzz=4, _flat=100),
		AXIS_RX : ABS_Params(_min=-0x400, _max=0x400, _fuzz=4, _flat=100),
		AXIS_RY : ABS_Params(_min=-0x400, _max=0x400, _fuzz=4, _flat=100)
	}

class MappingProfile():
	
	def __init__(self, name=None, wiimoteMapping=None, wiimoteNunchuckMapping=None, classicMapping=None, proMapping=None):
		self.wiimoteMapping = wiimoteMapping
		self.wiimoteNunchuckMapping = wiimoteNunchuckMapping
		self.classicMapping = classicMapping
		self.proMapping = proMapping
		self.name = name

class Mapping():
	
	isGamepad = False	
	
	def __init__(self, description, name=None, isGamepad=False):
		self.mapping = [None]*description.SIZE
		self.name = name
		self.description = description
		self.isGamepad = isGamepad
		
	def setMap(self, position, _map):
		if position >= 0 and position < len(self.mapping):
			self.mapping[position] = _map
		# Recalc isGamepad
		if not self.isGamepad:
			self.isGamepad = self.isGamepadAssignment(_map)
		
	def getMapping(self, position):
		return self.mapping[position]
		
	def isGamepadAssignment(self, key):
		return (
			(key._type == uinputdefs.EV_KEY and key._code[0] >= uinputdefs.BTN_DPAD_UP and key._code[0] <= uinputdefs.BTN_TRIGGER_HAPPY40) or
			(key._type == uinputdefs.EV_KEY and key._code[0] >= uinputdefs.BTN_JOYSTICK and key._code[0] <= uinputdefs.BTN_GEAR_UP) or
			(key._type == uinputdefs.EV_ABS and key._code[0] >= uinputdefs.ABS_X and key._code[0] <= uinputdefs.ABS_MAX)
			)
		
	
class ButtonMapping():
	_type = uinputdefs.EV_KEY
	
	def __init__(self, key, sensitivity=None):
		if isinstance(key, list):
			self._code = [key[0]]
		else:
			self._code = [key]
		self.sensitivity = sensitivity

class AxisMapping():
	_type = uinputdefs.EV_ABS
	
	def __init__(self, axis, sourceScale=None, deadZone=0, isInverted=False):
		if isinstance(axis, list):
			self._code = axis
		else:
			self._code = [axis]
		self.isInverted = isInverted
		self.deadZone = deadZone
		self.sourceScale = sourceScale