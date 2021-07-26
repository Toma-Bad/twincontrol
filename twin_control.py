#!/home/toma/anaconda2/bin/python
import serial
from sys import  stdin
import select
from astropy.coordinates import EarthLocation as EL

from astropy.time import Time as T
from astropy.table import Table
from astropy.io import ascii
from astropy import units as u
from astropy.coordinates import SkyCoord
from datetime import datetime
from astropy.coordinates import get_sun
from astropy.coordinates import solar_system_ephemeris
from astropy.coordinates import get_body_barycentric, get_body, get_moon
from time import sleep
import os
from astropy.coordinates import solar_system_ephemeris
from astropy.coordinates import get_body_barycentric, get_body, get_moon
import time
import curses
from Queue import Queue
from collections import deque
from multiprocessing import Process, Queue, Value, Array, Pipe
import glob
import numpy as np
from astropy.coordinates import Angle
from pylab import *
#from rtlsdr import RtlSdr
from astropy.io import ascii
import pickle
#ser = serial.Serial('/dev/ttyUSB0',115200,timeout = 1,parity  = serial.PARITY_NONE,rtscts=False)
#while True:
#	inp, outp, err = select.select([sys.stdin, ser], [], [], .2)
#	if sys.stdin in inp :
#		line = sys.stdin.readline()
#		if line == "exit\n": break
#	if ser in inp:
#		line = ser.readline()
step2asec = 1./5.12
asec2step = 5.12
tmp = 0
class Telescope:
	def __init__(self,name="0",ser=None,initposa=0,initposb=0,initpoint=None,curloc = EL.from_geodetic(-7.069468,50.729803)):
		"""Telescope Object Class. It initializes all the required variables and sets the location of the observatory.
		In all this code, pos/position named variables refer to the positions of the electric motors in the mounts, which
		need to move 5.12 steps per arcsec of telescope movement.
		Poi/pointing named variables or functions refer to pointings, which are either Ra Dec like coordinates or a
		SkyCoord object.
		"""
		self.name = name
		self.ser = ser
		self.init_pos = [initposa, initposb]
		self.init_point= initpoint
		self.tracking=False
		self.vra=50.
		self.vdec=50
		self.loc = curloc
		self.posa_c = Value('d',0.0)
		self.posb_c = Value('d',0.0)
		self.state_c = Value('d',0.0)
		self.time_c = Array('c',19)
		self.state_c = Value('i',0)
		self.iposa_c= Value('d',0.0)
		self.iposb_c= Value('d',0.0)
		self.ira_c= Value('d',0.0)
		self.idec_c= Value('d',0.0)
		self.ra_c= Value('d',0.0)
		self.pointing_string_c = Array('c',30)
		self.dec_c= Value('d',0.0)
		self.lst_c=Array('c',15)
		self.p = None
		self.pipe_con = None
		self.pipe_mon = None
		self.lenq_c = Value('i',0)
	def open_port(self,portname='/dev/ttyUSB0',baud=115200,timeout = 0.05,parity  = serial.PARITY_NONE,rtscts=False):
		"""Open a port to communicate via USB with the microcontroller running the telescope motors. If by chance
		/dev/ttyUSB0 is not the right port, the code looks for USB1,2... etc.
		"""
		portlist = glob.glob("/dev/ttyUSB*")
		self.portname = portname
		try:
			try:
				self.ser = serial.Serial(portname,baud,timeout = timeout,parity=parity,rtscts=rtscts)
				print( "port "+portname+" is open")
			except:
				print( "could not open original port, trying next")
				self.ser = serial.Serial(portlist[0],baud,timeout = timeout,parity=parity,rtscts=rtscts)
				print( "port "+portlist[0]+" is open")
		except Exception as e: 
			print( "Couldn't open port", e)
			quit()	
	def open_pipe(self):
		"""Open e pipe so that the main code, running in ipython for example, can send messages
		to the monitoring script. If pipe opens, the two ends of the pipe are self.pipe_con and
		self.pip_mon - the control and the monitor end of the pipe. Upon successful opening of the
		pipe the function returns true, otherwise false.
		"""
		try:
			self.pipe_con,self.pipe_mon = Pipe()
			print( "Communications pipe open",self.pipe_con,self.pipe_mon)
			return True
		except Exception as e:
			print( "Could not open pipe!", e)
			return False
	def close_pipe(self):
		"""Close the pipe opened by open_pipe function.
		"""
		try:	
			if self.pipe_con and self.pipe_mon:
				self.pipe_con.close()
				self.pipe_mon.close()
				print( "Pipes closed")
		except Exception as e:
			print( e)
			print( "cannot close pipes")
	def set_pos(self,posa,posb):
		"""Set the current POSition of the telescope motor counters to posa and posb. The telescope motors do not measure steps from a fixed position, so current position can be set to an arbitrary value. When measuring telescope movement in motor steps, they will be counted from this initial position. It wouldn't be necessary to use this function, since the initial positions can be defined in memory.
		"""
		try:
			self.ser.write(("ma="+str(int(posa))+"\r\n").encode())
			self.ser.write(("mb="+str(int(posb))+"\r\n").encode())
			print( "Setting motor positions to",posa,posb)
		except Exception as e:
			print( e)
	def set_ipos(self,initposa,initposb):
		"""Save initposa and initposb as the initial positions of the telescope motors. These values are then saved to the shared memory.
		"""
		self.iposa_c.value = initposa
		self.iposb_c.value = initposb

	def get_pos(self):
		"""Get the current position of the telescope motors in steps. It sends a command to the controller via the usb connection asking for the positions of the motors, then reads the reply.
		Function was made to usually filter out unwanted output for this command, such as text. 
		This position represents the offset between the current position of the motors and the motor position set by the set_pos function.
		Returns an array [posa,posb].
		"""
		self.ser.write("sp\r\n")
		readdata = self.ser.readlines()
		try:
			pos = [int(_) for _ in readdata[0].split()]
			print( "Current motor pos:", pos)
			return pos 
		except:
			mask = [any(char.isdigit() for char in string) for string in readdata]
			pos = [int(_) for _ in (mask*readdata).split()]
			print( "Current motor pos:", pos)
			return pos
	def get_tpos(self):
		"""Same as get_pos, but also appends the current time to the returned position. Returns [pos a,pos b,current time]
		"""
		self.ser.write("sp\r\n".encode())
		readdata = self.ser.readlines()
		#print(readdata)
		readtime = T.now()
		#print readdata
		try:
			pos = [int(i) for i in readdata[np.where([len(_.split()) == 2 for _ in readdata])[0][0]].split()]
			#print "Current motor pos:", pos
			return pos,time.strftime("%Y-%m-%d %H:%M:%S"),readtime

		except:	
		#	print "rec err"
		#	print readdata
			pos = [self.posa_c.value,self.posb_c.value]
			#mask = [any([char.isdigit() for char in string]) for string in readdata]
			#print readdata,mask
			#pos = [int(_) for _ in [readdata[i] for i, x in enumerate(mask) if x][0].split()]
			#print "Current motor pos:", pos
			return pos,time.strftime("%Y-%m-%d %H:%M:%S"),readtime
	
	def set_ipoi(self,coords):
		"""Assign a pointing (a SkyCoord object) to the current position of the telescope. All other measurements of the pointing will calculate an offset for this position. So it would
		be a good practice to use this function after you pointed the telescope (manually) to a known position.
		"""
		self.init_point=SkyCoord(coords,frame='icrs',unit=(u.hourangle,u.deg))
		self.ira_c.value = self.init_point.ra.value
		self.idec_c.value = self.init_point.dec.value
		print( "Initial telescope pointing set to:",SkyCoord(coords,frame='icrs',unit=(u.hourangle,u.deg)))
	def set_poi_sun(self,t = T(time.strftime("%Y-%m-%d %H:%M:%S")),l = None):
		if not l: l = self.loc
		self.init_point = get_body('sun',t,l)
		self.ira_c.value = self.init_point.ra.value
		self.idec_c.value = self.init_point.dec.value
		self.ra_c.value = self.init_point.ra.value
		self.dec_c.value = self.init_point.dec.value

		print self.init_point.ra.value,self.init_point.dec.value
	def get_poi(self):
		"""Using the get_tpos function and converting its output from steps to arcsec, knowing the initial pointing set by set_ipoi, this function returns the current pointing of the telescope. The returned
		value is a SkyCoord object.
		"""
		d_RA = (self.iposa_c.value+self.posa_c.value)*step2asec*u.arcsec
		d_dec= (self.iposb_c.value-self.posb_c.value)*step2asec*u.arcsec
		i_RA = self.ira_c.value * u.deg
		i_dec= self.idec_c.value * u.deg
		if (d_RA+i_RA) < 0*u.deg:d_RA = 360*u.deg + d_RA
		if (d_RA+i_RA) > 360*u.deg:d_RA = -360*u.deg + d_RA
		ra_val = Angle(self.lst_c.value) + (d_RA+i_RA)
		current_poi = SkyCoord(ra_val,d_dec+i_dec,frame='icrs',unit=(u.deg,u.deg))
		self.ra_c.value = current_poi.ra.to(u.deg).value
		self.dec_c.value = current_poi.dec.to(u.deg).value
		
		return current_poi
	def start_tracking(self,duration):
		"""send a command via the pipe to start moving on the RA motor such that the telescope will track an object on the sky. It takes as an argument the number of seconds you want the tracking to last.
		"""
		dpa = -int((duration.to(u.s).value*15)*asec2step)
		self.pipe_con.send("mra "+str(dpa)+ "\r\n")
		print("mra "+str(dpa)+ "\r\n")
		print( "now tracking!")
	def stop_tracking(self):
		"""stop tracking. Not currently working or implemented.
		"""
		if self.state_c.value != 1:
			print( "Tracking should be already OFF")
		if self.state_c.value ==1:
			self.tracking=False
			print( "Tracking is now OFF")
	def move(self,dra,ddec):
		"""Send a command via the pipe to move the telescope on the RA and Dec axis relative (dra,ddec) in units of degrees.
		"""
		dpa=dra.to(u.arcsec).value*asec2step
		dpb=ddec.to(u.arcsec).value*asec2step
		print("Moving relative RA:",dra,"dec:",ddec )
		self.pipe_con.send("grp "+str(int(dpa))+" "+str(int(dpb))+"\r\n")
	def goto_poi(self,coords):
		"""Send a command viua the pipe to move the telescope to a given pointing. Argument is a SkyCoord object.
		"""
		coords_togo = SkyCoord(coords,frame='icrs')
		d_RA = (self.get_poi().ra-coords_togo.ra)/(1-1./50.)
		d_dec= self.get_poi().dec-coords_togo.dec
		self.move(d_RA,d_dec)
		#self.pipe_con.send("grp "+str(int(dpa))+" "+str(int(dpb))+"\r\n")
		#print "Moving from",self.get_poi(),"(current pointing) to ",coords_togo,"which at time",timenow,"corresponds to HA:",d_RA,"dec:",d_dec
	def goto0(self):
		"""Command via pipe for the telescope to go to a parking position. Not implemented!
		"""
		print( "Sent command to go to zero!")
		self.ser.write("ma "+str(int(5000))+" "+str(int(0))+" 0\n")
		self.ser.write("ma "+str(int(5000))+" "+str(int(0))+" 1\n")
	def stop(self):
		"""Send a stop command via pipe
		"""
		print( "Sent command to stop!")
		self.pipe_con.send("mq \n")
	def monitor(self,conn):
		"""Monitoring:% script, the "heart" of the telescope:
		
		This method is meant to be run as a subprocess of the main object. Its function is to continuously poll the motors' microcontroller for their current positions, update
		the shared memory variables, such as position and time, and send some values of variables to a display code via a named pipe. It can also queue any commands
		sent to it from the telescope methods, and execute them one by one in sequence. It can also tell if the tlescope is moving or not. Soawn using the start_monitor method.
		"""

		FIFO = './monitorfifo'+self.portname.split("/")[-1]
		FIFO_Q = './commandfifo'+self.portname.split("/")[-1]
		command_q = deque(maxlen = 500)
		
		try:
			os.remove(FIFO)
			os.remove(FIFO_Q)
		except:
			pass
		os.mkfifo(FIFO_Q)
		os.mkfifo(FIFO)
		pos_mem_a = deque(maxlen = 2)
		pos_mem_b = deque(maxlen = 2)
		pos_mem_a.append(0)
		pos_mem_a.append(0)
		pos_mem_b.append(0)
		pos_mem_b.append(0)
	#	with open(FIFO_Q,'w') as fifo_q:
	#		fifo_q.write(" ")
	#		fifo_q.flush()
		while True:
			time.sleep(0.1)
			pos,timer,real_timer = self.get_tpos()
			self.posa_c.value = pos[0]
			self.posb_c.value = pos[1]
			self.time_c.value = timer
			self.lst_c.value = str((real_timer+1*u.hr).sidereal_time('apparent',longitude = self.loc.geodetic[0]))
			self.pointing_string_c.value = str(self.get_poi().to_string(sep=":",style="hmsdms"))
			pos_mem_a.append(pos[0])
			pos_mem_b.append(pos[1])
			if conn.poll():
				order = conn.recv()
				command_q.append(order)
				#print order
			self.lenq_c.value = len(command_q)
			if pos_mem_a[0] != pos_mem_a[1] or pos_mem_b[0] != pos_mem_b[1]:
				self.state_c.value = 1
				#print "b",pos_mem_a
			else:
				self.state_c.value = 0
				#print "c",pos_mem_a
			if self.state_c.value == 0 and len(command_q)>0: 
				self.ser.write(command_q.popleft())
				self.state_c.value = 1
				#print "a",len(command_q)
					#	with open(FIFO_Q,'w') as fifo_q: 
			#		fifo_q.write(str(command_q)+"\n")
			#		fifo_q.flush()
