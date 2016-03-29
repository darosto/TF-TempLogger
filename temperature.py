#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mysql.connector
import ConfigParser
import datetime
import time
import os, sys
from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_temperature import Temperature
from tinkerforge.bricklet_dual_relay import DualRelay
from tinkerforge.bricklet_ptc import PTC

class EthTemperature:
	HOST = "192.168.3.150"
	PORT = 4223
	DB_NAME = "tl"
	DB_HOST = "127.0.0.1" 
	DB_USER = "DBUSER"
	DB_PASS = "DBPASS"
	TB_OFFSET = 0 * 100
	PTC_OFFSET = 2.7 * 100

	def __init__(self):
		self.temp 	= None
		self.ptc 	= None
		self.dr 	= None
		self.relay	= 2

		self.ipcon 	= None
		self.ready 	= 0
		self.config = {}

		self.cursor = None
		self.cnx 	= None

		self.now = datetime.datetime.now()
		self.file = self.now.strftime('%Y-%m-%d')

		self.connect_db()
		self.read_config()

		# create ip connection
		self.ipcon = IPConnection()

		# register ip connection callbacks
		self.ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE,
						self.cb_enumerate)

		self.ipcon.register_callback(IPConnection.CALLBACK_CONNECTED,
						self.cb_connected)

		self.ipcon.connect(EthTemperature.HOST, EthTemperature.PORT)

	def release(self):
		if self.ipcon != None:
			self.ipcon.disconnect()

		if self.cursor != None:
			self.cursor.close()

		if self.cnx != None:
			self.cnx.close()

	def connect_db(self):
		self.cnx = mysql.connector.connect(user=EthTemperature.DB_USER, password=EthTemperature.DB_PASS,
			host=EthTemperature.DB_HOST, database=EthTemperature.DB_NAME)

		self.cursor = self.cnx.cursor()

	def read_config(self):
		if self.cursor == None:
			return

		sql = ("SELECT cfg_key, cfg_value FROM tl_config")
		self.cursor.execute(sql)		

		for (cfg_key, cfg_value) in self.cursor:
			self.config[cfg_key] = cfg_value

	def get_temperature(self, sensor):
		if sensor == "PTC":
			if self.ptc == None:
				return 0
			else:
				return self.ptc.get_temperature() + EthTemperature.PTC_OFFSET
		elif sensor == "TB":
			if self.temp == None:
				return 0
			else:
				return self.temp.get_temperature() + EthTemperature.TB_OFFSET

	def write_temperature(self):

		if self.cursor == None:
			return

		temp_inside = self.get_temperature("TB")
		temp_outside = self.get_temperature("PTC")

		sql = ("INSERT INTO tl_measurements "
               "(measurement_date, temperature, temperature_ptc) "
               "VALUES (%(a)s, %(b)s, %(c)s)")

		args = { 'a' : self.now.strftime('%Y-%m-%d %H:%M:%S'), 'b' : temp_inside, 'c' : temp_outside}

		self.cursor.execute(sql,args)

		# insert new temperature

		mid = self.cursor.lastrowid

		self.cnx.commit()
	
	def set_relay(self,state):
		if self.dr == None or isinstance(state,bool) == False:
			return

		self.dr.set_selected_state(self.relay, state)

	def check_temperature(self):
		if self.ptc == None:
			return

		temp_inside = self.get_temperature("PTC")

		if temp_inside/100.0  < float(self.config["min_temp"]):
			self.set_relay(True)
		elif temp_inside/100.0  > float(self.config["max_temp"]):
			self.set_relay(False)

	# callback handles device connections and configures possibly lost 
	def cb_enumerate(self, uid, connected_uid, position, hardware_version, 
				firmware_version, device_identifier, enumeration_type):
		if enumeration_type == IPConnection.ENUMERATION_TYPE_CONNECTED or enumeration_type == IPConnection.ENUMERATION_TYPE_AVAILABLE:
			# enumeration is for temperature bricklet
			if device_identifier == Temperature.DEVICE_IDENTIFIER:
				# create temperature device object
				self.temp = Temperature(uid, self.ipcon) 
				self.ready = self.ready + 1

			if device_identifier == DualRelay.DEVICE_IDENTIFIER:
				# create dual relay device object
				self.dr = DualRelay(uid, self.ipcon)
				self.ready = self.ready + 1

			if device_identifier == PTC.DEVICE_IDENTIFIER:
				# create ptc device object
				self.ptc = PTC(uid, self.ipcon)

				self.ptc.set_wire_mode(PTC.WIRE_MODE_3)

				self.ready = self.ready + 1

	# check if all sensors for temperature control connected
	def is_ready(self, mode):
		if mode == 'temperature':
			if self.dr != None && self.ptc != None:
				return True
		return False

	# callback handles reconnection of ip connection
	def cb_connected(self, connected_reason):
		# enumerate devices again. if we reconnected, the bricks/bricklets
		# may have been offline and the configuration may be lost.
		# in this case we don't care for the reason of the connection
		self.ipcon.enumerate()

if __name__ == "__main__":
	et = EthTemperature()
	i = 0

	# check if sensors connected
	while et.is_ready('temperature') != True:
		time.sleep(0.5)
		if i == 6: # exit programm, if no sensor connection after 3 secs
			et.release()
			sys.exit(0)

	if et.is_ready('temperature'):
		if et.now.minute == 0: # log temp every hour
			et.write_temperature()
		et.check_temperature()
		et.release()

