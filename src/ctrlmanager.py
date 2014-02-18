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
import logging

import wiimote_uinput_glue
import libwiimote

deviceList = []
ledSlots = [False, False, False, False]
ledSlotLock = threading.RLock()
deviceListLock = threading.RLock()
eventListeners = []

def acquireLedSlot():
	with ledSlotLock:
		i = -1
		for s in ledSlots[:]:
			i+=1
			if not s:
				ledSlots[i] = True
				return (i+1)
		return 1
	
def releaseLedSlot(slot):
	with ledSlotLock:
		ledSlots[(slot-1)] = False

def onDeviceDisconnected(device):
	with deviceListLock:
		deviceList.remove(device)
	releaseLedSlot(device.led)
	for l in eventListeners:
		l.onDeviceDisconnected(device)

def filter_devices(devices):
	for d in devices[:]:
		if not ("Nintendo RVL-CNT-01" in d[1] or "Nintendo RVL-WBC-01" in d[1]):
			devices.remove(d)
	return devices

def scan_wiimotes(duration=5):
	devices = bluetooth.discover_devices(duration=duration, lookup_names = True)
	devices = filter_devices(devices)
	logging.debug("scan_wiimotes::Found %d compatible devices"%len(devices))
	return devices

def connectDevice(device, mapping):
	led = acquireLedSlot()
	w = wiimote_uinput_glue.UInputWiimote(device[0], device[1], mapping, led=led, disconnectCallback=onDeviceDisconnected)
	with deviceListLock:
		deviceList.append(w)
	for l in eventListeners:
		l.onDeviceConnected(w)
		
def disconnectDevices():
	with deviceListLock:
		for d in deviceList[:]:
			d.disconnect()
	libwiimote.disconnect()
	
def registerForEvents(listener):
	if not listener in eventListeners:
		eventListeners.append(listener)
		
def unRegisterForEvents(listener):
	if listener in eventListeners:
		eventListeners.remove(listener)
		
def getDeviceList():
	return deviceList
	