#			else:
#				with open(FIFO_Q,'w') as fifo_q:
#					fifo_q.write(" ")
#					fifo_q.flush()
			
			
			#print self.lenq_c.value,self.state_c.value
			with open(FIFO,'w') as fifo:
				fifo.write(str(pos[0])+" "+str(pos[1])+" "+timer+" "+str(self.lst_c.value)+" "+self.pointing_string_c.value+" "+str(self.state_c.value)+" "+str(len(command_q))+" "+''.join([c.replace(' ','_') for c in command_q])+"\n")
				fifo.flush()
	def start_monitor(self):
		"""A method to start the monitoring script. This method opens the communications pipe, spawns the monitoring subprocess and connects the pipe to it. Now we can send and receive
		messages from the monitoring script.
		"""
		try:
			self.open_pipe()
			self.p = Process(target = self.monitor,args=(self.pipe_mon,))
			self.p.start()
			print( "monitoring started")
		except Exception as e:
			print( "unable to start monitoring", e)
	def stop_monitor(self):
		"""Method to close the pipes and terminate monitoring processes.
		"""
		try:
			self.p.terminate()
			self.close_pipe()
			print( "monitoring terminated")
		except:
			print( "unable to terminate monitoring")




class Receiver:
	def __init__(self,device='/dev/ttyACM0',timeout=0.5,telescope_objects = None,output_filename = "data_out.txt"):
		self.ser = serial.Serial(device,timeout = timeout,parity = serial.PARITY_NONE,rtscts = False)
		self.telescope_objects = telescope_objects
		self.output_filename = output_filename
		self.output_file = None
		if not telescope_objects: 
			print "Error, no tel object given!"
			quit()
		
	def read_mem(self):
		self.ser.write("m\r\n".encode())
		tmp_stream = self.ser.readlines()
		proc_stream = [[int(s) for s in st.split()] for st in tmp_stream if len(st.split())  == 5]
		antA,Q,I,antB,cnt = np.array(proc_stream).T
		return antA,Q,I,antB,cnt
	def save_mem(self,outfile = "memimage.txt"):
		antA,Q,I,antB,cnt = self.read_mem()
		datatab = Table([antA,Q,I,antB,cnt],names = ['antA','Q','I','antB','cnt'])
		ascii.write(datatab,output = outfile,format = "fixed_width",delimiter=',')
	
	
	
	def do_scan(self,tc = 30,tr = 50,nscans = 100,start_time = None):
		self.ser.write(("tc "+str(tc)+"\r\n").encode())
		self.ser.write(("tr "+str(tr)+"\r\n").encode())
		self.ser.write("r\r\n".encode())
		if not start_time: start_time = self.telescope_objects[0].time_c.value
		print(str(start_time)+": Scan started, would take approx. "+str(tr*nscans*1./1000)+" seconds.")
		time.sleep(tr * nscans*1./1000)
		self.ser.write("q\r\n".encode())
		print("Scan over.")
		return start_time
	
        def scan_move(self,tc=80,tr=20,start_time = None):
		self.ser.write(("tc "+str(tc)+"\r\n").encode())
		self.ser.write(("tr "+str(tr)+"\r\n").encode())
		self.ser.write("c\r\n".encode())
		if not start_time: start_time = self.telescope_objects[0].time_c.value
		print(str(start_time)+": Scan started")
		self.output_file = open('move'+self.output_filename,'a')
		#print self.telescope_objects[0].lenq_c.value
		while self.telescope_objects[0].state_c.value==1 or self.telescope_objects[0].lenq_c.value:
		#	print self.telescope_objects[0].lenq_c.value
			try:
				self.ser.write("p\r\n".encode())
				a = self.ser.readline()
				if len(a.split())>4:
		#			print a
					self.output_file.writelines([self.telescope_objects[0].time_c.value," ",self.telescope_objects[0].pointing_string_c.value," ",a])
			except Exception,e:
				print e
			except KeyboardInterrupt:
				break
		
		self.ser.write("q\r\n".encode())
		self.output_file.close()
		print("Scan over.")
		return start_time

	def scan_still(self,tc=80,tr=20,scan_time=10*u.s):
		self.ser.write(("tc "+str(tc)+"\r\n").encode())
		self.ser.write(("tr "+str(tr)+"\r\n").encode())
		self.ser.write("c\r\n".encode())
		self.output_file = open('still'+self.output_filename,'a')
		start_time = time.time()*u.s
		stop_time = start_time + scan_time
		while time.time() < stop_time.value:
			try:
				self.ser.write("p\r\n".encode())
				a = self.ser.readline()
				if len(a.split())>4:
		#			print a
					self.output_file.writelines([self.telescope_objects[0].time_c.value," ",self.telescope_objects[0].pointing_string_c.value," ",a])

				#self.output_file.writelines([self.telescope_objects[0].time_c.value," ",self.telescope_objects[0].pointing_string_c.value," ",self.ser.readline(),'\r\n'])
			except Exception,e:
				print e
			except KeyboardInterrupt:
				break
		

		self.ser.write("q\r\n".encode())
		self.output_file.close()
		print("Scan over.")
		return start_time
		

 	def stop_scan(self):
		self.ser.write("q\r\n".encode())
		self.output_file.close()
		print("Scan over.")



	def do_obs(self,outfile = None,start_pos = None,**kwargs):
		self.ser.write("c\r\n".encode())
		if not start_pos: start_pos = self.telescope_objects[0].get_poi().to_string(style="hmsdms")
		start_time = self.do_scan(kwargs) 
		obsdata = self.read_mem()
		if outfile:
			ascii.write(obsdata,output = (outfile+str(start_time)+"_"+str(start_pos).strip()+".txt").replace(" ","_").replace(":","-"),names = ['antA','Q','I','antB','cnt'],format = "fixed_width")
		return start_time,start_pos,obsdata


