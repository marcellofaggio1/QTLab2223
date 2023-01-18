# Contributo alla libreria che stiamo scrivendo per parlare con gli strumenti

import pyvisa
import numpy as np
import time
import smtplib, ssl
from matplotlib import pyplot as plt
import struct

port = 465                               # This port selects a high security protocol
password = '--------'                    # Obscure when uploading on GitHub
context = ssl.create_default_context()

#with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
#server.login("mail@gmail.com", password)

def measure(fridge, vna, temps, format_data):
    '''Outpus two matrices with dimensions num_points vs num_temperatures.
    The first contains the i values while the second contains the q values.'''
    I = np.zeros(len(temps))
    Q = np.zeros(len(temps))
    j = 0

    for t in temps:
        fridge.set_T(t)
        # we need to add a sleep maybe? And how much?
        fridge.check_T_stability(t/10, t)

        i, q = vna.get_data(format_data)
        I[j] = i
        Q[j] = q
        j += 1
        
    return I, Q

def amp_phase(I, Q):
    '''Outputs two matrices with dimensions num_points vs num_temperatures.
    The first contains the S_21 amplitude values while the second contains the S_21 phase values'''
    #a is the S_21 amplitude vector and p is the S_21 phases vector
    #A is the S_21 amplitude matrix and P is the S_21 phases matrix

    num_points = len(I[0]) # number of points i.e. usually 1601
    num_temps = len(I) # number of various temperatures

    A = np.zeros(num_temps)
    P = np.zeros(num_temps)
    a = np.zeros(num_points)
    p = np.zeros(num_points)

    for j in range(num_temps):
        for k in range(num_points):
            a[k] = np.sqrt(I[j,k]**2 + Q[j,k]**2)
            p[k] = np.arctan(Q[j,k]/I[j,k])
        A[j] = a
        P[j] = p

    return A, P


class FridgeHandler:
    def __init__(self):
        self.inst = pyvisa.ResourceManager().open_resource('ASRL1::INSTR')
  
    def execute(self, cmd):
        self.inst.write('$'+ str(cmd))

    def read(self, cmd):
        out = '?'
        while '?' in out or 'E' in out:
            out = self.inst.query_ascii_values(str(cmd), converter='s')
            print(out)
            out = str.rstrip(out[0])
            print(out)
        
        return out

    def get_sensor(self, cmd = 3):
        '''Measure temperature or pressure of a sensor of the system. Default: MC temperature.'''                           
        k = self.read('R' + str(cmd))
        k = k.replace("R+", "")
        print(k)
        #k = k.replace("?", "")
        return float(k)        

    def scan_T(self, cmd, interval, time):      # cmd -> command that specifies which temperature,
                                                # interval -> time step to perform control
                                                # time -> total time of the scansion
        '''Temperature scansion that prints the values every "interval" seconds for a "time" time'''
        N = int(time/interval)
        Temps = np.zeros(N)
        for i in range(N):
            out = self.inst.query_ascii_values(cmd, converter='s')
            out = str.rstrip(out[0])
            time.sleep(interval)
            out = (out.split('+'))[1]           # split the string where '+' is and gives back only the second part (1)
            Temps[i] = float(out)
            print('Temperature at step ' + i + ' is ' + out)
        return Temps

    def state(self):
        out = self.inst.query_ascii_values('X', converter='s')
        out = str.rstrip(out[0])
        print(out)
    
    def set_T(self, T):
        '''Set temperature to arbitrary value in 0.1 mK. 
        Be careful! The value of temp has to be specified with 5 figures!
        Range is the command name for the power range (E1, E2 ...)'''
        
        cmd = 'E'
        if T <= 35:
            cmd += '1'
        elif T <= 55:
            cmd += '2'
        elif T <= 140:
            cmd += '3'
        elif T <= 400:
            cmd += '4'
        else:
            cmd += '5'

        self.execute(cmd)
        self.execute('A2')
        self.execute('T' + str(10*T))

    def check_p(self):
        out = self.get_sensor(14) < 10000 and self.get_sensor(15) < 100000  #!!!!!!!!!!! check the pressure values
        if (not out):
            print("High pressure! O_O' ")
            # self.send_alert_mail()
        return out  

