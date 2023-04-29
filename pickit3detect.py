#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only
#
# Much butchered version of lsusb-VERSION.py
# found at https://github.com/gregkh/usbutils/blob/master/lsusb.py.in
#Still a bit heavyweight, but OK for our purposes.
#
# Which normally displays your USB devices in reasonable form.
# Origial, with many thanks to:
# Copyright (c) 2009 Kurt Garloff <garloff@suse.de>
# Copyright (c) 2013,2018 Kurt Garloff <kurt@garloff.de>
#
# This version simply returns a list of usbdevs of Microchip pickits.
# The code contains no print() statements


import os
import re
#import sys


prefix = "/sys/bus/usb/devices/"

def get_list_pickit3(returnlist):
	"Read toplevel USB entries and search "
	root_hubs = []
	for dirent in os.listdir(prefix):
		if not dirent[0:3] == "usb":
			continue
		usbdev = UsbDevice(None, dirent, 0)
		root_hubs.append(usbdev)
	for usbdev in root_hubs:
		usbdev.get_childrens_pickits(returnlist)

class UsbObject:
	def read_attr(self, name):
		path = prefix + self.path + "/" + name
		return open(path).readline().strip()

	def read_link(self, name):
		path = prefix + self.path + "/" + name
		return os.path.basename(os.readlink(path))

class UsbEndpoint(UsbObject):
	"Container for USB endpoint info"
	def __init__(self, parent, fname, level):
		self.parent = parent
		self.level = level
		self.fname = fname
		self.path = ""
		self.epaddr = 0
		self.len = 0
		self.ival = ""
		self.type = ""
		self.attr = 0
		self.max = 0
		if self.fname:
			self.read(self.fname)

	def read(self, fname):
		self.fname = fname
		self.path = self.parent.path + "/" + fname
		self.epaddr = int(self.read_attr("bEndpointAddress"), 16)
		ival = int(self.read_attr("bInterval"), 16)
		if ival:
			self.ival = " (%s)" % self.read_attr("interval")
		self.len = int(self.read_attr("bLength"), 16)
		self.type = self.read_attr("type")
		self.attr = int(self.read_attr("bmAttributes"), 16)
		self.max = int(self.read_attr("wMaxPacketSize"), 16)

	def __repr__(self):
		return "<UsbEndpoint[%r]>" % self.fname


class UsbInterface(UsbObject):
	"Container for USB interface info"
	def __init__(self, parent, fname, level=1):
		self.parent = parent
		self.level = level
		self.fname = fname
		self.path = ""
		self.iclass = 0
		self.isclass = 0
		self.iproto = 0
		self.noep = 0
		self.driver = ""
		self.devname = ""
		self.protoname = ""
		self.eps = []
		if self.fname:
			self.read(self.fname)

	def read(self, fname):
		self.fname = fname
		self.path = self.parent.path + "/" + fname
		self.iclass = int(self.read_attr("bInterfaceClass"),16)
		self.isclass = int(self.read_attr("bInterfaceSubClass"),16)
		self.iproto = int(self.read_attr("bInterfaceProtocol"),16)
		self.noep = int(self.read_attr("bNumEndpoints"))

	def __repr__(self):
		return "<UsbInterface[%r]>" % self.fname

class UsbDevice(UsbObject):
	"Container for USB device info"
	def __init__(self, parent, fname, level=0):
		self.parent = parent
		self.level = level
		self.fname = fname
		self.path = ""
		self.iclass = 0
		self.isclass = 0
		self.iproto = 0
		self.vid = 0
		self.pid = 0
		self.name = ""
		self.serial = ""
		self.usbver = ""
		self.speed = ""
		self.maxpower = ""
		self.noports = 0
		self.devname = ""
		self.interfaces = []
		self.product = ""

		self.children = []
		if self.fname:
			self.read(self.fname)
			self.readchildren()

	def read(self, fname):
		self.fname = fname
		self.path = fname
		self.iclass = int(self.read_attr("bDeviceClass"), 16)
		self.isclass = int(self.read_attr("bDeviceSubClass"), 16)
		self.iproto = int(self.read_attr("bDeviceProtocol"), 16)
		self.vid = int(self.read_attr("idVendor"), 16)
		self.pid = int(self.read_attr("idProduct"), 16)
		try:
			self.name = self.read_attr("manufacturer")
		except:
			pass
		try:
			self.product = self.read_attr("product")
		except:
			pass
		if self.name:
			mch = re.match(r"Linux [^ ]* (.hci[_-]hcd) .HCI Host Controller", self.name)
			if mch:
				self.name = mch.group(1)
		try:
			ser = self.read_attr("serial")
			# Some USB devs report "serial" as serial no. suppress
			if (ser and ser != "serial"):
				self.serial = ser
		except:
			pass
		self.usbver = self.read_attr("version")
		self.speed = self.read_attr("speed")
		self.maxpower = self.read_attr("bMaxPower")
		self.noports = int(self.read_attr("maxchild"))

	def readchildren(self):
		if self.fname[0:3] == "usb":
			fname = self.fname[3:]
		else:
			fname = self.fname
		for dirent in os.listdir(prefix + self.fname):
			if not dirent[0:1].isdigit():
				continue
			if os.access(prefix + dirent + "/bInterfaceClass", os.R_OK):
				iface = UsbInterface(self, dirent, self.level+1)
				self.interfaces.append(iface)
			else:
				usbdev = UsbDevice(self, dirent, self.level+1)
				self.children.append(usbdev)
#		usbsortkey = lambda obj: [int(x) for x in re.split(r"[-:.]", obj.fname)]
#		self.interfaces.sort(key=usbsortkey)
#		self.children.sort(key=usbsortkey)
# Check to see if the given object is a pickit and add to the list if it is.
# Then recursively call to add any from each child.
	def get_childrens_pickits(self,returnlist):
		if "microchip" in self.name.lower() and "pickit" in self.product.lower():
			returnlist.append(self)
		for child in self.children:	
			child.get_childrens_pickits(returnlist)