def serial_ports():																			   
	""" Lists serial port names
	:raises EnvironmentError:
	On unsupported or unknown platforms
	:returns:
	A list of the serial ports available on the system
	"""
	if sys.platform.startswith('win'):
		ports == ['COM%s' % (i + 1) for i in range(256)]
	elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
		# this excludes your current terminal "/dev/tty"
		ports = glob.glob('/dev/tty[A-Za-z0-9]*')
	elif sys.platform.startswith('darwin'):
		ports = glob.glob('/dev/tty.*')
	else:
		raise EnvironmentError('Unsupported platform')
	
	result = []
	for port in ports:
		print(port)
		try:
			s = serial.Serial(port)
			s.close()
			result.append(port)
		except Exception as e:
			print(e)
			pass
	return result

def raster_scan(telescope_objects = None,receiver_object=None,sideofsquare = 5*u.deg,density=10,**kwargs):
	telescope_objects[0].move(sideofsquare/2,sideofsquare/2)
	telescope_objects[0].move(-sideofsquare,0*u.deg)
	telescope_objects[1].move(sideofsquare/2,sideofsquare/2)
	telescope_objects[1].move(-sideofsquare,0*u.deg)
	time.sleep(0.1)
	for i in range(density):
		time.sleep(0.1)
		telescope_objects[0].move(sideofsquare,-sideofsquare/density)
		telescope_objects[1].move(sideofsquare,-sideofsquare/density)
		telescope_objects[0].move(-sideofsquare,0*u.deg)
		telescope_objects[1].move(-sideofsquare,0*u.deg)
	receiver_object.scan_move(kwargs)
