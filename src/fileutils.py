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
import re
import logging

import uinputdefs
from mapping import WiimoteDescription,NunchukDescription,ClassicControllerDescription, ProControllerDescription, MappingProfile, Mapping, ButtonMapping, AxisMapping

PrettyMappingNames = {
	"XBOX360_A": "BTN_A",
	"XBOX360_B": "BTN_B",
	"XBOX360_X": "BTN_X",
	"XBOX360_Y": "BTN_Y",
	"XBOX360_BACK": "BTN_SELECT",
	"XBOX360_GUIDE": "BTN_MODE",
	"XBOX360_START": "BTN_START",
	"XBOX360_UP": "BTN_DPAD_UP",
	"XBOX360_DOWN": "BTN_DPAD_DOWN",
	"XBOX360_LEFT": "BTN_DPAD_LEFT",
	"XBOX360_RIGHT": "BTN_DPAD_RIGHT",
	"XBOX360_LB": "BTN_TL",
	"XBOX360_RB": "BTN_TR",
	"XBOX360_LT": "ABS_Z",
	"XBOX360_RT": "ABS_RZ",
	"XBOX360_LEFT_STICK_X": "ABS_X",
	"XBOX360_LEFT_STICK_Y": "ABS_Y",
	"XBOX360_RIGHT_STICK_X": "ABS_RX",
	"XBOX360_RIGHT_STICK_Y": "ABS_RY",
	"XBOX360_LEFT_STICK": "BTN_THUMBL",
	"XBOX360_RIGHT_STICK": "BTN_THUMBR"
}

# Descriptor-file mapping
WiimoteFileDescription = {
	"wiimote.a": WiimoteDescription.BTN_A,
	"wiimote.b": WiimoteDescription.BTN_B,
	"wiimote.one": WiimoteDescription.BTN_1,
	"wiimote.two": WiimoteDescription.BTN_2,
	"wiimote.minus": WiimoteDescription.BTN_MINUS,
	"wiimote.home": WiimoteDescription.BTN_HOME,
	"wiimote.plus": WiimoteDescription.BTN_PLUS,
	"wiimote.left": WiimoteDescription.BTN_LEFT,
	"wiimote.right": WiimoteDescription.BTN_RIGHT,
	"wiimote.up": WiimoteDescription.BTN_UP,
	"wiimote.down": WiimoteDescription.BTN_DOWN,
	"wiimote.accel_x": WiimoteDescription.ACCEL_X,
	"wiimote.accel_y": WiimoteDescription.ACCEL_Y,
	"wiimote.accel_z": WiimoteDescription.ACCEL_Z,
	"wiimote.shake": WiimoteDescription.BTN_SHAKE
}
WiimoteNunchuckFileDescription = {
	"wiimotenunchuk.a": NunchukDescription.BTN_A,
	"wiimotenunchuk.b": NunchukDescription.BTN_B,
	"wiimotenunchuk.one": NunchukDescription.BTN_1,
	"wiimotenunchuk.two": NunchukDescription.BTN_2,
	"wiimotenunchuk.minus": NunchukDescription.BTN_MINUS,
	"wiimotenunchuk.home": NunchukDescription.BTN_HOME,
	"wiimotenunchuk.plus": NunchukDescription.BTN_PLUS,
	"wiimotenunchuk.left": NunchukDescription.BTN_LEFT,
	"wiimotenunchuk.right": NunchukDescription.BTN_RIGHT,
	"wiimotenunchuk.up": NunchukDescription.BTN_UP,
	"wiimotenunchuk.down": NunchukDescription.BTN_DOWN,
	"wiimotenunchuk.accel_x": NunchukDescription.ACCEL_X,
	"wiimotenunchuk.accel_y": NunchukDescription.ACCEL_Y,
	"wiimotenunchuk.accel_z": NunchukDescription.ACCEL_Z,
	"wiimotenunchuk.shake": NunchukDescription.BTN_SHAKE,
	"wiimotenunchuk.nunchuk.accel_x": NunchukDescription.ACCEL_NX,
	"wiimotenunchuk.nunchuk.accel_y": NunchukDescription.ACCEL_NY,
	"wiimotenunchuk.nunchuk.accel_z": NunchukDescription.ACCEL_NZ,
	"wiimotenunchuk.nunchuk.c": NunchukDescription.BTN_C,
	"wiimotenunchuk.nunchuk.z": NunchukDescription.BTN_Z,
	"wiimotenunchuk.nunchuk.axis_x": NunchukDescription.AXIS_X,
	"wiimotenunchuk.nunchuk.axis_y": NunchukDescription.AXIS_Y,
	"wiimotenunchuk.nunchuk.shake": NunchukDescription.BTN_NSHAKE
}
ClassicFileDescription = {
	"classic.a": ClassicControllerDescription.BTN_A,
	"classic.b": ClassicControllerDescription.BTN_B,
	"classic.x": ClassicControllerDescription.BTN_X,
	"classic.y": ClassicControllerDescription.BTN_Y,
	"classic.left": ClassicControllerDescription.BTN_LEFT,
	"classic.right": ClassicControllerDescription.BTN_RIGHT,
	"classic.up": ClassicControllerDescription.BTN_UP,
	"classic.down": ClassicControllerDescription.BTN_DOWN,
	"classic.minus": ClassicControllerDescription.BTN_MINUS,
	"classic.home": ClassicControllerDescription.BTN_HOME,
	"classic.plus": ClassicControllerDescription.BTN_PLUS,
	"classic.axis_x": ClassicControllerDescription.AXIS_X,
	"classic.axis_y": ClassicControllerDescription.AXIS_Y,
	"classic.axis_rx": ClassicControllerDescription.AXIS_RX,
	"classic.axis_ry": ClassicControllerDescription.AXIS_RY,
	"classic.axis_lt": ClassicControllerDescription.AXIS_LT,
	"classic.axis_rt": ClassicControllerDescription.AXIS_RT,
	"classic.lt": ClassicControllerDescription.BTN_TL,
	"classic.rt": ClassicControllerDescription.BTN_TR,
	"classic.zl": ClassicControllerDescription.BTN_ZL,
	"classic.zr": ClassicControllerDescription.BTN_ZR
}

