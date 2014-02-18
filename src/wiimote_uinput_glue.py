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
import bluetooth
import logging

import libuinput
import libwiimote
import uinputdefs
import mapping
import fileutils

def getevent(typ, code, value):
	ev = uinputdefs.input_event()
	ev.time = uinputdefs.gettimeofday()
	ev.type = typ
	ev.code = code
	ev.value = value
	return ev

PROFILE_UNKNOWN = 0
PROFILE_WIIMOTE = 1
PROFILE_WIIMOTE_NUNCHUK = 2
PROFILE_CLASSIC_CONTROLLER = 3
PROFILE_PRO_CONTROLLER = 4
PROFILE_BALANCE_BOARD = 5

def getNumberOfGamepads():
	f = open('/proc/bus/input/devices', 'r')
	n = 0
	try:
		devices = f.readlines()
		for l in devices[:]:
			if "andlers=" in l and "js" in l:
				n+=1
	except:
		pass
	return n



def getNewWiimoteLedIndex():
	f = open('/proc/bus/input/devices', 'r')
	n = 0
	try:
		devices = f.readlines()
		for l in devices[:]:
			if "andlers=" in l and "js" in l:
				n+=1
	except:
		pass
	return n

def compute_deadzone(_axmap, _aymap, _axmax, _aymax, ax, ay):
	if isinstance(_axmap, mapping.AxisMapping) and isinstance(_aymap, mapping.AxisMapping):
		_axdz = _axmap.deadZone
		_aydz = _aymap.deadZone
		if _axdz > 0 and _aydz > 0:
			_axlim = (_axdz/float(100))*_axmax
			_aylim = (_aydz/float(100))*_aymax
			ellip = (ax ** 2 / _axlim ** 2) + (ay ** 2 / _aylim ** 2)
			return ellip < 1
	return False
	
def compute_single_deadzone(_axmap, _axmax, ax):
	if isinstance(_axmap, mapping.AxisMapping):
		_axdz = _axmap.deadZone
		if _axdz > 0:
			_axlim = (_axdz/float(100))*_axmax
			return ax < _axlim and ax > -_axlim
	return False