def dec_scan(telescope_objects = None,receiver_object=None,sideofsquare = 5*u.deg,density=10,**kwargs):
	telescope_objects[0].move(0*u.deg,sideofsquare/2)
	telescope_objects[1].move(0*u.deg,sideofsquare/2)
	time.sleep(0.1)
	for i in range(density):
		time.sleep(0.1)
		telescope_objects[0].move(0*u.deg,-sideofsquare)
		telescope_objects[1].move(0*u.deg,-sideofsquare)
		telescope_objects[0].move(0*u.deg,+sideofsquare)
		telescope_objects[1].move(0*u.deg,+sideofsquare)

	receiver_object.scan_move(kwargs)

def sd_dec_scan(telescope_objects = None,receiver_object=None,sideofsquare = 5*u.deg,density=10,**kwargs):
	telescope_objects[0].move(0*u.deg,sideofsquare/2)
	time.sleep(0.1)
	for i in range(density):
		time.sleep(0.1)
		telescope_objects[0].move(0*u.deg,-sideofsquare)
		telescope_objects[0].move(0*u.deg,+sideofsquare)

	receiver_object.scan_move(kwargs)



def track_scan(telescope_objects = None,receiver_object=None,duration = 10*u.s,**kwargs):
	telescope_objects[0].start_tracking(duration)
	telescope_objects[1].start_tracking(duration)
	time.sleep(1)
	receiver_object.scan_move(kwargs)

def set_sun_and_scan(telescope_objects = None,receiver_object=None,duration = 10*u.s,**kwargs):
	telescope_objects[0].set_pos(0,0)
	telescope_objects[1].set_pos(0,0)
	telescope_objects[0].set_poi_sun()
	telescope_objects[1].set_poi_sun()
	telescope_objects[0].start_tracking(duration)	
	telescope_objects[1].start_tracking(duration)
	receiver_object.scan_still(scan_time = duration)

def stop_all(tel01,tel02):
	tel01.stop_monitor()
	tel02.stop_monitor()

	
	



tel1 = Telescope("aifa1")
tel1.open_port(portname='/dev/ttyUSB0')
tel1.start_monitor()
tel2 = Telescope("aifa2")
tel2.open_port(portname='/dev/ttyUSB1')
tel2.start_monitor()
rec1 = Receiver(telescope_objects = [tel2])
#rec1.tune()
