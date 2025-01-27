# Contributo alla libreria che stiamo scrivendo per parlare con gli strumenti

import pyvisa
import numpy as np
import time

#classe per controllo Kelvinox

class FridgeHandler:
    def __init__(self):
        self.inst = pyvisa.ResourceManager().open_resource('ASRL1::INSTR')
  
    def execute(self, cmd):
        self.inst.write('$'+ str(cmd))

    def read(self, cmd):
        out = self.inst.query_ascii_values(str(cmd), converter='s')
        out = str.rstrip(out[0])
        print(out)

    def scan_t(self, cmd, interval, time):       # cmd -> command that specifies which temperature,
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

    def check_temp_stabilty(self, cmd, interval, time, CentralTemp, sigma ):     # same par.s as ScanT + 
                                                                        # CentralTemp -> Temperature
                                                                        # sigma -> half range of confidence
        ''''Check of Temperature stability making scansions until the Temperature is stable'''
        i = 0
        while i == 0:
            Temp = scan_t(self, cmd, interval, time)
            for k in range(len(Temp)):
                if Temp[k] < CentralTemp - sigma or Temp[k] > CentralTemp + sigma:
                    i = 0
                    break
                i = 1
            print('The temperature doesn t seem stable!')
        print('The temperature is stable!')

    #def SetT(self, cmd):      # cmd -> specifies the temperature and which 
    #    '''Set the temperature to one of the allowed values (does so supplying power to the Mixing chamber)'''
    #    self.inst.write()

    def state(self):
        out = self.inst.query_ascii_values('X', converter='s')
        out = str.rstrip(out[0])
        print(out)
    
    def set_t(self, T):
        '''Set temperature to arbitrary value in 0.1 mK. 
        Be careful! The value of temp has to be specified with 5 figures!
        Range is the command name for the power range (E1, E2 ...)'''

        cmd = 'E'
        if T<=35:
            cmd+='1'
        elif T<=55:
            cmd+='2'
        elif T<=140:
            cmd+='3'
        elif T<=400:
            cmd+='4'
        else:
            cmd+='5'

        self.execute(cmd)
        self.execute('T' + str(10*T))
