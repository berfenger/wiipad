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
import threading
import select
import time
import sys
import logging
import array

if sys.version_info < (3, 0):
	import Queue as queue
	socket_to_bytearray = lambda x: map(ord, x)
else:
	import queue
	socket_to_bytearray = lambda x: x

def i2bs(val):
	lst = []
	while val:
		lst.append(val&0xff)
		val = val >> 8
	lst.reverse()
	return lst

class WiiProtoState:
	FLAG_LED_1 = 0x01
	FLAG_LED_2 = 0x02
	FLAG_LED_3 = 0x04
	FLAG_LED_4 = 0x08
	FLAG_RUMBLE = 0x10
	FLAG_ACCEL = 0x20
	FLAG_IR_BASIC = 0x40
	FLAG_IR_EXT = 0x80
	FLAG_IR_FULL = 0xc0 # IR_BASIC | IR_EXT
	FLAG_EXT_PLUGGED = 0x0100
	FLAG_EXT_USED = 0x0200
	FLAG_EXT_ACTIVE = 0x0400
	FLAG_MP_PLUGGED = 0x0800
	FLAG_MP_USED = 0x1000
	FLAG_MP_ACTIVE = 0x2000
	FLAG_BUILTIN_MP = 0x010000
	FLAG_NO_MP = 0x020000
	FLAG_PRO_CALIB_DONE = 0x040000

class WiiProtoReqs:
	WIIPROTO_REQ_NULL = 0x0
	WIIPROTO_REQ_RUMBLE = 0x10
	WIIPROTO_REQ_LED = 0x11
	WIIPROTO_REQ_DRM = 0x12
	WIIPROTO_REQ_IR1 = 0x13
	WIIPROTO_REQ_SREQ = 0x15
	WIIPROTO_REQ_WMEM = 0x16
	WIIPROTO_REQ_RMEM = 0x17
	WIIPROTO_REQ_IR2 = 0x1a
	WIIPROTO_REQ_STATUS = 0x20
	WIIPROTO_REQ_DATA = 0x21
	WIIPROTO_REQ_RETURN = 0x22

	# DRM_K: BB*2 
	WIIPROTO_REQ_DRM_K = 0x30

	# DRM_KA: BB*2 AA*3 
	WIIPROTO_REQ_DRM_KA = 0x31

	# DRM_KE: BB*2 EE*8 
	WIIPROTO_REQ_DRM_KE = 0x32

	# DRM_KAI: BB*2 AA*3 II*12 
	WIIPROTO_REQ_DRM_KAI = 0x33

	# DRM_KEE: BB*2 EE*19 
	WIIPROTO_REQ_DRM_KEE = 0x34

	# DRM_KAE: BB*2 AA*3 EE*16 
	WIIPROTO_REQ_DRM_KAE = 0x35

	# DRM_KIE: BB*2 II*10 EE*9 
	WIIPROTO_REQ_DRM_KIE = 0x36

	# DRM_KAIE: BB*2 AA*3 II*10 EE*6 
	WIIPROTO_REQ_DRM_KAIE = 0x37

	# DRM_E: EE*21 
	WIIPROTO_REQ_DRM_E = 0x3d

	# DRM_SKAI1: BB*2 AA*1 II*18 
	WIIPROTO_REQ_DRM_SKAI1 = 0x3e

	# DRM_SKAI2: BB*2 AA*1 II*18 
	WIIPROTO_REQ_DRM_SKAI2 = 0x3f

class WiiDevType:
	WIIMOTE_DEV_UNKNOWN = 0
	WIIMOTE_DEV_GENERIC = 1
	WIIMOTE_DEV_GEN10 = 2
	WIIMOTE_DEV_GEN20 = 3
	WIIMOTE_DEV_BALANCE_BOARD = 4
	WIIMOTE_DEV_PRO_CONTROLLER = 5
	
class WiiDevExtension:
	WIIMOTE_EXT_NONE = 0
	WIIMOTE_EXT_UNKNOWN = 1
	WIIMOTE_EXT_NUNCHUK = 2
	WIIMOTE_EXT_CLASSIC_CONTROLLER = 3
	WIIMOTE_EXT_CLASSIC_CONTROLLER_PRO = 4
	WIIMOTE_EXT_BALANCE_BOARD = 5
	WIIMOTE_EXT_PRO_CONTROLLER = 6
	
class WiiMPMode:
	WIIMOTE_MP_NONE = 0
	WIIMOTE_MP_UNKNOWN = 1
	WIIMOTE_MP_SINGLE = 2
	WIIMOTE_MP_PASSTHROUGH_NUNCHUK = 3
	WIIMOTE_MP_PASSTHROUGH_CLASSIC = 4
	
class WiiDeviceState:
	send_command = threading.RLock()
	command_ready = threading.Condition()
	cmd_type = WiiProtoReqs.WIIPROTO_REQ_NULL
	cmd_buffer = []
	cmd_error = 0
	cmd_battery = 0xff
	flags = 0x0000
	device = WiiDevType.WIIMOTE_DEV_UNKNOWN
	extension = WiiDevExtension.WIIMOTE_EXT_NONE
	lastpoll = 0
	calib_pro_sticks = [0, 0, 0, 0]

