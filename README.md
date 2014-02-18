 
Wiipad
=======

Wiipad is a simple user-space driver written in python that allows you to use some Wii/WiiU peripherals as a gamepad or keyboard.
Current supported devices are Wii Remote (the original one), Wii Remote Plus (Motion Plus inside) and WiiU Pro Controller. The Nunchuk and Classic Controller extensions are supported as well.

Author: Arturo Casal

Requirements
------------------

python2.7
python-bluez/pybluez (Python wrappers around BlueZ stack)
pygi (Python GObject Instrospection needed by the gui version)

Usage
--------
There are two flavours of wiipad: a command-line interface (cli) and a slightly graphical interface based on an app-indicator (gui).

CLI version:
$ ./wiipad_cli.sh -m mapping.map  (mapping.map is a file containing the mapping applied at runtime)
The program will search for devices for 5 seconds at start time. Moreover, you can enable continuous scanning at start time by adding the option -s on the command line.

GUI version:
$ ./wiipad.sh -m mapping.map  (mapping.map is a file containing the mapping applied at runtime)
Now, you can trigger device scanning by clicking on the proper indicator item. Also, you can enable continuous scanning at start time by adding the option -s on the command line.

What's not supported
--------------------

* Rumble: currently there's no rumble support. It's supported on the libwiimote side, and partially supported on the uinput side. Also, this requires rumble effect simulation code that supports the effects defined by the structs ff_constant_effect and ff_rumble_effect. Other effects can be supported but the Wii/WiiU remotes only support two states (rumble on/rumble off).

* Wii Remote IR camera: this feature is not supported and there isn't plans for its support. This application is intended for gamepad/keyboard simulation, so it's not needed. But who knows, the door is open.

What's supported
----------------
* Analog Sticks, Triggers, buttons, and accelerometers.
* Dead zones for sticks/accelerometer axes.
* Scale axis ranges.
* Button simulation with an axis.
* Axis simulation with a button.
* Map Wiimote/Nunchuk shake to a button.
* Map 2 axes to 1 axis. (positive range to one axis, and the negative range to another axis) ie: tilt left = left trigger & tilt right = right trigger

Future Work
-----------
* Implement rumble support.
* GUI to visualize current mapping (controller image with mapping text overlayed)


How to copy
---------------
Wiipad is free (libre) software and licensed under the terms of
GNU Public License version 2 or later. In short, it means that you are
free to copy, redistribute and modify this software as long as you
place the derivative work under a compatible license.
See COPYING for details.