#Possiamo provare ad implementare un tempo dopo il quale, se la temperatura non è stabile, usciamo dal ciclo?    
    def check_T_stability(self, T, error, interval = 90, sleeptime = 5):    # T --> desired temperature
                                                                            # error --> uncertainty allowed on the temperature
                                                                            # interval --> minimum time of stability required
                                                                            # sleeptime --> time interval between each check
        #self.set_T(T)
        counter = 0
        countermax = int(interval/sleeptime)
        while counter < countermax:  
            if self.check_p() == False or (T-error < self.get_sensor(2) and self.get_sensor(2) < T+error): # check if values are ok
                # change get_sensor parameters !!!!!!!!
                counter = 0
                time.sleep(interval*4) #sleeps for 6 minutes if T not stable         
            else:
                counter += 1
                time.sleep(sleeptime) #5 sec of sleep between each T check
        if counter == countermax:
            print("Temperature is stable and fridgeboy is ready!")
            out = True
        return out

# Class for the communication with VNA

class VNAHandler:
    def __init__(self, num_points = 1601):
        self.inst = pyvisa.ResourceManager().open_resource('GPIB0::16::INSTR')
        self.inst.write('FORM2;')
        self.inst.write('CHAN1')
        self.inst.write('S21;')

        self.inst.write('POIN '+ str(num_points)+';')        #set number of points
        self.points = num_points

        self.inst.read_termination = '\n'
        self.inst.write_termination = '\n'
        print('VNA object created correctly\n')
        print(self.points)

    def set_range_freq(self, start_f, stop_f):
        ''''Set the range of frequencies for the next scan from start_f to stop_f'''
        self.inst.write('LINFREQ;')
        self.inst.write('STAR '+str(start_f)+' GHZ;')       #set start frequency
        self.inst.write('STOP '+str(stop_f)+' GHZ;')        #set stop frequency
        self.inst.write('CONT;')

    def beep(self):
            ''' Emit an interesting sound'''
            self.inst.write('EMIB')
            
    def set_format(self, format):
        ''' Set the format for the displayed data'''
        if format == 'polar':
            write_string = 'POLA;'
        elif format == 'log magnitude':
            write_string = 'LOGM;'
        elif format == 'phase':
            write_string = 'PHAS;'
        elif format == 'delay':
            write_string = 'DELA;'
        elif format == 'smith chart':
            write_string = 'SMIC;'
        elif format == 'linear magnitude':
            write_string = 'LINM;'
        elif format == 'standing wave ratio':
            write_string = 'SWR;'
        elif format == 'real':
            write_string = 'REAL;'
        elif format == 'imaginary':
            write_string = 'IMAG;'

        self.inst.write(write_string)

    def output_data_format(self, format):
        if format == 'raw data array 1':
            msg = 'OUTPRAW1;'
        elif format == 'raw data array 2':
            msg = 'OUTPRAW2;'
        elif format == 'raw data array 3':
            msg = 'OUTPRAW3;'
        elif format == 'raw data array 4':
            msg = 'OUTPRAW4;'
        elif format == 'error-corrected data':
            msg = 'OUTPDATA;'
        elif format == 'error-corrected trace memory':
            msg = 'OUTPMEMO;'
        elif format == 'formatted data':
            msg = 'DISPDATA;OUTPFORM'
        elif format == 'formatted memory':
            msg = 'DISPMEMO;OUTPFORM'
        elif format == 'formatted data/memory':
            msg = 'DISPDDM;OUTPFORM'
        elif format == 'formatted data-memory':
            msg = 'DISPDMM;OUTPFORM'
        
        self.inst.write(msg)  

    def get_data(self, format_data, format_out = 'formatted data'):
        '''Get data of a certain type'''

        self.set_format(format_data)
        self.output_data_format(format_out)
        
        num_bytes = 8*int(int(float(self.points)))+4
        #time.sleep(2)
        raw_bytes = self.inst.read_bytes(num_bytes)

        trimmed_bytes = raw_bytes[4:]
        tipo = '>' + str(2*int(float(self.points))) + 'f'
        x = struct.unpack(tipo, trimmed_bytes)

        amp_q = list(x)
        amp_i = amp_q.copy()

        del amp_i[1::2]
        del amp_q[0::2]

        plt.plot(amp_i, amp_q)

        return amp_i, amp_q