ProFileDescription = {
	"pro.a": ProControllerDescription.BTN_A,
	"pro.b": ProControllerDescription.BTN_B,
	"pro.x": ProControllerDescription.BTN_X,
	"pro.y": ProControllerDescription.BTN_Y,
	"pro.left": ProControllerDescription.BTN_LEFT,
	"pro.right": ProControllerDescription.BTN_RIGHT,
	"pro.up": ProControllerDescription.BTN_UP,
	"pro.down": ProControllerDescription.BTN_DOWN,
	"pro.minus": ProControllerDescription.BTN_MINUS,
	"pro.home": ProControllerDescription.BTN_HOME,
	"pro.plus": ProControllerDescription.BTN_PLUS,
	"pro.axis_x": ProControllerDescription.AXIS_X,
	"pro.axis_y": ProControllerDescription.AXIS_Y,
	"pro.axis_rx": ProControllerDescription.AXIS_RX,
	"pro.axis_ry": ProControllerDescription.AXIS_RY,
	"pro.lt": ProControllerDescription.BTN_TL,
	"pro.rt": ProControllerDescription.BTN_TR,
	"pro.zl": ProControllerDescription.BTN_ZL,
	"pro.zr": ProControllerDescription.BTN_ZR,
	"pro.lthumb": ProControllerDescription.BTN_THUMBL,
	"pro.rthumb": ProControllerDescription.BTN_THUMBR
}