def getDeviceName(device):
	name = ""
	if device.state.device == WiiDevType.WIIMOTE_DEV_GEN10:
		name = "Wiimote"
	elif device.state.device == WiiDevType.WIIMOTE_DEV_GEN20:
		name = "Wiimote Plus"
	elif device.state.device == WiiDevType.WIIMOTE_DEV_BALANCE_BOARD:
		name = "Balance Board"
	elif device.state.device == WiiDevType.WIIMOTE_DEV_PRO_CONTROLLER:
		name = "WiiU Pro Controller"
	if device.state.extension == WiiDevExtension.WIIMOTE_EXT_CLASSIC_CONTROLLER_PRO:
		name += " + Classic Controller Pro"
	elif device.state.extension == WiiDevExtension.WIIMOTE_EXT_CLASSIC_CONTROLLER:
		name += " + Classic Controller"
	elif device.state.extension == WiiDevExtension.WIIMOTE_EXT_NUNCHUK:
		name += " + Nunchuk"
	return name		
		
class WiiDataParser():
	@staticmethod
	def parseBalanceBoardKeys(device, payload):
		btn_a = not not(payload[1] & 0x08)
		return btn_a

	@staticmethod
	def parseWiimoteKeys(device, payload):
		btn_left = not not (payload[0] & 0x01)
		btn_right = not not (payload[0] & 0x02)
		btn_down = not not (payload[0] & 0x04)
		btn_up = not not (payload[0] & 0x08)
		
		btn_plus = not not (payload[0] & 0x10)
		btn_2 = not not (payload[1] & 0x01)
		btn_1 = not not (payload[1] & 0x02)
		btn_b = not not (payload[1] & 0x04)
		btn_a = not not (payload[1] & 0x08)
		btn_minus = not not (payload[1] & 0x10)
		btn_home = not not (payload[1] & 0x80)
		return btn_left, btn_right, btn_up, btn_down, btn_minus, btn_home, btn_plus, btn_a, btn_b, btn_1, btn_2
		
	@staticmethod
	def parseWiimoteAccel(device, accel):
		x = accel[2] << 2
		y = accel[3] << 2
		z = accel[4] << 2
	
		x |= (accel[0] >> 5) & 0x3
		y |= (accel[1] >> 4) & 0x2
		z |= (accel[1] >> 5) & 0x2
		
		if device.state.device == WiiDevType.WIIMOTE_DEV_GEN10:
			x -= 0x1e7
			y -= 0x1e7
			z -= 0x1e7
		else:
			x -= 0x200
			y -= 0x200
			z -= 0x200
		
		return x, y, z
		
	#   Byte |   8    7 |  6    5 |  4    3 |  2 |  1  |
	#   -----+----------+---------+---------+----+-----+
	#    1   |              Button X <7:0>             |
	#    2   |              Button Y <7:0>             |
	#   -----+----------+---------+---------+----+-----+
	#    3   |               Speed X <9:2>             |
	#    4   |               Speed Y <9:2>             |
	#    5   |               Speed Z <9:2>             |
	#   -----+----------+---------+---------+----+-----+
	#    6   | Z <1:0>  | Y <1:0> | X <1:0> | BC | BZ  |
	#   -----+----------+---------+---------+----+-----+
	# Button X/Y is the analog stick. Speed X, Y and Z are the
	# accelerometer data in the same format as the wiimote's accelerometer.
	# The 6th byte contains the LSBs of the accelerometer data.
	# BC and BZ are the C and Z buttons: 0 means pressed
	#
	# If reported interleaved with motionp, then the layout changes. The
	# 5th and 6th byte changes to:
	#   -----+-----------------------------------+-----+
	#    5   |            Speed Z <9:3>          | EXT |
	#   -----+--------+-----+-----+----+----+----+-----+
	#    6   |Z <2:1> |Y <1>|X <1>| BC | BZ | 0  |  0  |
	#   -----+--------+-----+-----+----+----+----+-----+
	# All three accelerometer values lose their LSB. The other data is
	# still available but slightly moved.
	#
	# Center data for button values is 128. Center value for accelerometer
	# values it 512 / 0x200
	@staticmethod
	def parseNunchuk(device, ext):
		# X/Y axis
		bx = ext[0]
		by = ext[1]
		bx -= 128
		by -= 128
		by = -by
		
		# Accelerometer
		x = ext[2] << 2
		y = ext[3] << 2
		z = ext[4] << 2
		
		if device.state.flags & WiiProtoState.FLAG_MP_ACTIVE:
			x |= (ext[5] >> 3) & 0x02
			y |= (ext[5] >> 4) & 0x02
			z &= ~0x4
			z |= (ext[5] >> 5) & 0x06
		else:
			x |= (ext[5] >> 2) & 0x03
			y |= (ext[5] >> 4) & 0x03
			z |= (ext[5] >> 6) & 0x03
		
		x -= 0x200
		y -= 0x200
		z -= 0x200
		
		# Buttons
		btn_z = False
		btn_c = False
		if device.state.flags & WiiProtoState.FLAG_MP_ACTIVE:
			btn_z = not (ext[5] & 0x04)
			btn_c = not (ext[5] & 0x08)
		else:
			btn_z = not (ext[5] & 0x01)
			btn_c = not (ext[5] & 0x02)
			
		return bx, by, x, y, z, btn_c, btn_z
		
	#   Byte |  8  |  7  |  6  |  5  |  4  |  3  |  2  |  1  |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#    1   | RX <5:4>  |              LX <5:0>             |
	#    2   | RX <3:2>  |              LY <5:0>             |
	#   -----+-----+-----+-----+-----------------------------+
	#    3   |RX<1>| LT <5:4>  |         RY <5:1>            |
	#   -----+-----+-----------+-----------------------------+
	#    4   |     LT <3:1>    |         RT <5:1>            |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#    5   | BDR | BDD | BLT | B-  | BH  | B+  | BRT |  1  |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#    6   | BZL | BB  | BY  | BA  | BX  | BZR | BDL | BDU |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	# All buttons are 0 if pressed
	# RX and RY are right analog stick
	# LX and LY are left analog stick
	# LT is left trigger, RT is right trigger
	# BLT is 0 if left trigger is fully pressed
	# BRT is 0 if right trigger is fully pressed
	# BDR, BDD, BDL, BDU form the D-Pad with right, down, left, up buttons
	# BZL is left Z button and BZR is right Z button
	# B-, BH, B+ are +, HOME and - buttons
	# BB, BY, BA, BX are A, B, X, Y buttons
	# LSB of RX, RY, LT, and RT are not transmitted and always 0.
	#
	# With motionp enabled it changes slightly to this:
	#   Byte |  8  |  7  |  6  |  5  |  4  |  3  |  2  |  1  |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#    1   | RX <5:4>  |          LX <5:1>           | BDU |
	#    2   | RX <3:2>  |          LY <5:1>           | BDL |
	#   -----+-----+-----+-----+-----------------------+-----+
	#    3   |RX<1>| LT <5:4>  |         RY <5:1>            |
	#   -----+-----+-----------+-----------------------------+
	#    4   |     LT <3:1>    |         RT <5:1>            |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#    5   | BDR | BDD | BLT | B-  | BH  | B+  | BRT | EXT |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#    6   | BZL | BB  | BY  | BA  | BX  | BZR |  0  |  0  |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	# Only the LSBs of LX and LY are lost. BDU and BDL are moved, the rest
	# is the same as before.
	@staticmethod
	def parseClassic(device, ext):
		mp = device.state.flags & WiiProtoState.FLAG_MP_ACTIVE
		rx = 0; ry = 0; lx = 0; ly = 0; lt = 0; rt = 0
		
		if mp:
			lx = ext[0] & 0x3e
			ly = ext[1] & 0x3e
		else:
			lx = ext[0] & 0x3f
			ly = ext[1] & 0x3f
			
		rx = (ext[0] >> 3) & 0x18
		rx |= (ext[1] >> 5) & 0x06
		rx |= (ext[2] >> 7) & 0x01
		ry = ext[2] & 0x1f
	
		rt = ext[3] & 0x1f
		lt = (ext[2] >> 2) & 0x18
		lt |= (ext[3] >> 5) & 0x07
	
		rx <<= 1
		ry <<= 1
		rt <<= 1
		lt <<= 1
		
		rx -= 0x20
		lx -= 0x20
		ry -= 0x20
		ly -= 0x20
		ly = -ly
		ry = -ry
		lt = lt - 30
		rt = rt - 30
		
		btn_right = not (ext[4] & 0x80)
		btn_down = not (ext[4] & 0x40)
		btn_lt = not (ext[4] & 0x20)
		btn_minus = not (ext[4] & 0x10)
		btn_home = not (ext[4] & 0x08)
		btn_plus = not (ext[4] & 0x04)
		btn_rt = not (ext[4] & 0x02)
		btn_zl = not (ext[5] & 0x80)
		btn_b = not (ext[5] & 0x40)
		btn_y = not (ext[5] & 0x20)
		btn_a = not (ext[5] & 0x10)
		btn_x = not (ext[5] & 0x08)
		btn_zr = not (ext[5] & 0x04)
		btn_up = False
		btn_left = False
		if mp:
			btn_left = not (ext[1] & 0x01)
			btn_up = not (ext[0] & 0x01)
		else:
			btn_left = not (ext[5] & 0x02)
			btn_up = not (ext[5] & 0x01)
			
		return lx, ly, rx, ry, lt, rt, btn_left, btn_right, btn_up, btn_down, btn_minus, btn_home, btn_plus, btn_a, btn_b, btn_x, btn_y, btn_lt, btn_rt, btn_zl, btn_zr
	
	#   Byte |  8  |  7  |  6  |  5  |  4  |  3  |  2  |  1  |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#    1   |                   LX <7:0>                    |
	#   -----+-----------------------+-----------------------+
	#    2   |  0     0     0     0  |       LX <11:8>       |
	#   -----+-----------------------+-----------------------+
	#    3   |                   RX <7:0>                    |
	#   -----+-----------------------+-----------------------+
	#    4   |  0     0     0     0  |       RX <11:8>       |
	#   -----+-----------------------+-----------------------+
	#    5   |                   LY <7:0>                    |
	#   -----+-----------------------+-----------------------+
	#    6   |  0     0     0     0  |       LY <11:8>       |
	#   -----+-----------------------+-----------------------+
	#    7   |                   RY <7:0>                    |
	#   -----+-----------------------+-----------------------+
	#    8   |  0     0     0     0  |       RY <11:8>       |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#    9   | BDR | BDD | BLT | B-  | BH  | B+  | BRT |  1  |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#   10   | BZL | BB  | BY  | BA  | BX  | BZR | BDL | BDU |
	#   -----+-----+-----+-----+-----+-----+-----+-----+-----+
	#   11   |  1  |     BATTERY     | USB |CHARG|LTHUM|RTHUM|
	#   -----+-----+-----------------+-----------+-----+-----+
	# All buttons are low-active (0 if pressed)
	# RX and RY are right analog stick
	# LX and LY are left analog stick
	# BLT is left trigger, BRT is right trigger.
	# BDR, BDD, BDL, BDU form the D-Pad with right, down, left, up buttons
	# BZL is left Z button and BZR is right Z button
	# B-, BH, B+ are +, HOME and - buttons
	# BB, BY, BA, BX are A, B, X, Y buttons
	#
	# Bits marked as 0/1 are unknown and never changed during tests.
	#
	# Not entirely verified:
	#   CHARG: 1 if uncharging, 0 if charging
	#   USB: 1 if not connected, 0 if connected
	#   BATTERY: battery capacity from 000 (empty) to 100 (full)
	@staticmethod
	def parseProController(device, ext):
		lx = (ext[0] & 0xff) | ((ext[1] & 0x0f) << 8)
		rx = (ext[2] & 0xff) | ((ext[3] & 0x0f) << 8)
		ly = (ext[4] & 0xff) | ((ext[5] & 0x0f) << 8)
		ry = (ext[6] & 0xff) | ((ext[7] & 0x0f) << 8)
		
		# zero-point offsets 
		lx -= 0x800
		ly = 0x800 - ly
		rx -= 0x800
		ry = 0x800 - ry
		
		# Trivial automatic calibration. We don't know any calibration data
		# in the EEPROM so we must use the first report to calibrate the
		# null-position of the analog sticks. Users can retrigger calibration
		# via sysfs, or set it explicitly. If data is off more than abs(500),
		# we skip calibration as the sticks are likely to be moved already. 
		if not (device.state.flags & WiiProtoState.FLAG_PRO_CALIB_DONE):
			device.state.flags |= WiiProtoState.FLAG_PRO_CALIB_DONE
			if abs(lx) < 500:
				device.state.calib_pro_sticks[0] = -lx
			if abs(ly) < 500:
				device.state.calib_pro_sticks[1] = -ly
			if abs(rx) < 500:
				device.state.calib_pro_sticks[2] = -rx
			if abs(ry) < 500:
				device.state.calib_pro_sticks[3] = -ry
		
		
		# apply calibration data 
		lx += device.state.calib_pro_sticks[0]
		ly += device.state.calib_pro_sticks[1]
		rx += device.state.calib_pro_sticks[2]
		ry += device.state.calib_pro_sticks[3]
		
		btn_right = not (ext[8] & 0x80)
		btn_down = not (ext[8] & 0x40)
		btn_tl = not (ext[8] & 0x20)
		btn_minus = not (ext[8] & 0x10)
		btn_home = not (ext[8] & 0x08)
		btn_plus = not (ext[8] & 0x04)
		btn_tr = not (ext[8] & 0x02)
		
		btn_zl = not (ext[9] & 0x80)
		btn_b = not (ext[9] & 0x40)
		btn_y = not (ext[9] & 0x20)
		btn_a = not (ext[9] & 0x10)
		btn_x = not (ext[9] & 0x08)
		btn_zr = not (ext[9] & 0x04)
		btn_left = not (ext[9] & 0x02)
		btn_up = not (ext[9] & 0x01)
		
		btn_thumbl = not (ext[10] & 0x02)
		btn_thumbr = not (ext[10] & 0x01)
		
		return lx, ly, rx, ry, btn_left, btn_right, btn_up, btn_down, btn_minus, btn_home, btn_plus, btn_a, btn_b, btn_x, btn_y, btn_tl, btn_tr, btn_zl, btn_zr, btn_thumbl, btn_thumbr
		

