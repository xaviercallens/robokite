from math import atan2, sin, cos
import scipy as sp
import socket, traceback
import threading
import time
def decimalstr2float(decimalstrs):
    """ This function converts a string to float (probably exists elsewhere)"""
    decimal = []
    if type(decimalstrs) == str: 
        decimal = float(decimalstrs.replace(',', '.'))
    else : 
        for dec in decimalstrs:
            decimal.append(decimalstr2float(dec))
    return decimal 

class mobileState:
  """This class stores and process information about mobile phone"""
  def __init__(self):
    self.acceleration = [0, 0, 0]
    self.magnetic = [0, 0, 0]
    self.isToUpdate = False
    self.roll = 0
    self.pitch = 0
    self.yaw = 0
    self.filterTimeConstant = 0.3
    self.time_acceleration = 0
    self.time_magnetic = 0
    self.isTerminated = False

  def computeRPY(self):
    """Computes roll, pitch and yaw. See "Implementing a Tilt-Compensated
    eCompass using Accelerometer and
    Magnetometer Sensors" reference AN4248 from Freescale""" 

    Gpx = self.acceleration[0]
    Gpy = self.acceleration[1]
    Gpz = self.acceleration[2]
    Bpx = self.magnetic[0]
    Bpy = self.magnetic[1]
    Bpz = self.magnetic[2]
    # These parameters could be used to compensate for hard iron effect, if not already compensated
    Vx = 0
    Vy = 0
    Vz = 0
    phi = atan2(Gpy, Gpz) # According to Eqn 13
    theta = atan2(-Gpx, Gpy*sin(phi)+Gpz*cos(phi)) # According to Eqn 15
    psi = atan2((Bpz-Vz)*sin(phi)-(Bpy-Vy)*cos(phi), (Bpx-Vx)*cos(theta)+(Bpy-Vy)*sin(theta)*sin(phi)+(Bpz-Vz)*sin(theta)*cos(phi))   #According to Eqn 22
    self.roll = phi
    self.pitch = theta
    self.yaw = -psi # Sign changed to get correct output \todo find the first bug

  def decodeMessageSensorUDP(self, msg):
    """ This is used to decode message from sensorUDP application from the android market.
    The orientation field was first used, but its conventions were unclear.
    So now acceleration and magnetic vectors should be used"""
    data = msg.split(', ')
    if data[0]=='G':
        time = decimalstr2float(data[2])
        latitude_deg = decimalstr2float(data[3])
        longitude_deg = decimalstr2float(data[4])
        altitude = decimalstr2float(data[5])
        hdop = decimalstr2float(data[7])
        vdop = decimalstr2float(data[8])
        print time, latitude_deg, longitude_deg, altitude, hdop, vdop
    if data[0]=='O':
        #  'O, 146, 1366575961732, 230,1182404, -075,2031250, 001,7968750'
        [ u, u,    # data not used                                         \    
        heading_deg, # pointing direction of top of phone                    \ 
        roll_deg,    # around horizontal axis, positive clockwise [-180:180] \   
        pitch_deg] = decimalstr2float(data[1:])  # around vertical axis [_90:90]
        elevation_deg = -sp.rad2deg(sp.arctan2( 					\
			sp.cos(sp.deg2rad(pitch_deg))*sp.cos(sp.deg2rad(roll_deg)),     \
 			sp.sqrt(1+sp.cos(sp.deg2rad(roll_deg))**2*(sp.sin(sp.deg2rad(pitch_deg))**2-1)))) #positive up
        inclinaison_deg = pitch_deg #positive clockwise
        print heading_deg, roll_deg, pitch_deg, elevation_deg, inclinaison_deg
    if data[0] == 'A':
    # Index and sign are adjusted to obtain x through the screen, and z down
	deltaT = decimalstr2float(data[2])/1000 - self.time_acceleration
	alpha = 1-sp.exp(-deltaT/self.filterTimeConstant)
        self.time_acceleration = decimalstr2float(data[2])/1000
        self.acceleration[0] += alpha*(-decimalstr2float(data[5])-self.acceleration[0])
        self.acceleration[1] += alpha*(decimalstr2float(data[3])-self.acceleration[1])
        self.acceleration[2] += alpha*(-decimalstr2float(data[4])-self.acceleration[2])
    if data[0] == 'M':
    # Index and sign are adjusted to obtain x through the screen, and z down
	deltaT =  decimalstr2float(data[2])/1000-self.time_magnetic
	alpha = 1-sp.exp(-deltaT/self.filterTimeConstant)
        self.time_magnetic = decimalstr2float(data[2])/1000
        self.magnetic[0] += alpha*(-decimalstr2float(data[5])-self.magnetic[0])
        self.magnetic[1] += alpha*(decimalstr2float(data[3])-self.magnetic[1])
        self.magnetic[2] += alpha*(-decimalstr2float(data[4])-self.magnetic[2])

  def checkUpdate(self):
    host = ''
    port = 12345

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind((host, port))
    while not(self.isTerminated):
        try:
          message, address = s.recvfrom(9000)
          self.decodeMessageSensorUDP(message)
        except (KeyboardInterrupt, SystemExit):
          raise
        except:
	  traceback.print_exc()

if __name__ == '__main__':
  max_length = 0
  timeList = []
  rollList = []
  pitchList = []
  headingList = []
  filein = open('saveOrientation.txt', 'w')
  import matplotlib.pyplot as plt
  import numpy as np
  import time
  t0 = time.time()
  mobile = mobileState()
  a = threading.Thread(None, mobileState.checkUpdate, None, (mobile,))
  a.start()
  while time.time()-t0 < 20:
        mobile.computeRPY()
        print mobile.acceleration
	print mobile.roll
	timeList.append(time.time())
        headingList.append(mobile.yaw)
        rollList.append(mobile.roll)
        pitchList.append(mobile.pitch)
        time.sleep(0.1)

  plt.hold()
  plt.plot(np.array(timeList)-timeList[0], np.array(headingList))
  plt.plot(np.array(timeList)-timeList[0], np.array(rollList),'g')
  plt.plot(np.array(timeList)-timeList[0], np.array(pitchList), 'r')

  plt.show()

