'''
This is the class that controls the motor
'''
import serial
import threading
import time
import signal
import sys
import argparse

class Motor():
	
	def __init__(self, Port, baudrate=115200):
		
		##Serial port setup	
		self.ser = serial.Serial()
		self.ser.timeout = 1 #maximum blocking time for read is 1 second	
		self.ser.baudrate = baudrate
		if (type(Port) is int):
			self.ser.port = Port - 1 #windows numerical port
		elif(type(Port) is str):
			self.ser.port = Port #linux string port
		self.ser.open()
		
		#Threading setup	
		self.alive = 1 #tell the thread to stay alive
		self.motor_thread = threading.Thread(target=self.motor_variable_process)
		self.motor_thread.daemon = True #make daemon thread so it exits when program ends
		self.data_lock = threading.Lock() #mutex for variables
		self.ser_lock = threading.Lock() #mutex for serial port
		self.motor_thread.start()
		
		self.update_period = .5 #update rate for variables		

		#Motor Variables
		self.error_codes = 0
		self.supply_voltage = 0
		self.temperature = 0	
	def __del__(self):
		self.Stop()
		self.ser.close()
	def MoveRight(self, percent):
		self.Enable() #enable the motor
		speed = self.getValueFromPercent(percent)
		speed1 = chr(speed & 0x1F)
		speed2 = chr(speed >> 5)
		self.ser.write(chr(0x85) + speed1 + speed2)
	def MoveLeft(self, percent):
		self.Enable() #enable the motor
		speed = self.getValueFromPercent(percent)
		speed1 = chr(speed & 0x1F)
		speed2 = chr(speed >> 5)
		self.ser.write(chr(0x86) + speed1 + speed2)
	def Stop(self):
		self.ser.write(chr(0xE0))
	def getVariables(self):
		variables = []
		self.data_lock.acquire()
		try:
			#return a tuple containing all the values
			variables.append(self.error_codes)
			variables.append(self.supply_voltage)
			variables.append(self.temperature)
		finally:
			self.data_lock.release()
		return variables	
	def Reset(self):
		while(position != 0):
			MoveLeft(self, getValueFromPercent(10))

	def Enable(self):	
		self.ser.write(chr(0x83))
	@staticmethod
	def getValueFromPercent(percent):
		return 3200 * percent / 100

	def motor_variable_process(self):
		print "motor variable process started"
		while self.alive:
			#aquire mutex locks
			self.ser_lock.acquire()
			self.data_lock.acquire()
			try: #try to read the motor variables
				#get error codes
				self.error_codes = self.ReadVar(1)
				#get supply voltage
				tmp = self.ReadVar(23)
				self.supply_voltage = float(tmp)/1000
				#get motor temperature
				tmp = self.ReadVar(24)
				self.temperature = float(tmp)/10
			finally: #release the locks
				self.ser_lock.release()
				self.data_lock.release()
			time.sleep(self.update_period)
		print "motor variable process exiting"
	
	def ReadVar(self, addr):
		#read variable at motor address
		self.ser.flushInput()
		self.ser.write(chr(0xA1) + chr(addr))
		[lbyte, hbyte] = self.ser.read(2)
		result = (ord(hbyte) << 8) | ord(lbyte)
		return result

	