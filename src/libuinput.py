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
import ctypes
import fcntl
import os
import threading
import select
import logging

import uinputdefs

def open_uinput():
	# Open uinput device
	try:
		f = os.open('/dev/uinput',  os.O_RDWR | os.O_NONBLOCK)
	except OSError:
		try:
			f = os.open('/dev/input/uinput', os.O_RDWR | os.O_NONBLOCK)
		except OSError:
			logging.warning('Could not open uinput. Do you have permissions?')
			return None
	return f

def write_uinput_device_info(uidev, f):

	# Write device info
	buf = buffer(uidev)[:]
	os.write(f, buf)
	fcntl.ioctl(f, uinputdefs.UI_DEV_CREATE)
	return f

def free_uinput_device(f):
	# Free resources and delete uinput device
	fcntl.ioctl(f, uinputdefs.UI_DEV_DESTROY)

STATE_UINPUT = 1
STATE_DEV_CREATED = 2
STATE_DEV_DESTROYED = 3

class UInputDevice(object):

	"""
	Class to create input devices using uinput API
	"""
	def __init__(self, name="uinput-device",
                 bustype=0x00, vendor=0x00, product=0x00, version=0x00, ff_callback=None):
		self._f = open_uinput()
		self.state = 0
		if not self._f:
			logging.warning('Failed to open uinput')
			raise OSError
		else:
			self.state = STATE_UINPUT
		self.uidev = uinputdefs.uinput_user_dev()
		self.uidev.name = name.encode()
		self.uidev._id.bustype = bustype
		self.uidev._id.vendor = vendor
		self.uidev._id.product = product
		self.uidev._id.version = version
		self.uidev.ff_effects_max = 0
		self.flock = threading.Lock()
		self.useff = False
		self.ff_effects = []
		self.ff_callback = ff_callback

	def setup(self):
		"""
		Create the uinput device. Cannot be modified from now on
		"""
		write_uinput_device_info(self.uidev, self._f)
		self.state = STATE_DEV_CREATED
		self.running = True
		if self.useff:
			t1 = threading.Thread(target=self.bak_read)
			t1.start()

	def enable_event_type(self, evt):
		"""
		Enables a specific event type
		"""
		if evt == uinputdefs.EV_FF:
			self.useff = True
			self.uidev.ff_effects_max = uinputdefs.FF_EFFECT_MAX
		fcntl.ioctl(self._f, uinputdefs.UI_SET_EVBIT, evt)

	def enable_event(self, evt, evc):
		"""
		Enables an event code. The event type should be enabled too
		"""
		evbit = uinputdefs.evbits[evt]
		fcntl.ioctl(self._f, evbit, evc)

	def set_absprops(self, _abs, _max=0, _min=0, _fuzz=0, _flat=0):
		"""
		Set absolute axis properties
		"""
		self.uidev.absmax[_abs] = _max
		self.uidev.absmin[_abs] = _min
		self.uidev.absfuzz[_abs] = _fuzz
		self.uidev.absflat[_abs] = _flat

	def bak_read(self):
		logging.debug("uinput::start::Listen for uinput events (FF).")
		while(self.running):
			with self.flock:
				if not self.running:
					break
				inputready,outputready,exceptready = select.select([self._f], [], [], 0.5)
				# If no data, listen again
				if len(inputready) <= 0:
					continue
				estr = os.read(self._f, ctypes.sizeof(uinputdefs.input_event))
				e = ctypes.cast(estr, ctypes.POINTER(uinputdefs.input_event))
				evv = e.contents
				ev = uinputdefs.input_event(evv.time, evv.type, evv.code, evv.value)
				#print("eventt type: "+repr(ev.type))
				#print("eventt code: "+repr(ev.code))
				if ev.type == uinputdefs.EV_FF:
					#print("EV_FF")
					#print("Rumble: "+repr(ev.code)+"/"+repr(ev.value))
					if self.ff_callback != None:
						self.ff_callback(ev.code, ev.value)
				elif ev.type == uinputdefs.EV_UINPUT:
					#print("EV_UINPUT")
					if ev.code == uinputdefs.UI_FF_UPLOAD:
						#print("es upload")
						upload = uinputdefs.uinput_ff_upload()
						upload.request_id = ev.value
						buf = buffer(upload)[:]
						fcntl.ioctl(self._f, uinputdefs.UI_BEGIN_FF_UPLOAD, buf);
						u = ctypes.cast(buf, ctypes.POINTER(uinputdefs.uinput_ff_upload))
						upp = u.contents
						upload = uinputdefs.uinput_ff_upload(upp.request_id, upp.retval, upp.effect, upp.old)
						# Add effect to list
						if len(self.ff_effects) > uinputdefs.FF_EFFECT_MAX:
							self.ff_effects.pop()
						self.ff_effects.append(upload.effect)
						fcntl.ioctl(self._f, uinputdefs.UI_END_FF_UPLOAD, buf);
					elif ev.code == uinputdefs.UI_FF_ERASE:
						#print("es erase")
						erase = uinputdefs.uinput_ff_erase()
						erase.request_id = ev.value
						buf = buffer(erase)[:]
						fcntl.ioctl(self._f, uinputdefs.UI_BEGIN_FF_ERASE, buf);
						# Delete given effect
						ee = ctypes.cast(buf, ctypes.POINTER(uinputdefs.uinput_ff_erase))
						eee = ee.contents
						self.del_ff_effect_by_id(eee.effect_id)
						fcntl.ioctl(self._f, uinputdefs.UI_END_FF_ERASE, buf);
				else:
					logging.debug("uinput::input::Invalid input code received")
			
		
		logging.debug("uinput::stop:Listen for uinput events (FF).")

	def send_event(self, ev):
		if self.state != STATE_DEV_CREATED:
			return
		os.write(self._f, buffer(ev)[:])
		
	def send_sync(self):
		if self.state != STATE_DEV_CREATED:
			return
		ev = uinputdefs.input_event()
		ev.time = uinputdefs.gettimeofday()
		ev.type = uinputdefs.EV_SYN
		ev.code = uinputdefs.SYN_REPORT
		ev.value = 0
		os.write(self._f, buffer(ev)[:])
		
	def get_ff_effect_by_id(self, _id):
		for eff in self.ff_effects[:]:
			if _id == eff.id:
				return eff
		return None
		
	def del_ff_effect_by_id(self, _id):
		for eff in self.ff_effects[:]:
			if _id == eff.id:
				self.ff_effects.remove(eff)
				return eff
		return None

	def __del__(self):
		laststate = self.state
		self.state = STATE_DEV_DESTROYED
		self.running = False
		with self.flock:
			if hasattr(self, '_f') and laststate == STATE_DEV_CREATED:
				logging.debug("UInput device deleted.")
				free_uinput_device(self._f)
			#elif laststate:
			#	os.close(self._f)
