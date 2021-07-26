import os 
import sys
import errno
import glob
from curses import *
fifolist = glob.glob("mon*")

FIFO=fifolist[0]
FIFO2 = fifolist[1]
#FIFO_Q="./commandfifo"
#
##screen1 = curses.initscr()
##curses.start_color()
##curses.init_pair(1,curses.COLOR_BLACK,curses.COLOR_WHITE)
#
try:
	os.mkfifo(FIFO)
	os.mkfifo(FIFO2)
except OSError as oe:
	if oe.errno != errno.EEXIST:
		raise
#try:
#    os.mkfifo(FIFO_Q)
#except OSError as oe:
#    if oe.errno != errno.EEXIST:
#        raise


def display(screen):
	
	screen.clear()
	screen.border()
	start_color()
	
	init_pair(1,COLOR_CYAN,COLOR_BLACK)
	init_pair(2,COLOR_BLACK,COLOR_CYAN)
	init_pair(3,COLOR_WHITE,COLOR_BLACK)
	init_pair(4,COLOR_BLACK,COLOR_GREEN)
	init_pair(5,COLOR_BLACK,COLOR_RED)


	motor_w = newwin(4,18,1,1)
	motor_w.attron(color_pair(1))
	motor_w.border()
	motor_w.attroff(color_pair(1))
	motor_w2 = newwin(4,18,1,22)
	motor_w2.attron(color_pair(1))
	motor_w2.border()
	motor_w2.attroff(color_pair(1))
	

	
	date_w = newwin(4,18,5,1)
	date_w.attron(color_pair(1))
	date_w.border()
	date_w.attroff(color_pair(1))
 	
	time_w = newwin(4,18,9,1)
	time_w.attron(color_pair(1))
	time_w.border()
	time_w.attroff(color_pair(1))
	
	telcoord_w = newwin(4,18,13,1)
	telcoord_w.attron(color_pair(1))
	telcoord_w.border()
	telcoord_w.attroff(color_pair(1))
	reacoord_w = newwin(6,18,17,1)
	reacoord_w.attron(color_pair(1))
	reacoord_w.border()
	reacoord_w.attroff(color_pair(1))
	status_w = newwin(4,18,23,1)
	status_w.attron(color_pair(1))
	status_w.border()	
	status_w.attroff(color_pair(1))
	
	telcoord_w2 = newwin(4,18,13,22)
	telcoord_w2.attron(color_pair(1))
	telcoord_w2.border()
	telcoord_w2.attroff(color_pair(1))
	reacoord_w2 = newwin(6,18,17,22)
	reacoord_w2.attron(color_pair(1))
	reacoord_w2.border()
	reacoord_w2.attroff(color_pair(1))
	status_w2 = newwin(4,18,23,22)
	status_w2.attron(color_pair(1))
	status_w2.border()	
	status_w2.attroff(color_pair(1))


	while True:
		try:
			with open(FIFO,'r') as fifo, open(FIFO2,'r') as fifo2 :
				while True:
					
					data_mon = fifo.read().split()
	#				print data_mon
					if len(data_mon) != 0:
						motor_w.addstr(0,1,"Motor pos",color_pair(2))
						motor_w.addstr(1,1,data_mon[0]+"  ")
						motor_w.addstr(2,1,data_mon[1]+"  ")
						motor_w.refresh()
						
						date_w.addstr(0,1,"Date",color_pair(2))
						date_w.addstr(1,1,data_mon[2])
						date_w.refresh()
						
						time_w.addstr(0,1,"Time/LTS",color_pair(2))
						time_w.addstr(1,1,data_mon[3]+"  ")
						time_w.addstr(2,1,(data_mon[4])[0:8]+"  ")
						time_w.refresh()
						
						telcoord_w.addstr(0,1,"Tel. coords",color_pair(2))
	
	
						telcoord_w.refresh()
						
						reacoord_w.addstr(0,1,"Real. Coords",color_pair(2))
						reacoord_w.addstr(1,1,"RA",color_pair(2))
						telcoord_w.addstr(1,1,data_mon[5])
						reacoord_w.addstr(3,1,"Dec",color_pair(2))
						telcoord_w.addstr(2,1,data_mon[6])
						reacoord_w.refresh()
						
						status_w.addstr(0,1,"Status",color_pair(2))
						if data_mon[7]=='1':status_w.addstr(1,1,"Moving ",color_pair(5))
						if data_mon[7]=='0':status_w.addstr(1,1,"Stopped",color_pair(4))
						status_w.addstr(2,1,data_mon[8]+"   ")
						status_w.refresh()

					if len(data_mon) == 0:
						break
					data_mon = fifo2.read().split()
	#				print data_mon
					if len(data_mon) != 0:
						motor_w2.addstr(0,1,"Motor pos",color_pair(2))
						motor_w2.addstr(1,1,data_mon[0]+"   ")
						motor_w2.addstr(2,1,data_mon[1]+"   ")
						motor_w2.refresh()
						
											
						telcoord_w2.addstr(0,1,"Tel. coords",color_pair(2))
	
	
						telcoord_w2.refresh()
						
						reacoord_w2.addstr(0,1,"Real. Coords",color_pair(2))
						reacoord_w2.addstr(1,1,"RA",color_pair(2))
						telcoord_w2.addstr(1,1,data_mon[5])
						reacoord_w2.addstr(3,1,"Dec",color_pair(2))
						telcoord_w2.addstr(2,1,data_mon[6])
						reacoord_w2.refresh()
						
						status_w2.addstr(0,1,"Status",color_pair(2))
						if data_mon[7]=='1':status_w2.addstr(1,1,"Moving ",color_pair(5))
						if data_mon[7]=='0':status_w2.addstr(1,1,"Stopped",color_pair(4))
						status_w2.addstr(2,1,data_mon[8]+"   ")
						status_w2.refresh()

					if len(data_mon) == 0:
						break

		except KeyboardInterrupt:
			break

wrapper(display)
#display()
