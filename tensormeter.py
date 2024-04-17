# -*- coding: utf-8 -*-
"""
Created on Tue May  9 15:48:01 2023

@author: local_admin
"""

import numpy as np
import time
import socket
import struct
from time import sleep
import serial

class tensormeter:
    
    def __init__(self, N_samples, n_max_attempts = 10, HOST = 'localhost', PORT = 6340  ):
        #HOST = 'localhost'  # The server's hostname or IP address
        #PORT = 6340         # The port used by the server
        
        self.N_samples = N_samples
        self.n_max_attempts = n_max_attempts
        socket.setdefaulttimeout(0.5)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((HOST, PORT))
    
    def fomt(self,c):
        switcher = {
            'lfrq': 'd',
            'meas': 'i',
            'sres': 'd',
            'avgt': 'd',
            'vamp': 'd',
            'camp': 'd',
            'vodc': 'd',
            'cudc': 'd',
            'virg': 'd',
            'vorg': 'd',
            'crng': 'd',
            'vpro': 'd',
            'cpro': 'd',
            'amod': 'H',
            'mod?': 'H',
            'cmod': 'H',
            'tcai': '?',
            'trmo': 'i',
            'refe': '?',
        }
        return switcher.get(c,'b')
    
    
    def send_meas(self, N_samples):
        value = struct.pack('>i', N_samples)
        
        size_value = struct.calcsize('i')

        command = b'meas'
        size_command = 4
        size = size_command + size_value
        size = struct.pack('>i', size)
        self.s.sendall(size+command+value)
        
    def send_vodc(self, voltage):
        value = struct.pack('>d', voltage)
        
        size_value = struct.calcsize('d')
        command = b'vodc'
        size_command = 4
        size = size_command + size_value
        size = 12
        size = struct.pack('>i', size)
        self.s.sendall(size+command+value)
    
    def send_cldt(self):
        command = b'cldt'
        size_command = 4
        size = size_command
        size = struct.pack('>i', size)
        self.s.sendall(size+command)
    
    def send_newd(self):
        command = b'newd'
        size_command = 4
        size = size_command
        size = struct.pack('>i', size)
        self.s.sendall(size+command)
        
    def send_alld(self):
        command = b'alld'
        size_command = 4
        size = size_command
        size = struct.pack('>i', size)
        self.s.sendall(size+command)
        
    def empty(self):
        self.s.recv(1)
        return
        
    def get_data(self, int_time):
        got_all_data = False
        
        n_failed_attempts = 0
        n_max_attempts = self.n_max_attempts
        #time.sleep(int_time)
        while not got_all_data and n_failed_attempts< n_max_attempts:
            self.send_newd()
            
            done = False
            
            
            while not done:
                #print("reading length...")
                length = struct.unpack('>i', self.s.recv(4))[0]
                #print("reading command...")
                command = struct.unpack('>4s', self.s.recv(4))
                command = command[0].decode("ascii")
                #print("command: ", command, "length: ", length)
                
                if command=="newd":
                    try:
                        rows = struct.unpack('>i', self.s.recv(4))[0]
                        columns = struct.unpack('>i', self.s.recv(4))[0]
                        X = rows*columns
                        #print("reading data... rows: ",rows, " colmuns: ",columns)
                        #rawdata = self.s.recv(4096)
                        #while len(rawdata) != X*8:
                        #    rawdata += self.s.recv(4096)
                        
                        max_msg_size = 4096
                        msg_len = X*8
                        rawdata = bytearray(msg_len )
                        pos = 0
                        while pos < msg_len:
                            rawdata[pos:pos+max_msg_size] = self.s.recv(max_msg_size)
                            pos += max_msg_size
                        
                        fmt = ">"+str(X)+"d"
                        
                        rawdata = struct.unpack(fmt,rawdata)[0:X]
                        
                        rawdata = np.array(rawdata)
                        
                        rawdata = rawdata.reshape(rows,columns)
                        
                        got_all_data = True
                        
                        #print(rawdata)
                        print(rawdata.shape)
                        print(rawdata[0,0],rawdata[-1,0])
                        print(rawdata[0,0]-rawdata[-1,0])
                        #print( np.abs(rawdata[:,0]-rawdata[-1,0])<int_time )
                        #print( rawdata[:,0][np.abs(rawdata[:,0]-rawdata[-1,0])<int_time].shape )
                        
                        valids = rawdata[:,0][np.abs(rawdata[:,0]-rawdata[-1,0])<int_time].shape[0]
                        rawdata = rawdata[-valids:,:]
 
                        #print(rawdata)
                        print(rawdata.shape)
                        print(rawdata[0,0],rawdata[-1,0])
                        print(rawdata[0,0]-rawdata[-1,0])
                        
                        return rawdata, n_max_attempts
                    
                    except Exception as e:
                        print(e)
                        n_failed_attempts += 1
                        print("failed.. ",n_failed_attempts)
                        pass
                    
                    done=True
                    
                    
                else:
                    rcv = self.s.recv(length-4)
            
        print("Could not retrieve data!")    
        
    def get_all_data(self):
        got_all_data = False
        
        n_failed_attempts = 0
        n_max_attempts = 10
        #time.sleep(int_time)
        while not got_all_data and n_failed_attempts< n_max_attempts:
            self.send_alld()
            
            done = False
            
            
            while not done:
                #print("reading length...")
                length = struct.unpack('>i', self.s.recv(4))[0]
                #print("reading command...")
                command = struct.unpack('>4s', self.s.recv(4))
                command = command[0].decode("ascii")
                #print("command: ", command, "length: ", length)
                
                if command=="alld":
                    try:
                        rows = struct.unpack('>i', self.s.recv(4))[0]
                        columns = struct.unpack('>i', self.s.recv(4))[0]
                        X = rows*columns
                        #print("reading data... rows: ",rows, " colmuns: ",columns)
                        #rawdata = self.s.recv(4096)
                        #while len(rawdata) != X*8:
                        #    rawdata += self.s.recv(4096)
                        
                        max_msg_size = 4096
                        msg_len = X*8
                        rawdata = bytearray(msg_len )
                        pos = 0
                        while pos < msg_len:
                            rawdata[pos:pos+max_msg_size] = self.s.recv(max_msg_size)
                            pos += max_msg_size
                        
                        fmt = ">"+str(X)+"d"
                        
                        rawdata = struct.unpack(fmt,rawdata)[0:X]
                        
                        rawdata = np.array(rawdata)
                        
                        rawdata = rawdata.reshape(rows,columns)
                        
                        got_all_data = True
                        
                        #print(rawdata)
                        print(rawdata.shape)
                        print(rawdata[0,0],rawdata[-1,0])
                        print(rawdata[0,0]-rawdata[-1,0])
                        #print( np.abs(rawdata[:,0]-rawdata[-1,0])<int_time )
                        #print( rawdata[:,0][np.abs(rawdata[:,0]-rawdata[-1,0])<int_time].shape )
                        
                        #valids = rawdata[:,0][np.abs(rawdata[:,0]-rawdata[-1,0])<int_time].shape[0]
                        #rawdata = rawdata[-valids:,:]
 
                        #print(rawdata)
                        print(rawdata.shape)
                        print(rawdata[0,0],rawdata[-1,0])
                        print(rawdata[0,0]-rawdata[-1,0])
                        
                        return rawdata, n_max_attempts
                    
                    except Exception as e:
                        print(e)
                        n_failed_attempts += 1
                        print("failed.. ",n_failed_attempts)
                        pass
                    
                    done=True
                    
                    
                else:
                    rcv = self.s.recv(length-4)
            
        print("Could not retrieve data!")   
                
        
#%%
if __name__ == "__main__":
    tens = tensormeter(0)

#%%
def measure_data_point(tens, int_time=1):
    #tens.send_meas(-1)
    tens.send_cldt()
    t0 = time.time()
    print("integrate...")
    while time.time()-t0<int_time:
        pass
    print("request data")
    d,a = tens.get_all_data()
    print(d[:,9].mean())
    return d[:,9].mean()





            
        
        
        
        