#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_temperature import Temperature

class EthTemperature:
	HOST = "192.168.3.150"
	PORT = 4223
	FILE = "_temperature.txt"
	PATH = "/home/gus484/public_html/temp/"

	def __init__(self):
		self.temp = None
		self.temp_val = 0
		self.ipcon = None
		self.ready = 0

		self.now = datetime.datetime.now()
		self.file = self.now.strftime('%Y-%m-%d')

		# create ip connection
		self.ipcon = IPConnection()

		# register ip connection callbacks
		self.ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE,
						self.cb_enumerate)

		self.ipcon.register_callback(IPConnection.CALLBACK_CONNECTED,
						self.cb_connected)

		self.ipcon.connect(EthTemperature.HOST, EthTemperature.PORT)

		self.ipcon.enumerate()

	def release(self):
		if self.ipcon != None:
			self.ipcon.disconnect()

	# callback updates temperature displayed on terminal
	#def cb_temperature(self, temperature):
	#	print temperature/100.0
	#	self.temp_val = temperature
	#	self.write_temperature()

	def write_temperature(self):
		if self.temp == None:
			return

		self.temp_val = self.temp.get_temperature()
		
		f = open(EthTemperature.PATH+self.file+EthTemperature.FILE,"a")
		f.write(self.now.strftime('%H:%M')+'|')
		f.write(str(self.temp_val)+"\n")
		f.close()

	# callback handles device connections and configures possibly lost 
	# configuration of lcd and temperature callbacks, backlight etc.
	def cb_enumerate(self, uid, connected_uid, position, hardware_version, 
				firmware_version, device_identifier, enumeration_type):
		if enumeration_type == IPConnection.ENUMERATION_TYPE_CONNECTED or enumeration_type == IPConnection.ENUMERATION_TYPE_AVAILABLE:
            
			# enumeration is for temperature bricklet
			if device_identifier == Temperature.DEVICE_IDENTIFIER:
				# create temperature device object
				self.temp = Temperature(uid, self.ipcon) 
				self.ready = 2
				#self.temp.register_callback(self.temp.CALLBACK_TEMPERATURE, 
				#	self.cb_temperature)

				#self.temp.set_temperature_callback_period(50)

	# callback handles reconnection of ip connection
	def cb_connected(self, connected_reason):
		# enumerate devices again. if we reconnected, the bricks/bricklets
		# may have been offline and the configuration may be lost.
		# in this case we don't care for the reason of the connection
		self.ipcon.enumerate()

if __name__ == "__main__":
	et = EthTemperature()
	while et.ready == 0:
		time.sleep(0.5)
	if et.ready == 2:
		et.write_temperature()
		et.release()