class WiiCommandQueue(threading.Thread):
	queue = None
	
	def __init__(self):
		threading.Thread.__init__(self)
		self.devices = []
		self.queue = queue.Queue()
		self.lock = threading.RLock()
		self.running = True
			
	def run(self):
		logging.debug("libwiimote::command_queue::started")
		# poll device to detect device disconnection
		while self.running:
			try:
				device, command = self.queue.get(block=True, timeout=0.5)
				ret = device._send_data(command)
				if ret <= 0:
					device.state.cmd_error = 0xff
					device.state.command_ready.notify()
			except:
				pass
			
			for device in self.devices:
				device.laststatusN += 1
				# Each 5 seconds (or less if there was some commands), check time, and send status request
				if device.laststatusN >= 7:
					if time.time() > device.laststatus:
						device.laststatusN = 0
						device.laststatus = time.time() + 5
						msg = [WiiProtoReqs.WIIPROTO_REQ_SREQ] + [device.wiiproto_cmd_keep_rumble(0x00)]
						try:
							device._send_data(msg)
						except:
							device.disconnect()
					else:
						device.laststatusN = 0
		logging.debug("libwiimote::command_queue::stopped")
			
	def delDevice(self, device):
		with self.lock:
			if device in self.devices:
				self.devices.remove(device)
			if len(self.devices) <= 0:
				self.stop()
			
	def stop(self):
		self.running = False
		global cmd_queue
		cmd_queue = WiiCommandQueue()
		
	def send(self, device, data):
		if not device in self.devices:
			device.laststatus = time.time()
			device.laststatusN = 0
			self.devices.append(device)
		self.queue.put((device, data))
		if not self.isAlive():
			self.start()

