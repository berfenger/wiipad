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
import sys
import getopt
import time
import logging

import ctrlmanager
import fileutils

def print_license():
	print("Wiipad version 1.0, Copyright (C) 2014  Arturo Casal")
	print("Wiipad comes with ABSOLUTELY NO WARRANTY;")
	print("This is free software, and you are welcome")
	print("to redistribute it under certain conditions.\n")

def print_help():
	print("wiipad_cli.py [options]")
	print("-m <mapping file> (define mapping file to use)")
	print("-s (enable continuous device scanning)")
	print("-h (print this help message)")

if __name__ == "__main__":
	try:
		print_license()
		mapfile = None
		continuous = False
		try:
			opts, args = getopt.getopt(sys.argv[1:],"hsm:d",["mapfile="])
		except getopt.GetoptError:
			print_help()
			sys.exit(2)
		for opt, arg in opts:
			if opt == ('-h',):
				print_help()
				sys.exit()
			elif opt in ("-m", "--mapfile"):
				mapfile = arg
			elif opt in ("-s",):
				continuous = True
			elif opt in ("-d",):
				logging.basicConfig(level=logging.DEBUG)
				
		if mapfile == None:
			print("Map file needed.")
			print_help()
			sys.exit(1)
			
		try:
			profile = fileutils.readMappingFromFile(mapfile)
		except Exception as e:
			print(e)
			print("Error in mapping file")
			sys.exit(1)
		
		print("Scanning devices...")
		print("Please, press 1+2 on your Wiimote or Sync button on your Wiimote Plus, Pro Controller or Balance Board")
		if not continuous:
			# Single device scan
			found = False
			for x in range(0, 4):
				devices = ctrlmanager.scan_wiimotes(duration=2)
				for d in devices[:]:
					ctrlmanager.connectDevice(d, profile)
				if len(devices) > 0:
					found = True
					break
				time.sleep(1)
			if not found:
				print("No compatible devices found")
				sys.exit(0)
			print("\nPress Control+C to exit")
			while True:
				time.sleep(1)
		else:
			while continuous:
				devices = ctrlmanager.scan_wiimotes(duration=2)
				for d in devices[:]:
					ctrlmanager.connectDevice(d, profile)
				time.sleep(3)
					
	except KeyboardInterrupt:
		print("Shutting down...")
		ctrlmanager.disconnectDevices()
		print("Done")
	