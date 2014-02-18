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
# See linux/include/uapi/asm-generic/ioctl.h

import struct

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8

# According to linux these *may* be architecture specific
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRMASK = (1 << _IOC_NRBITS) - 1
_IOC_TYPEMASK = (1 << _IOC_TYPEBITS) - 1
_IOC_SIZEMASK = (1 << _IOC_SIZEBITS) - 1
_IOC_DIRMASK = (1 << _IOC_DIRBITS) - 1

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2


def IOC(_dir, _type, nr, size):
    if type(size) in (str, unicode):
        size = struct.calcsize(size)
    return _dir << _IOC_DIRSHIFT | _type << _IOC_TYPESHIFT | \
            nr << _IOC_NRSHIFT | size << _IOC_SIZESHIFT


IO = lambda _type, nr: IOC(_IOC_NONE, _type, nr, 0)
IOR = lambda _type, nr, size: IOC(_IOC_READ, _type, nr, size)
IOW = lambda _type, nr, size: IOC(_IOC_WRITE, _type, nr, size)
IORW = lambda _type, nr, size: IOC(_IOC_READ | _IOC_WRITE, _type, nr, size)
IOWR = IORW