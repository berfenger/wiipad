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
import getopt
import sys
import threading
import logging
import time
import os

import gettext
_ = gettext.gettext

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import AppIndicator3 as AppIndicator

import ctrlmanager
import fileutils

def print_license():
	print("Wiipad version 1.0, Copyright (C) 2014  Arturo Casal")
	print("Wiipad comes with ABSOLUTELY NO WARRANTY;")
	print("This is free software, and you are welcome")
	print("to redistribute it under certain conditions.\n")
	
def print_help():
	print("wiipad_gui.py [options]")
	print("-m <mapping file> (define mapping file to use)")
	print("-s (enable continuous device scanning)")
	print("-h (print this help message)")

profile = None

# TODO: Crear una clase thread que se encargue de hacer las busquedas de dispositivos en segundo plano (tanto escaneo continuo como puntual)
class BackgroundDeviceScanner(threading.Thread):
	
	def __init__(self, finishCallback=None, continuous=False):
		threading.Thread.__init__(self)
		self.running = True
		self.continuous = continuous
		self.finishCallback = finishCallback
		
	def run(self):
		logging.debug("BackgroundDeviceScanner::started")
		try:
			if not self.continuous:
				# Single device scan
				for x in range(0, 4):
					devices = ctrlmanager.scan_wiimotes(duration=2)
					for d in devices[:]:
						ctrlmanager.connectDevice(d, profile)
					if len(devices) > 0:
						break
					time.sleep(1)
			else:
				# Continuous device scan mode
				while self.running:
					devices = ctrlmanager.scan_wiimotes(duration=2)
					if not self.running:
						return
					for d in devices[:]:
						ctrlmanager.connectDevice(d, profile)
					# Sleep for 3 seconds
					for x in range(0, 4):
						time.sleep(1)
						if not self.running:
							return
		finally:
			self.running = False
			logging.debug("BackgroundDeviceScanner::stopped")
			if self.finishCallback != None:
				self.finishCallback()
			
	def stop(self):
		self.running = False