class InvalidMappingFileException(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

def translateMappingPrettyNames(_maps):
	_tmaps = []
	for onemap in _maps[:]:
		if onemap in PrettyMappingNames:
			onemap = PrettyMappingNames[onemap]
		_tmaps.append(onemap)
	return _tmaps

def checkTargetMapping(_maps):
	ss = None
	if "KEY_" in _maps[0]:
		ss = "KEY_"
	elif "ABS_" in _maps[0]:
		ss = "ABS_"
	elif "BTN_" in _maps[0]:
		ss = "BTN_"
	else:
		raise Exception("Only KEY_/ABS_/BTN_ allowed")
	for _map in _maps[2:]:
		if not ss in _map:
			raise Exception("")
			
def parseTargetMap(_maps):
	_sysmap = [None]*len(_maps)
	i = -1
	for v in _maps:
		i += 1
		_sysmap[i] = eval("uinputdefs."+v)
	return _sysmap

def getDescriptionForMap(_map):
	if _map in WiimoteFileDescription:
		return WiimoteFileDescription[_map], WiimoteFileDescription
	elif _map in WiimoteNunchuckFileDescription:
		return WiimoteNunchuckFileDescription[_map], WiimoteNunchuckFileDescription
	elif _map in ClassicFileDescription:
		return ClassicFileDescription[_map], ClassicFileDescription
	elif _map in ProFileDescription:
		return ProFileDescription[_map], ProFileDescription
	return None, None

def readMappingFromFile(filePath):
	profileName = None
	wiimoteMapping = None
	wiimoteNunchuckMapping = None
	classicMapping = None
	proMapping = None
	content = None
	with open(filePath) as f:
		content = f.readlines()
		
	if content==None or len(content)<=0:
		raise InvalidMappingFileException(filePath)
		
	sensP = re.compile('\^[0-9]+')
	dzP = re.compile('%[0-9]+')
	mapP = re.compile('[a-z0-9_]+(,[a-z0-9_]+){0,1}')
	
	for l in content[:]:
		if "profile.name" in l.lower():
			l, c, r = l.rstrip().partition("=")
			r = r.replace("\"", "", 999).strip()
			profileName = r
			continue
		s = l.lower().replace("profile.", "").replace(" ", "", 999).rstrip()
		if len(s)<=0 or s[0] == "#":
			continue
		el, sep, _map = s.partition("=")
		# Sens match
		s = sensP.search(_map)
		ssen = 0
		if s!=None:
			ssen = int(s.group()[1:])
		# Dead zone match
		d = dzP.search(_map)
		ddz = 0
		if d!=None:
			ddz = int(d.group()[1:])
		if ddz < 0 or ddz > 100:
			ddz = 0
		# Inverted
		inverted = "inverted" in _map.lower()
		m = mapP.search(_map)
		if m == None:
			logging.warning("Invalid source mapping assignment: "+l)
			continue
		mm = m.group().upper()
		# Map to 2 axis
		_maps = []
		if "," in mm:
			ax1, sep, ax2 = mm.partition(",")
			_maps.append(ax1)
			_maps.append(ax2)
		else:
			_maps.append(mm)
		ignore = False
		# Translate pretty names into input.h names
		_maps = translateMappingPrettyNames(_maps)
		# Validate mapping
		for onemap in _maps[:]:
			# Try to translate from pretty names
			try:
				eval("uinputdefs."+onemap)
			except:
				logging.warning("Invalid target mapping assignment: "+l)
				ignore = True
				break
		if ignore:
			continue
		# "el" is the controller button/axis, "_maps" is the uinput mapped button/axis
		# "ssen" = sensitivity, "ddz" = dead zone
		try:
			checkTargetMapping(_maps)
		except Exception:
			logging.warning("Invalid target mapping assignment: "+l)
			continue
		_mapinst = None
		_sysmaps = parseTargetMap(_maps)
		if "BTN_" in _maps[0] or "KEY_" in _maps[0]:
			_mapinst = ButtonMapping(_sysmaps, sensitivity=ssen)
		elif "ABS_" in _maps[0]:
			_mapinst = AxisMapping(_sysmaps, sourceScale=ssen, deadZone=ddz, isInverted=inverted)
		else:
			logging.warning("Invalid target mapping assignment: "+l)
			continue
		val, desc = getDescriptionForMap(el)
		if desc == WiimoteFileDescription:
			if wiimoteMapping == None:
				wiimoteMapping = Mapping(WiimoteDescription)
			wiimoteMapping.setMap(val, _mapinst)
		elif desc == WiimoteNunchuckFileDescription:
			if wiimoteNunchuckMapping == None:
				wiimoteNunchuckMapping = Mapping(NunchukDescription)
			wiimoteNunchuckMapping.setMap(val, _mapinst)
		elif desc == ClassicFileDescription:
			if classicMapping == None:
				classicMapping = Mapping(ClassicControllerDescription)
			classicMapping.setMap(val, _mapinst)
		elif desc == ProFileDescription:
			if proMapping == None:
				proMapping = Mapping(ProControllerDescription)
			proMapping.setMap(val, _mapinst)
	_prof = MappingProfile(name=profileName, wiimoteMapping=wiimoteMapping, wiimoteNunchuckMapping=wiimoteNunchuckMapping,
						classicMapping=classicMapping, proMapping=proMapping)
	logging.info("Loaded profile: "+_prof.name)
	return _prof