class WiiDeviceReceiver(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.devices = []
		self.lock = threading.RLock()
		
	def getDeviceByDataSocket(self, datasocket):
		for d in self.devices[:]:
			if d.datasocket == datasocket:
				return d
		return None
		
	def readFromDataSockets(self):
		sockets = []
		for d in self.devices:
			sockets.append(d.datasocket)
		inputready,outputready,exceptready = select.select(sockets, [], [], 0.5)
		if len(inputready) <= 0:
			raise Exception()
		data = []
		for inr in inputready[:]:
			ev = inr.recv(32)
			x = socket_to_bytearray(ev)
			dev = self.getDeviceByDataSocket(inr)
			if len(ev) <= 0:
				dev.disconnect()
				continue
			data.append((dev, x))
		return data
		
	def run(self):
		logging.debug("libwiimote::receiver::started")
		self.running = True
		while self.running:
			try:
				datas = self.readFromDataSockets()
				for dev, data in datas[:]:
					dev.processInputData(data)
			except:
				pass
			
		logging.debug("libwiimote::receiver::stopped")
	
	def addDevice(self, device):
		if not device in self.devices:
			self.devices.append(device)
			if not self.isAlive():
				self.start()
				
	def delDevice(self, device):
		with self.lock:
			if device in self.devices:
				self.devices.remove(device)
			if len(self.devices) <= 0:
				self.stop()
				
	def stop(self):
		self.running = False
		global receiver
		receiver = WiiDeviceReceiver()

cmd_queue = WiiCommandQueue()
receiver = WiiDeviceReceiver()

def disconnect():
	cmd_queue.stop()
	receiver.stop()

class WiiHandler():
	def __init__(self, code, size, handler):
		self.handler = handler
		self.code = code
		self.size = size
		
	def invoke(self, data):
		self.handler(data)
		
	def isValid(self, code, size):
		return self.code == code and self.size < size
	
class WiiDevice():
	
	extension_change_callback = None
	isDisconnected = False
	isConnected = False
	disconnectLock = threading.RLock()
	
	def __init__(self, address, name, handler_keys, handler_accel, handler_ext, handler_sync, extension_change_callback=None, disconnect_callback=None):

		self.address = address
		self.name = name
		self.state = WiiDeviceState()
		self.extension_change_callback = extension_change_callback
		self.disconnect_callback = disconnect_callback
		
		self.handler_keys_callback = handler_keys
		self.handler_accel_callback = handler_accel
		self.handler_ext_callback = handler_ext
		self.handler_sync_callback = handler_sync
		
		# Event handler setup. Handlers must be sorted: first the one with larger size
		self.handlers = []
		# DRM K
		self.handlers.append(WiiHandler(WiiProtoReqs.WIIPROTO_REQ_DRM_K, 2, self.handler_drm_K))
		# DRM KA
		self.handlers.append(WiiHandler(WiiProtoReqs.WIIPROTO_REQ_DRM_KA, 5, self.handler_drm_KA))
		self.handlers.append(WiiHandler(WiiProtoReqs.WIIPROTO_REQ_DRM_KA, 2, self.handler_drm_K))
		# DRM KAE
		self.handlers.append(WiiHandler(WiiProtoReqs.WIIPROTO_REQ_DRM_KAE, 21, self.handler_drm_KAE))
		self.handlers.append(WiiHandler(WiiProtoReqs.WIIPROTO_REQ_DRM_KAE, 2, self.handler_drm_K))
		# DRM KEE
		self.handlers.append(WiiHandler(WiiProtoReqs.WIIPROTO_REQ_DRM_KEE, 21, self.handler_drm_KEE))
		self.handlers.append(WiiHandler(WiiProtoReqs.WIIPROTO_REQ_DRM_KEE, 2, self.handler_drm_K))
		
	def handler_keys(self, payload):
		# Wiimote buttons and balance board button "A"
		if self.handler_keys_callback != None:
			self.handler_keys_callback(payload)
			
	def handler_accel(self, payload):
		# Wiimote accelerometer
		if self.handler_accel_callback != None:
			self.handler_accel_callback(payload)
			
	def handler_ext(self, payload):
		# Extension data
		if self.handler_ext_callback != None:
			self.handler_ext_callback(payload)
			
	def handler_sync(self):
		# Extension data
		if self.handler_sync_callback != None:
			self.handler_sync_callback()
	
	def handler_drm_K(self, payload):
		self.handler_keys(payload)
		self.handler_sync()
		pass
	def handler_drm_KA(self, payload):
		self.handler_keys(payload)
		self.handler_accel(payload)
		self.handler_sync()
		pass
	def handler_drm_KE(self, payload):
		pass
	def handler_drm_KAI(self, payload):
		pass
	def handler_drm_KEE(self, payload):
		self.handler_keys(payload)
		self.handler_ext(payload[2:])
		self.handler_sync()
		pass
	def handler_drm_KIE(self, payload):
		pass
	def handler_drm_KAE(self, payload):
		self.handler_keys(payload)
		self.handler_accel(payload)
		self.handler_ext(payload[5:])
		self.handler_sync()
		pass
	def handler_drm_KAIE(self, payload):
		pass
	def handler_drm_E(self, payload):
		pass
	def handler_drm_SKAI1(self, payload):
		pass
	def handler_drm_SKAI2(self, payload):
		pass
		
	def setExtensionChangeCallback(self, callback):
		self.extension_change_callback = callback
	
	def _send_data(self,data):
		msg = [self.CMD_SET_REPORT] + list(data)
		str_data = array.array('B', msg).tostring()
		ret = self.sendsocket.send(str_data)
		return ret

	def wiiproto_cmd_wmem(self, address, value, eeprom=False):
		with self.state.send_command:
			with self.state.command_ready:
				val = i2bs(value)
				val_len=len(val)
				val += [0]*(16-val_len)
				mtype = 0x00 if eeprom else 0x04
				msg = [WiiProtoReqs.WIIPROTO_REQ_WMEM] + [mtype] + i2bs(address) + [val_len] +val
				self.state.cmd_type = WiiProtoReqs.WIIPROTO_REQ_WMEM
				cmd_queue.send(self, msg)
				self.state.command_ready.wait()
				error = self.state.cmd_error
				return error
		
	def wiiproto_cmd_rmem(self, address, length, eeprom=False):
		with self.state.send_command:
			with self.state.command_ready:
				val_len=length
				mtype = 0x00 if eeprom else 0x04
				msg = [WiiProtoReqs.WIIPROTO_REQ_RMEM] + [mtype] + i2bs(address) + [(val_len >> 8)& 0xff] + [val_len & 0xff]
				self.state.cmd_type = WiiProtoReqs.WIIPROTO_REQ_RMEM
				cmd_queue.send(self, msg)
				self.state.command_ready.wait()
				# Check if probably desconnected
				if self.state.cmd_error == 0xff:
					return []
				read_data = []
				read_data[:] = self.state.cmd_buffer
				return read_data
				
	def wiiproto_req_status(self):
		with self.state.send_command:
			with self.state.command_ready:
				msg = [WiiProtoReqs.WIIPROTO_REQ_SREQ] + [self.wiiproto_cmd_keep_rumble(0x00)]
				self.state.cmd_type = WiiProtoReqs.WIIPROTO_REQ_STATUS
				cmd_queue.send(self, msg)
				self.state.command_ready.wait()
				# Check if probably desconnected
				if self.state.cmd_error == 0xff:
					return []
				read_data = []
				read_data[:] = self.state.cmd_buffer
				return read_data
	
	def wiiproto_cmd_keep_rumble(self, cmd):
		if self.state.flags & WiiProtoState.FLAG_RUMBLE:
			cmd |= 0x01
		return cmd
	
	def wiiproto_req_led(self):
		ledval = 0x00
		if self.state.flags & WiiProtoState.FLAG_LED_1:
			ledval |= 0x10
		if self.state.flags & WiiProtoState.FLAG_LED_2:
			ledval |= 0x20
		if self.state.flags & WiiProtoState.FLAG_LED_3:
			ledval |= 0x40
		if self.state.flags & WiiProtoState.FLAG_LED_4:
			ledval |= 0x80
		ledval = self.wiiproto_cmd_keep_rumble(ledval)
		cmd_queue.send(self, (WiiProtoReqs.WIIPROTO_REQ_LED, ledval))
	
	def handler_status(self, status):
		if status[2] & 0x02:
			if not self.state.flags & WiiProtoState.FLAG_EXT_PLUGGED:
				self.state.flags |= WiiProtoState.FLAG_EXT_PLUGGED
				# Call detect extension
				logging.debug("New extension detected")
				t1 = threading.Thread(target=self.init_extension, kwargs={"notify":True})
				t1.start()
		else:
			if self.state.flags & WiiProtoState.FLAG_EXT_PLUGGED:
				self.state.flags &= ~WiiProtoState.FLAG_EXT_PLUGGED
				self.state.flags &= ~WiiProtoState.FLAG_EXT_ACTIVE
				self.state.flags &= ~WiiProtoState.FLAG_MP_PLUGGED
				self.state.flags &= ~WiiProtoState.FLAG_MP_ACTIVE
				# Call detect extension (to disable extension)
				logging.debug("Extension unplugged")
				t1 = threading.Thread(target=self.init_extension, kwargs={"notify":True})
				t1.start()
				
		# Update battery
		if "RVL-CNT-01-UC" in self.name:
			self.state.cmd_battery = status[5] / 255.0 * 100.0
		else:
			self.state.cmd_battery = status[5] / 208.0 * 100.0
		
			
	def wiiproto_cmd_detect_ext(self):
		if self.state.flags & WiiProtoState.FLAG_EXT_PLUGGED:
			# init extension
			self.wiiproto_cmd_wmem(0xa400f0, 0x55)
			self.wiiproto_cmd_wmem(0xa400fb, 0x00)
			# read extensions
			rmem = self.wiiproto_cmd_rmem(0xa400fa, 6)
			logging.debug("RMEM ext: "+repr(list(map(hex, rmem))))
			if rmem[0] == 0xff and rmem[1] == 0xff and rmem[2] == 0xff and rmem[3] == 0xff and rmem[4] == 0xff and rmem[5] == 0xff:
				return WiiDevExtension.WIIMOTE_EXT_NONE
			if rmem[4] == 0x00 and rmem[5] == 0x00:
				return WiiDevExtension.WIIMOTE_EXT_NUNCHUK
			if rmem[0] == 0x00 and rmem[4] == 0x01 and rmem[5] == 0x01:
				return WiiDevExtension.WIIMOTE_EXT_CLASSIC_CONTROLLER
			if rmem[0] == 0x01 and rmem[4] == 0x01 and rmem[5] == 0x01:
				return WiiDevExtension.WIIMOTE_EXT_CLASSIC_CONTROLLER_PRO
			if rmem[4] == 0x04 and rmem[5] == 0x02:
				return WiiDevExtension.WIIMOTE_EXT_BALANCE_BOARD
			if rmem[4] == 0x01 and rmem[5] == 0x20:
				return WiiDevExtension.WIIMOTE_EXT_PRO_CONTROLLER
		return WiiDevExtension.WIIMOTE_EXT_NONE
		
	def wiiproto_cmd_set_device(self, ext):
		if ext == WiiDevExtension.WIIMOTE_EXT_PRO_CONTROLLER:
			self.state.device = WiiDevType.WIIMOTE_DEV_PRO_CONTROLLER
		elif ext == WiiDevExtension.WIIMOTE_EXT_BALANCE_BOARD:
			self.state.device = WiiDevType.WIIMOTE_DEV_BALANCE_BOARD
		else:
			if self.name == "Nintendo RVL-CNT-01":
				self.state.device = WiiDevType.WIIMOTE_DEV_GEN10
			elif self.name == "Nintendo RVL-CNT-01-TR":
				self.state.device = WiiDevType.WIIMOTE_DEV_GEN20
			elif self.name == "Nintendo RVL-WBC-01":
				self.state.device = WiiDevType.WIIMOTE_DEV_BALANCE_BOARD
			elif self.name == "Nintendo RVL-CNT-01-UC":
				self.state.device = WiiDevType.WIIMOTE_DEV_PRO_CONTROLLER
			else:
				self.state.device = WiiDevType.WIIMOTE_DEV_UNKNOWN
	
	def init_extension(self, notify=False):
		ext = self.wiiproto_cmd_detect_ext()
		self.state.extension = ext
		logging.debug("Extension detected: "+repr(ext))
		if notify and self.extension_change_callback != None:
			self.extension_change_callback()
	
	def init_detect(self):
		self.wiiproto_req_status()
		self.init_extension()
		self.wiiproto_cmd_set_device(self.state.extension)
		# TODO: call probe
		
	def setLedByIndex(self, index):
		self.state.flags &= ~WiiProtoState.FLAG_LED_1
		self.state.flags &= ~WiiProtoState.FLAG_LED_2
		self.state.flags &= ~WiiProtoState.FLAG_LED_3
		self.state.flags &= ~WiiProtoState.FLAG_LED_4
		if index == 1:
			self.state.flags |= WiiProtoState.FLAG_LED_1
		elif index == 2:
			self.state.flags |= WiiProtoState.FLAG_LED_2
		elif index == 3:
			self.state.flags |= WiiProtoState.FLAG_LED_3
		elif index == 4:
			self.state.flags |= WiiProtoState.FLAG_LED_4
		self.wiiproto_req_led()
		
	def isWiimote(self):
		return self.state.device == WiiDevType.WIIMOTE_DEV_GEN10 or self.state.device == WiiDevType.WIIMOTE_DEV_GEN20
		
	def isWiimotePlus(self):
		return self.state.device == WiiDevType.WIIMOTE_DEV_GEN20
		
	def isProController(self):
		return self.state.device == WiiDevType.WIIMOTE_DEV_PRO_CONTROLLER
		
	def isBalanceBoard(self):
		return self.state.device == WiiDevType.WIIMOTE_DEV_BALANCE_BOARD
		
	def hasExtensionPlugged(self):
		return self.state.extension != WiiDevExtension.WIIMOTE_EXT_NONE
		
	def hasNunchuk(self):
		return self.state.extension == WiiDevExtension.WIIMOTE_EXT_NUNCHUK
		
	def hasClassicController(self):
		return self.state.extension == WiiDevExtension.WIIMOTE_EXT_CLASSIC_CONTROLLER
		
	def hasClassicControllerPro(self):
		return self.state.extension == WiiDevExtension.WIIMOTE_EXT_CLASSIC_CONTROLLER_PRO	
	
	def readFromDataSocket(self):
		inputready,outputready,exceptready = select.select([self.datasocket], [], [], 0.3)
		if len(inputready) <= 0:
			return []
		ev = inputready[0].recv(32)
		x = socket_to_bytearray(ev)
		return x
	
	def processInputData(self, x):
		if len(x)>0:
			code = x[1]
			if code == WiiProtoReqs.WIIPROTO_REQ_STATUS:
				self.state.lastpoll = time.time()
				handled = False
				with self.state.command_ready:
					if self.state.cmd_type == WiiProtoReqs.WIIPROTO_REQ_STATUS:
						self.state.cmd_buffer = x[2:]
						self.state.cmd_error = 0x00
						self.handler_status(x[2:])
						handled = True
						self.state.command_ready.notify()
				if not handled:
					self.handler_status(x[2:])
						
			elif code == WiiProtoReqs.WIIPROTO_REQ_DATA:
				with self.state.command_ready:
					if self.state.cmd_type == WiiProtoReqs.WIIPROTO_REQ_RMEM:
						self.state.cmd_buffer = x[7:]
						self.state.cmd_error = 0x00
						self.state.command_ready.notify()
						
			elif code == WiiProtoReqs.WIIPROTO_REQ_RETURN:
				with self.state.command_ready:
					if self.state.cmd_type == WiiProtoReqs.WIIPROTO_REQ_WMEM:
						self.state.cmd_error = x[5]
						self.state.command_ready.notify()
			else:
				# Invoke handler. Only the first matching handler is invoked
				data = x[2:]
				size = len(x)-1
				for h in self.handlers[:]:
					if h.isValid(code, size):
						h.invoke(data)
						break
						
		if self.state.lastpoll > 0 and self.state.lastpoll + 14 < time.time():
			self.disconnect()
	
	def _do_disconnect(self):
		cmd_queue.delDevice(self)
		receiver.delDevice(self)
		self.datasocket.close()
		self.sendsocket.close()
		
		logging.debug("Device "+self.address+" disconnected.")
		if self.disconnect_callback != None:
			self.disconnect_callback()
	
	def disconnect(self, block=False):
		with self.disconnectLock:
			if not self.isDisconnected:
				self.isDisconnected = True
				if block:
					self._do_disconnect()
				else:
					t1 = threading.Thread(target=self._do_disconnect)
					t1.start()
		
				
	def connect(self):
		logging.debug("Trying to connect to %s" % self.address)
		self.CMD_SET_REPORT = 0x52
		if "RVL-CNT-01-TR" in self.name or "RVL-CNT-01-UC" in self.name:
			# Protocol version 2
			self.CMD_SET_REPORT = 0xa2
			self.controlsocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
			self.controlsocket.connect((self.address,17))
			self.datasocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
			self.datasocket.connect((self.address,19))
			self.sendsocket = self.datasocket
			logging.debug("Controller protocol v2")
		else:
			# Protocol version 1
			self.sendsocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
			self.sendsocket.connect((self.address,17))
			self.datasocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
			self.datasocket.connect((self.address,19))
			logging.debug("Controller protocol v1")

		receiver.addDevice(self)
		status = self.wiiproto_req_status()
		logging.debug("Status: "+repr(list(map(hex, status))))
		
		self.init_detect()
		self.wiiproto_req_drm()
																
		logging.debug("Connected to %s" % self.address)
		self.isConnected = True
		return 1
		
	# DRM methods
	def wiiproto_select_drm(self):	
		drm = WiiProtoReqs.WIIPROTO_REQ_DRM_K
		ir = self.state.flags & (WiiProtoState.FLAG_IR_BASIC | WiiProtoState.FLAG_IR_EXT | WiiProtoState.FLAG_IR_FULL)
		ext = (self.state.flags & WiiProtoState.FLAG_EXT_USED) or (self.state.flags & WiiProtoState.FLAG_MP_USED)
		
		if self.state.device == WiiDevType.WIIMOTE_DEV_BALANCE_BOARD:
			if ext:
				return WiiProtoReqs.WIIPROTO_REQ_DRM_KEE
			else:
				return WiiProtoReqs.WIIPROTO_REQ_DRM_K
		if ir == WiiProtoState.FLAG_IR_BASIC:
			if self.state.flags & WiiProtoState.FLAG_ACCEL:
				return WiiProtoReqs.WIIPROTO_REQ_DRM_KAIE
			else:
				return WiiProtoReqs.WIIPROTO_REQ_DRM_KIE
		elif ir == WiiProtoState.FLAG_IR_EXT:
			return WiiProtoReqs.WIIPROTO_REQ_DRM_KAI
		elif ir == WiiProtoState.FLAG_IR_FULL:
			return WiiProtoReqs.WIIPROTO_REQ_DRM_SKAI1
		else:
			if self.state.flags & WiiProtoState.FLAG_ACCEL:
				if ext:
					return WiiProtoReqs.WIIPROTO_REQ_DRM_KAE
				else:
					return WiiProtoReqs.WIIPROTO_REQ_DRM_KA
			else:
				if ext:
					return WiiProtoReqs.WIIPROTO_REQ_DRM_KEE
				else:
					return WiiProtoReqs.WIIPROTO_REQ_DRM_K
		return drm
	def wiiproto_req_drm(self, _drm=None):
		drm = _drm
		if drm == None:
			drm = self.wiiproto_select_drm()
		logging.debug("DRM request: %x"%drm)
		cmd_queue.send(self, (WiiProtoReqs.WIIPROTO_REQ_DRM, self.wiiproto_cmd_keep_rumble(0x04), drm))
		
	def enableAccel(self):
		self.state.flags |= WiiProtoState.FLAG_ACCEL
		self.wiiproto_req_drm()
		
	def disableAccel(self):
		self.state.flags &= ~WiiProtoState.FLAG_ACCEL
		self.wiiproto_req_drm()
		
	def enableExtension(self):
		if self.state.flags & WiiProtoState.FLAG_EXT_PLUGGED:
			self.state.flags |= WiiProtoState.FLAG_EXT_USED
			self.wiiproto_req_drm()
		
	def disableExtension(self):
		self.state.flags &= WiiProtoState.FLAG_EXT_USED
		self.wiiproto_req_drm()
	