class WiiControllersIndicator():
	loop = None
	scanner = None
	# Device scan menu item
	sfd = None
	# Enable continuous scan menu item
	ecs = None
	# Disable continuous scan menu item
	dcs = None
	
	def __init__(self, continuous=False):
		icons = Gtk.IconTheme.get_default()
		icons.append_search_path("./res/")
		self.ind = AppIndicator.Indicator.new (
                        "battery-100-charging",
                        "indicator-messages",
                        AppIndicator.IndicatorCategory.APPLICATION_STATUS)

		self.ind.set_status (AppIndicator.IndicatorStatus.ACTIVE)
		self.ind.set_attention_icon ("indicator-messages-new")
		self.ic_scan = os.path.realpath("./res/wiipad_scan.svg")
		self.ic_no_scan = os.path.realpath("./res/wiipad_no_scan.svg")
		self.ind.set_icon(self.ic_no_scan)
		self.ind.set_title("Wiipad"); 
		self.refreshDeviceList()
		ctrlmanager.registerForEvents(self)
		if continuous:
			self.enable_continuous_scanning(None)
		
	def onDeviceDisconnected(self, device):
		self.refreshDeviceList()
		pass
	
	def onDeviceConnected(self, device):
		self.refreshDeviceList()
		pass
		
	def refreshDeviceList(self):
		menu = Gtk.Menu()
		devices = ctrlmanager.getDeviceList()
		
		# Actions menu
		self.sfd = Gtk.MenuItem(_("Scan for device"))
		self.sfd.show()
		self.sfd.connect("activate", self.scan_for_device)
		menu.append(self.sfd)
		self.ecs = Gtk.MenuItem(_("Enable continuous scan"))
		self.ecs.show()
		self.ecs.connect("activate", self.enable_continuous_scanning)
		menu.append(self.ecs)
		self.dcs = Gtk.MenuItem(_("Disable continuous scan"))
		self.dcs.show()
		self.dcs.connect("activate", self.disable_continuous_scanning)
		menu.append(self.dcs)
		# Separator
		separator = Gtk.SeparatorMenuItem()
		separator.show()
		menu.append(separator)
		
		for dev in devices[:]:
			batt_pc = dev.wiimotedev.state.cmd_battery
			# Controller name
			menu_item = Gtk.MenuItem(_("%s (%d)"%(dev.prettyName, dev.led)))
			#menu_item = Gtk.ImageMenuItem("%s (%d)"%(dev.prettyName, dev.led))
			#img = Gtk.Image()
			#img.set_from_icon_name("distributor-logo", Gtk.IconSize.MENU)
			#menu_item.set_image(img)
			#menu_item.set_always_show_image(True)
			menu_item.show()
			menu_item.set_sensitive(False)
			menu.append(menu_item)
			# Battery status
			if batt_pc >= 0:
				menu_item = None
				menu_item = Gtk.MenuItem(_("Battery: %d %%") % batt_pc)
				menu_item.show()
				menu_item.set_sensitive(False)
				menu.append(menu_item)
			# Disconnect button
			menu_item = Gtk.MenuItem(_("Disconnect"))
			menu_item.show()
			menu_item.connect("activate", self.disconnect_device, dev)
			menu.append(menu_item)
			# Separator
			separator = Gtk.SeparatorMenuItem()
			separator.show()
			menu.append(separator)
			
		quititem = Gtk.MenuItem(_("Exit"))
		quititem.connect("activate", self.indicator_quit)
		quititem.show()
		menu.append(quititem)		
		menu.show()
		self.ind.set_menu(menu)
		self.refresh_buttons()
		
	def scan_for_device(self, item):
		if self.scanner == None or (self.scanner != None and not self.scanner.running):
			self.scanner = BackgroundDeviceScanner(continuous=False, finishCallback=self.scan_finish)
			self.scanner.start()
			self.refreshDeviceList()
			
	def enable_continuous_scanning(self, item):
		if self.scanner == None or (self.scanner != None and not self.scanner.running):
			self.scanner = BackgroundDeviceScanner(continuous=True, finishCallback=self.scan_finish)
			self.scanner.start()
			self.refreshDeviceList()
			
	def disable_continuous_scanning(self, item):
		if self.scanner != None and self.scanner.running:
			self.scanner.stop()
			self.refresh_buttons()
			
	def scan_finish(self):
		self.refreshDeviceList()
			
	def disconnect_device(self, item, device):
		device.disconnect()
		
	def run(self):
		self.loop = GObject.MainLoop()
		self.loop.run()
		
	def stop(self):
		ctrlmanager.unRegisterForEvents(self)
		self.disable_continuous_scanning(None)
		self.loop.quit()
		
	def refresh_buttons(self):
		if self.scanner != None and self.scanner.running and self.scanner.continuous:
			self.dcs.show()
			self.ecs.hide()
			self.sfd.hide()
			self.ind.set_icon(self.ic_scan)
		elif self.scanner != None and self.scanner.running and not self.scanner.continuous:
			self.dcs.hide()
			self.ecs.hide()
			self.sfd.hide()
			self.ind.set_icon(self.ic_scan)
		else:
			self.ecs.show()
			self.dcs.hide()
			self.sfd.show()
			self.ind.set_icon(self.ic_no_scan)
		
	def indicator_quit(self, a):
		self.stop()
		
if __name__ == "__main__":
	print_license()
	mapfile = None
	continuous = False
	try:
		opts, args = getopt.getopt(sys.argv[1:],"hsm:d",["mapfile="])
	except getopt.GetoptError:
		print_help()
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print_help()
			sys.exit()
		elif opt in ("-m", "--mapfile"):
			mapfile = arg
		elif opt in ("-s"):
				continuous = True
		elif opt in ("-d"):
			logging.basicConfig(level=logging.DEBUG)
			
	if mapfile == None:
		print("Map file needed.")
		print_help()
		sys.exit(1)
		
	try:
		profile = fileutils.readMappingFromFile(mapfile)
	except Exception as e:
		print(e)
		print("Error in mapping file: "+mapfile)
		sys.exit(1)
	try:
		indicator = WiiControllersIndicator(continuous=continuous)
		indicator.run()
	except KeyboardInterrupt:
		indicator.stop()
		
	ctrlmanager.disconnectDevices()