class UInputWiimote():
	initialized = False
	def __init__(self, address, name, mappingProfile, led=1, disconnectCallback=None):
		self.uinputextension = libwiimote.WiiDevExtension.WIIMOTE_EXT_NONE
		self.mappingProfile = mappingProfile
		self.disconnectCallback = disconnectCallback
		self.profile = PROFILE_UNKNOWN
		self.led = led
		self.wiimotedev = libwiimote.WiiDevice(address, name, self.handler_keys, self.handler_accel, self.handler_ext, self.handler_sync, extension_change_callback=self.extension_change, disconnect_callback=self.device_disconnected)
		self.address = address
		self.name = name
		self.wiimotedev.connect()
		
		self.wiimotedev.setLedByIndex(led)
		
		self.initializeDevice()
	
	def initializeDevice(self):
		self.update_profile_status()		
		
		if self.profile == PROFILE_PRO_CONTROLLER:
			self.mapping = self.mappingProfile.proMapping
		elif self.profile == PROFILE_CLASSIC_CONTROLLER:
			self.mapping = self.mappingProfile.classicMapping
		elif self.profile == PROFILE_WIIMOTE:
			self.mapping = self.mappingProfile.wiimoteMapping
		elif self.profile == PROFILE_WIIMOTE_NUNCHUK:
			self.mapping = self.mappingProfile.wiimoteNunchuckMapping
			
		if self.mapping == None:
			logging.warning("Your mapping profile does not have a mapping defined for your device combination")
			self.initialized = False
			return
		
		# Avoid Xorg server blacklist
		if not self.mapping.isGamepad:
			self.uinput_name = self.uinput_name.replace("Nintendo", "Nintendo Keyboard")
		
		self.prettyName = libwiimote.getDeviceName(self.wiimotedev)
		print(self.prettyName+" detected (player %d)."%self.led)
		print("Battery level = %d %%"%self.wiimotedev.state.cmd_battery)
		
		logging.debug("Creating UInput device called \""+self.uinput_name+"\"")
		self.create_uinput_dev()
		
		self.initialized = True
	
	def handler_keys(self, payload):
		if not self.initialized or self.uinputdev == None:
			return
		if self.profile == PROFILE_WIIMOTE or self.profile == PROFILE_WIIMOTE_NUNCHUK:
			btn_left, btn_right, btn_up, btn_down, btn_minus, btn_home, btn_plus, btn_a, btn_b, btn_1, btn_2 = libwiimote.WiiDataParser.parseWiimoteKeys(self.wiimotedev, payload)
			pd = self.mapping.description
			values = [False]*pd.SIZE
			values[pd.BTN_A] = btn_a
			values[pd.BTN_B] = btn_b
			values[pd.BTN_1] = btn_1
			values[pd.BTN_2] = btn_2
			values[pd.BTN_LEFT] = btn_left
			values[pd.BTN_RIGHT] = btn_right
			values[pd.BTN_UP] = btn_up
			values[pd.BTN_DOWN] = btn_down
			values[pd.BTN_MINUS] = btn_minus
			values[pd.BTN_HOME] = btn_home
			values[pd.BTN_PLUS] = btn_plus
			# Send events
			index = -1
			for v in values[:]:
				index+=1
				_map = self.mapping.mapping[index]
				if _map == None:
					continue
				self.send_event(_map, v, pd.axis[index])
	
	def handler_accel(self, payload):
		if not self.initialized or self.uinputdev == None:
			return
		if self.profile == PROFILE_WIIMOTE or self.profile == PROFILE_WIIMOTE_NUNCHUK:
			x, y, z = libwiimote.WiiDataParser.parseWiimoteAccel(self.wiimotedev, payload)
			y = -y
			pd = self.mapping.description
			# ACCEL_X
			_map = self.mapping.mapping[pd.ACCEL_X]
			if _map != None:
				if compute_single_deadzone(_map, pd.abs_params[pd.ACCEL_X].max, x):
					x = 0
				self.send_event(_map, x, pd.axis[pd.ACCEL_X], _abs=pd.abs_params[pd.ACCEL_X])
			# ACCEL_Y (tilt left-right in horizontal)
			_map = self.mapping.mapping[pd.ACCEL_Y]
			if _map != None:
				if compute_single_deadzone(_map, pd.abs_params[pd.ACCEL_Y].max, y):
					y = 0
				self.send_event(_map, y, pd.axis[pd.ACCEL_Y], _abs=pd.abs_params[pd.ACCEL_Y])
			# ACCEL_Z
			_map = self.mapping.mapping[pd.ACCEL_Z]
			if _map != None:
				if compute_single_deadzone(_map, pd.abs_params[pd.ACCEL_Z].max, z):
					z = 0
				self.send_event(_map, z, pd.axis[pd.ACCEL_Z], _abs=pd.abs_params[pd.ACCEL_Z])
				
			# BTN_SHAKE
			_map = self.mapping.mapping[pd.BTN_SHAKE]
			if _map != None:
				_sens = 260
				if isinstance(_map, mapping.ButtonMapping) and _map.sensitivity > 0:
					_sens = _map.sensitivity
				val = 1 if (z < -_sens or z > _sens) else 0
				self.send_event(_map, val, pd.axis[pd.BTN_SHAKE])
		
	def handler_ext(self, payload):
		if not self.initialized or self.uinputdev == None:
			return
		# Check extension first
		pd = self.mapping.description
		values = {}
		if self.profile == PROFILE_PRO_CONTROLLER:
			lx, ly, rx, ry, btn_left, btn_right, btn_up, btn_down, btn_minus, btn_home, btn_plus, btn_a, btn_b, btn_x, btn_y, btn_tl, btn_tr, btn_zl, btn_zr, btn_thumbl, btn_thumbr = libwiimote.WiiDataParser.parseProController(self.wiimotedev, payload)		
			values[pd.BTN_A] = btn_a
			values[pd.BTN_B] = btn_b
			values[pd.BTN_X] = btn_x
			values[pd.BTN_Y] = btn_y
			values[pd.BTN_LEFT] = btn_left
			values[pd.BTN_RIGHT] = btn_right
			values[pd.BTN_UP] = btn_up
			values[pd.BTN_DOWN] = btn_down
			values[pd.BTN_MINUS] = btn_minus
			values[pd.BTN_HOME] = btn_home
			values[pd.BTN_PLUS] = btn_plus
			values[pd.BTN_TL] = btn_tl
			values[pd.BTN_TR] = btn_tr
			values[pd.BTN_ZL] = btn_zl
			values[pd.BTN_ZR] = btn_zr
			values[pd.AXIS_X] = lx
			values[pd.AXIS_Y] = ly
			values[pd.AXIS_RX] = rx
			values[pd.AXIS_RY] = ry
			values[pd.BTN_THUMBL] = btn_thumbl
			values[pd.BTN_THUMBR] = btn_thumbr
			
			# Compute PRO controller dead zones
			in_dz = compute_deadzone(self.mapping.mapping[pd.AXIS_X], self.mapping.mapping[pd.AXIS_Y], 
							pd.abs_params[pd.AXIS_X].max, pd.abs_params[pd.AXIS_Y].max, lx, ly)
			if in_dz:
				lx = 0
				ly = 0
				values[pd.AXIS_X] = lx
				values[pd.AXIS_Y] = ly
				
			in_dz = compute_deadzone(self.mapping.mapping[pd.AXIS_RX], self.mapping.mapping[pd.AXIS_RY], 
							pd.abs_params[pd.AXIS_RX].max, pd.abs_params[pd.AXIS_RY].max, rx, ry)
			if in_dz:
				rx = 0
				ry = 0
				values[pd.AXIS_RX] = rx
				values[pd.AXIS_RY] = ry
			
		elif self.profile == PROFILE_CLASSIC_CONTROLLER:
			lx, ly, rx, ry, lt, rt, btn_left, btn_right, btn_up, btn_down, btn_minus, btn_home, btn_plus, btn_a, btn_b, btn_x, btn_y, btn_lt, btn_rt, btn_zl, btn_zr = libwiimote.WiiDataParser.parseClassic(self.wiimotedev, payload)
			values[pd.BTN_A] = btn_a
			values[pd.BTN_B] = btn_b
			values[pd.BTN_X] = btn_x
			values[pd.BTN_Y] = btn_y
			values[pd.BTN_LEFT] = btn_left
			values[pd.BTN_RIGHT] = btn_right
			values[pd.BTN_UP] = btn_up
			values[pd.BTN_DOWN] = btn_down
			values[pd.BTN_MINUS] = btn_minus
			values[pd.BTN_HOME] = btn_home
			values[pd.BTN_PLUS] = btn_plus
			values[pd.BTN_TL] = btn_lt
			values[pd.BTN_TR] = btn_rt
			values[pd.BTN_ZL] = btn_zl
			values[pd.BTN_ZR] = btn_zr
			values[pd.AXIS_X] = lx
			values[pd.AXIS_Y] = ly
			values[pd.AXIS_RX] = rx
			values[pd.AXIS_RY] = ry
			values[pd.AXIS_LT] = lt
			values[pd.AXIS_RT] = rt
			# Compute classic controller dead zones
			in_dz = compute_deadzone(self.mapping.mapping[pd.AXIS_X], self.mapping.mapping[pd.AXIS_Y], 
							pd.abs_params[pd.AXIS_X].max, pd.abs_params[pd.AXIS_Y].max, lx, ly)
			if in_dz:
				lx = 0
				ly = 0
				values[pd.AXIS_X] = lx
				values[pd.AXIS_Y] = ly
				
			in_dz = compute_deadzone(self.mapping.mapping[pd.AXIS_RX], self.mapping.mapping[pd.AXIS_RY], 
							pd.abs_params[pd.AXIS_RX].max, pd.abs_params[pd.AXIS_RY].max, rx, ry)
			if in_dz:
				rx = 0
				ry = 0
				values[pd.AXIS_RX] = rx
				values[pd.AXIS_RY] = ry
			
		elif self.profile == PROFILE_WIIMOTE_NUNCHUK:
			bx, by, x, y, z, btn_c, btn_z = libwiimote.WiiDataParser.parseNunchuk(self.wiimotedev, payload)
			values[pd.BTN_Z] = btn_z
			values[pd.BTN_C] = btn_c
			values[pd.AXIS_X] = bx
			values[pd.AXIS_Y] = by
			values[pd.ACCEL_NX] = x
			values[pd.ACCEL_NY] = y
			values[pd.ACCEL_NZ] = z
			# BTN_NSHAKE
			_map = self.mapping.mapping[pd.BTN_NSHAKE]
			if _map != None:
				_sens = 260
				if isinstance(_map, mapping.ButtonMapping) and _map.sensitivity > 0:
					_sens = _map.sensitivity
				val = 1 if (z < -_sens or z > _sens) else 0
				self.send_event(_map, val, pd.axis[pd.BTN_NSHAKE])
			# Compute nunchuk dead zone
			in_dz = compute_deadzone(self.mapping.mapping[pd.AXIS_X], self.mapping.mapping[pd.AXIS_Y], 
							pd.abs_params[pd.AXIS_X].max, pd.abs_params[pd.AXIS_Y].max, bx, by)
			if in_dz:
				bx = 0
				by = 0
				values[pd.AXIS_X] = bx
				values[pd.AXIS_Y] = by
			
		# Send events
		for k in values.keys():
			index = k
			v = values[k]
			_map = self.mapping.mapping[index]
			if _map == None:
				continue
			_abs = None
			if pd.axis[index]:
				_abs = pd.abs_params[index]
			self.send_event(_map, v, pd.axis[index], _abs=_abs)
	
	def handler_sync(self):
		if not self.initialized or self.uinputdev == None:
			return
		self.uinputdev.send_sync()
	
	def send_event(self, _map, value, isNaturalAxis, _abs=None):
		if _map._type == uinputdefs.EV_ABS and not isNaturalAxis:
			# Axis emulation with button
			ev = getevent(_map._type, _map._code[0], 1 if value else -1)
		elif _map._type == uinputdefs.EV_KEY and isNaturalAxis:
			# Button emulation with axis
			_sens = 30
			if isinstance(_map, mapping.ButtonMapping) and _map.sensitivity != None:
				_sens = _map.sensitivity
			ev = getevent(_map._type, _map._code[0], 1 if value>_sens else 0)
		elif isNaturalAxis:
			# Axis - Axis
			if isinstance(_map, mapping.AxisMapping) and _abs != None:
				# Apply axis inversion
				if _map.isInverted:
					value = -value
				# Apply axis scale
				if _map.sourceScale != None and _map.sourceScale > 0 and _abs != None:
					_max = _abs.max
					_scalef = _max / float(_map.sourceScale)
					value = int(_scalef*value)
				# Apply 1 axis to 2 axis
				if len(_map._code) >= 2 and value > 0:
					ev = getevent(_map._type, _map._code[1], value-(_abs.max/2))
					self.uinputdev.send_event(ev)
					ev = getevent(_map._type, _map._code[0], _abs.min)
					self.uinputdev.send_event(ev)
					return
				elif len(_map._code) >= 2 and value < 0:
					ev = getevent(_map._type, _map._code[0], (-value)-(_abs.max/2))
					self.uinputdev.send_event(ev)
					ev = getevent(_map._type, _map._code[1], _abs.min)
					self.uinputdev.send_event(ev)
					return
				elif len(_map._code) >= 2 and value == 0:
					ev = getevent(_map._type, _map._code[0], _abs.min)
					self.uinputdev.send_event(ev)
					ev = getevent(_map._type, _map._code[1], _abs.min)
					self.uinputdev.send_event(ev)
					return
			ev = getevent(_map._type, _map._code[0], value)
		else:
			# Button - Button
			ev = getevent(_map._type, _map._code[0], 1 if value else 0)
		self.uinputdev.send_event(ev)
	
	def extension_change(self):
		if not self.initialized:
			return
		logging.debug("UNPUT: Extension notification!!")
		if self.wiimotedev.state.extension != self.uinputextension:
			logging.debug("UNPUT: Extension changed!!")
			self.uinputdev.__del__()
			self.initialized = False
			self.initializeDevice()
		
	def device_disconnected(self):
		if not self.initialized:
			return
		logging.debug("UINPUT: Disconnected!!")
		print(self.prettyName+" disconnected (player %d)."%self.led)
		self.uinputdev.__del__()
		if self.disconnectCallback != None:
			self.disconnectCallback(self)
		
	def disconnect(self):
		self.wiimotedev.disconnect(block=True)
		self.uinputdev.__del__()
		
	def update_profile_status(self):
		if self.wiimotedev.isProController():
			self.uinput_name = "Nintendo Wii Remote Pro Controller"
			self.profile = PROFILE_PRO_CONTROLLER
		elif self.wiimotedev.isBalanceBoard():
			self.uinput_name = "Nintendo Wii Remote"
			self.profile = PROFILE_BALANCE_BOARD
		elif self.wiimotedev.isWiimotePlus():
			self.uinput_name = "Nintendo Wii Remote"
			self.profile = PROFILE_WIIMOTE
		elif self.wiimotedev.isWiimote():
			self.uinput_name = "Nintendo Wii Remote"
			self.profile = PROFILE_WIIMOTE
			
		if self.wiimotedev.hasNunchuk():
			self.uinput_name = "Nintendo Wii Remote"
			self.profile = PROFILE_WIIMOTE_NUNCHUK
		elif self.wiimotedev.hasClassicController() or self.wiimotedev.hasClassicControllerPro():
			self.uinput_name = "Nintendo Wii Remote Classic Controller"
			self.profile = PROFILE_CLASSIC_CONTROLLER
			
		# Enable wiimote accelerometer and/or extension
		if self.profile == PROFILE_WIIMOTE or self.profile == PROFILE_WIIMOTE_NUNCHUK:
			self.wiimotedev.enableAccel()
		if self.profile == PROFILE_PRO_CONTROLLER or self.profile == PROFILE_CLASSIC_CONTROLLER or self.profile == PROFILE_WIIMOTE_NUNCHUK or self.profile == PROFILE_BALANCE_BOARD:
			self.wiimotedev.enableExtension()
		
	def create_uinput_dev(self):
		self.uinputextension = self.wiimotedev.state.extension
		# Product code selection
		productCode = 0x0001
		if self.wiimotedev.state.device == libwiimote.WiiDevType.WIIMOTE_DEV_GEN10:
			productCode = 0x0306
		elif self.wiimotedev.state.device == libwiimote.WiiDevType.WIIMOTE_DEV_GEN20:
			productCode = 0x0330
		elif self.wiimotedev.state.device == libwiimote.WiiDevType.WIIMOTE_DEV_PRO_CONTROLLER:
			productCode = 0x0330

		self.uinputdev = libuinput.UInputDevice(name=self.uinput_name, bustype=uinputdefs.BUS_BLUETOOTH, vendor=0x057e, product=productCode, version=0x01)
		self.uinputdev.enable_event_type(uinputdefs.EV_ABS)
		self.uinputdev.enable_event_type(uinputdefs.EV_KEY)
		pd = self.mapping.description
		if pd == None:
			logging.warning("UInput device could not be created. Bad Profile.")
			return
		index = -1
		for _map in self.mapping.mapping[:]:
			index+=1
			if _map == None:
				continue
			_type = _map._type
			_code = _map._code
			if _type == None or _code == None:
				continue
			# Enable mapped button/axis
			for _c in _code:
				self.uinputdev.enable_event(_type, _c)

			# Setup ABS Axis if needed
			if len(_code) <= 1 and _type == uinputdefs.EV_ABS and pd.axis[index]:
				# Without axis emulation
				_abs = pd.abs_params[index]
				self.uinputdev.set_absprops(_code[0], _abs.max, _abs.min, _abs.fuzz, _abs.flat)
			elif len(_code) <= 1 and _type == uinputdefs.EV_ABS and not pd.axis[index]:
				# AXIS emulation with button
				self.uinputdev.set_absprops(_code[0], _max=1, _min=-1, _fuzz=0, _flat=0)
			elif len(_code) >= 2 and _type == uinputdefs.EV_ABS and pd.axis[index]:
				# 1 AXIS to 2 AXIS
				_abs = pd.abs_params[index]
				self.uinputdev.set_absprops(_code[0], _abs.max/2, _abs.min/2, _abs.fuzz, _abs.flat)
				self.uinputdev.set_absprops(_code[1], _abs.max/2, _abs.min/2, _abs.fuzz, _abs.flat)
	
		self.uinputdev.setup()


# MAIN (for testing purposes)
if __name__ == "__main__":
	profile = fileutils.readMappingFromFile("360_mapping.map")
	devices = bluetooth.discover_devices(duration=2, lookup_names = True)
	print("Found %d devices." % len(devices))
	for d in devices[:]:
		if "Nintendo RVL-CNT-01" in d[1] or "Nintendo RVL-WBC-01" in d[1]:
			print("Found Controller: %s" % d[0])
			w = UInputWiimote(d[0], d[1], profile)
	
	from gi.repository import GObject
	GObject.MainLoop().run()
		