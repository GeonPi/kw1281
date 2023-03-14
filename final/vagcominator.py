#
#   You MUST plug the arduino first
#

#!/usr/bin/python3
import os
import argparse
import sys
import serial
import time
import binascii
import hashlib
import serial.tools.list_ports
import tkinter as tk
from tkinter.messagebox import *
from tkinter.filedialog import *
from scipy import interpolate

WIDTH  = 850
HEIGHT = 400
WAIT   = 1     #ms

CMD_INIT  = ("I" + chr(10))
CMD_HOME  = ("H" + chr(10))
CMD_ERROR = ("E" + chr(10))
CMD_CLEAR = ("C" + chr(10))

ID_PACKET_INFO_ECU          = 246    # xF6
ID_PACKET_GROUP_DESCRIPTION = 2      # x02
ID_PACKET_GROUP_VALUE       = 244    # xF4
ID_PACKET_ERROR_CODE        = 252    # xFC
ID_PACKET_NO_DATA           = 9      # x09

ERR_CODE_NO_ERROR           = 65535  # xFFFF
ERR_CODE_THROTTLE           = 518
ERR_CODE_ENGINE_TEMPERATURE = 522
ERR_CODE_AIR_TEMPERATURE    = 523
ERR_CODE_LAMBDA             = 525
ERR_CODE_VAF                = 552
ERR_TYPE_NO_SIGNAL           = 28
ERR_TYPE_NO_POSITIVE_SIGNAL  = 30
ERR_TYPE_NO_NEGATIVE_SIGNAL  = 31
ERR_TYPE_INTERMITTENT_SIGNAL = 162

DESCR_ENGINE_TEMPERATURE    = "Engine T°C"
DESCR_AIR_TEMPERATURE       = "Air T°C"
DESCR_RPM                   = "RPM"
DESCR_LAMBDA                = "Lambda"
DESCR_THROTTLE              = "Throttle Angle"
DESCR_CHARGE                = "Charge"
DESCR_INJECTION_DURATION    = "Injection Duration"
DESCR_IGNITION_TIMING       = "Ignition Timing"
DESCR_VOLTAGE               = "Voltage"
DESCR_ENGINE_STATE        = "Engine State"
DESCR_UNKNOWN               = "Unknown"

X_TEMPERATURE   = [-40, 0, 25, 50, 75, 102]
Y_TEMPERATURE   = [224, 109, 54, 24, 12, 5]
X_IGNITION      = [-4, 0, 7, 15, 20, 25, 30]
Y_IGNITION      = [34, 30, 23, 15, 10, 5, 0]
X_RPM           = [598, 1482, 2470, 5538, 5772, 6240]
Y_RPM           = [229, 176, 131, 38, 34, 7]


class Application(tk.Frame):
    def __init__(self, master = None):
        super().__init__(master)
        self.master = master
        self.ser = None
        self.port = ""
        self.input = ""
        self.sendToDecoding = False
        self.packet = []            #integer MSB
        self.infoEcu = 0
        self.packetSize = 0
        self.errors = []
        self.cmd = ''
        self.idGroup = 0
        self.activeGroup = 0
        self.fTemperature = interpolate.interp1d(Y_TEMPERATURE, X_TEMPERATURE, "quadratic")
        self.fIgnition = interpolate.interp1d(Y_IGNITION, X_IGNITION, "quadratic")
        self.fRpm = interpolate.interp1d(Y_RPM, X_RPM, "quadratic")
        self.create_widgets(master)


    #send init sequence
    def init_com(self):
        self.init_button.config(bg="red")
        while(1):
            print("Waiting for arduino...")
            l = self.ser.readline().decode()
            if(l == 'Ready\r\n'):
                print("Arduino is ready")
                break
        print("Send command: \"Init\"")
        sys.stdout.flush()
        self.ser.write(CMD_INIT.encode())
        self.waitokay()
        self.get_raw()

    def get_raw(self):
        sys.stdout.flush()
        l = self.ser.readline().decode()

        if(l):
            if(l == "start\r\n"):
                print(l, end="")
            elif(l == "stop\r\n"):
                self.sendToDecoding = True
                self.stop = True
                print(l, end="")
            else:
                self.packet.append(int('{:08b}'.format(int(l, 2))[::-1], 2))    #LSB to MSB to integer
                print("\t" + l, end="")

            if(self.sendToDecoding):
                self.decode_packet()
                self.sendToDecoding = False

                if(self.cmd):
                    self.send_cmd()

        #execute itself every WAIT milliseconds
        self.after(WAIT, self.get_raw)

    def send_cmd(self):
        sys.stdout.flush()
        self.ser.write(self.cmd.encode())
        self.waitokay()

        if(self.cmd == CMD_CLEAR):
            self.error_text.config(state='normal')
            self.error_text.delete("1.0", "end")
            self.error_text.config(state='disabled')
            self.clear_group_values()
        elif(self.cmd[0] == "M"):
            self.idGroup = int(self.cmd[1])
            self.set_description()

        self.cmd = ''

    def decode_packet(self):
        self.packetSize = self.packet[0]
        print("packet size = " + str(self.packetSize))

        if(ID_PACKET_INFO_ECU == self.packet[2]):
            if(self.infoEcu == 0):
                print("We got a packet: \"Serial Number\"")
                self.infoEcu += 1
                self.serialNumber_label['text'] = self.get_packet_data()
            elif(self.infoEcu == 1):
                print("We got a packet: \"Version\"")
                self.infoEcu += 1
                self.version_label['text'] = self.get_packet_data()
            elif(self.infoEcu == 2):
                print("We got a packet: \"Extra\"")
                self.infoEcu += 1
                self.extra_label['text'] = self.get_packet_data()
                self.init_button.config(bg="green")
        elif(ID_PACKET_GROUP_DESCRIPTION == self.packet[2]):        #don't care
            print("We got a packet: \"Group description\"")
        elif(ID_PACKET_GROUP_VALUE == self.packet[2]):
            print("We got a packet: \"Group value\"")
            self.get_group_values()
        elif(ID_PACKET_ERROR_CODE == self.packet[2]):
            print("We got a packet: \"Error code\"")
            self.clear_group_values()
            self.errors.clear()
            self.error_text.config(state='normal')
            self.error_text.delete("1.0", "end")
            self.get_error_codes()
            self.error_text.config(state='disabled')
        elif(ID_PACKET_NO_DATA == self.packet[2]):
            print("We got a packet: \"No data\"")
        else:
            print("We got a packet: \"Unknown...\"")
 
        self.packet.clear()

    def clear_group_values(self):
        self.v1_label['text'] = '_'
        self.v2_label['text'] = '_'
        self.v3_label['text'] = '_'
        self.v4_label['text'] = '_'
        self.reset_g_button_colour()
        
    def get_packet_data(self):
        s = ''
        for i in range(3, self.packetSize):
            s += chr(self.packet[i])
        return s

    def get_error_codes(self):
        #[error code, error type]
        for i in range(3, self.packetSize, 3):
            s = '{:08b}'.format(self.packet[i], 'b') + '{:08b}'.format(self.packet[i+1], 'b')
            self.errors.append([int(s, 2), self.packet[i+2]])

        #decoding
        for e in self.errors:
            if(e[0] == ERR_CODE_NO_ERROR):
                s = "   -- No error codes found --\n"
                self.error_text.insert("end", s)
            elif(e[0] == ERR_CODE_VAF):
                s = "   --" + str(e[0]) + " - Volume Air Flow sensor (G19)\n" + self.get_error_type(e[1])
                self.error_text.insert("end", s)
            elif(e[0] == ERR_CODE_LAMBDA):
                s = "   --" + str(e[0]) + " - Oxygen sensor (G39)\n" + self.get_error_type(e[1])
                self.error_text.insert("end", s)
            elif(e[0] == ERR_CODE_THROTTLE):
                s = "   --" + str(e[0]) + " - Throttle sensor (G69)\n" + self.get_error_type(e[1])
                self.error_text.insert("end", s)
            elif(e[0] == ERR_CODE_AIR_TEMPERATURE):
                s = "   --" + str(e[0]) + " - Air Temperature sensor (G42)\n" + self.get_error_type(e[1])
                self.error_text.insert("end", s)
            elif(e[0] == ERR_CODE_ENGINE_TEMPERATURE):
                s = "   --" + str(e[0]) + " - Engine Temperature sensor (G62)\n" + self.get_error_type(e[1])
                self.error_text.insert("end", s)
            else:
                self.error_text.insert("end", "   -- Unknown error --\n")
                self.error_text.insert("end", str(e[0]) + "\n" + str(e[1]))

    def get_error_type(self, e):
        if(e == ERR_TYPE_NO_POSITIVE_SIGNAL):
            return "\t\t30-00 No positive signal\n"
        elif(e == ERR_TYPE_NO_NEGATIVE_SIGNAL):
            return "\t\t31-00 No negative signal\n"
        elif(e == ERR_TYPE_INTERMITTENT_SIGNAL):
            return "\t\t34-10 Intermittent signal\n"
        elif(e == ERR_TYPE_NO_SIGNAL):
            return "\t\t28-00 No signal\n"
        else:
            return "\t\txx-xx Unknown error type\n"

    def set_description(self):
        self.d1_label['text'] = DESCR_ENGINE_TEMPERATURE
        self.d2_label['text'] = DESCR_RPM
        if(self.idGroup == 1):
            self.d3_label['text'] = DESCR_LAMBDA
            self.d4_label['text'] = DESCR_INJECTION_DURATION
        elif(self.idGroup == 2):
            self.d3_label['text'] = DESCR_THROTTLE
            self.d4_label['text'] = DESCR_CHARGE
        elif(self.idGroup == 3):
            self.d3_label['text'] = DESCR_AIR_TEMPERATURE
            self.d4_label['text'] = DESCR_VOLTAGE
        elif(self.idGroup == 4):
            self.d3_label['text'] = DESCR_IGNITION_TIMING
            self.d4_label['text'] = DESCR_CHARGE
        elif(self.idGroup == 6):
            self.d3_label['text'] = DESCR_UNKNOWN
            self.d4_label['text'] = DESCR_UNKNOWN
        elif(self.idGroup == 7):
            self.d3_label['text'] = DESCR_IGNITION_TIMING
            self.d4_label['text'] = DESCR_UNKNOWN
        elif(self.idGroup == 8):
            self.d3_label['text'] = DESCR_IGNITION_TIMING
            self.d4_label['text'] = DESCR_ENGINE_STATE            

    def get_group_values(self):
        self.values = []
        for i in range(3, self.packetSize):
            self.values.append(self.packet[i])

        self.v1_label['text'] = self.get_value_temperature(self.values[0])
        self.v2_label['text'] = self.get_value_rpm(self.values[1])

        if(self.idGroup == 1):
            self.v3_label['text'] = self.get_value_lambda(self.values[2])
            self.v4_label['text'] = self.get_value_injection_duration(self.values[3])
        elif(self.idGroup == 2):
            self.v3_label['text'] = self.get_value_throttle(self.values[2])
            self.v4_label['text'] = self.get_value_charge(self.values[3])
        elif(self.idGroup == 3):
            self.v3_label['text'] = self.get_value_temperature(self.values[2])
            self.v4_label['text'] = self.get_value_voltage(self.values[3])
        elif(self.idGroup == 4):
            self.v3_label['text'] = self.get_value_ignition(self.values[2])
            self.v4_label['text'] = self.get_value_charge(self.values[3])
        elif(self.idGroup == 6):
            self.v3_label['text'] = self.get_value_unknown(self.values[2])
            self.v4_label['text'] = self.get_value_unknown(self.values[3])
        elif(self.idGroup == 7):
            self.v3_label['text'] = self.get_value_ignition(self.values[2])
            self.v4_label['text'] = self.get_value_unknown(self.values[3])
        elif(self.idGroup == 8):
            self.v3_label['text'] = self.get_value_ignition(self.values[2])
            self.v4_label['text'] = self.get_value_cycle(self.values[3])

    def get_value_temperature(self, v):
        if(v > Y_TEMPERATURE[0]):
            v = Y_TEMPERATURE[0]
        elif(v < Y_TEMPERATURE[-1]):
            v = Y_TEMPERATURE[-1]
        return str(int(self.fTemperature(v))) + "°C" 

    def get_value_rpm(self, v):
        if(v > Y_RPM[0]):
            v = Y_RPM[0]
        elif(v < Y_RPM[-1]):
            v = Y_RPM[-1]
        return str(int(self.fRpm(v))) + " r/min"

    def get_value_ignition(self, v):
        if(v > Y_IGNITION[0]):
            v = Y_IGNITION[0]
        elif(v < Y_IGNITION[-1]):
            v = Y_IGNITION[-1]
        return str(int(self.fIgnition(v))) + "°"

    def get_value_lambda(self, v):
        return str(round(v / 128, 2)) + "v"

    def get_value_injection_duration(self, v):
        return str(round(v / 2, 2)) + "ms"

    def get_value_charge(self, v):
        return str(round(v / 2.56, 2)) + "%"

    def get_value_throttle(self, v):
        return str(v) + "°"

    def get_value_voltage(self, v):
        return str(v) + "v"

    def get_value_unknown(self, v):
        return str(v)

    def get_value_cycle(self, v):
        if(v == 0):
            return "Mid load"
        elif(v == 1):
            return "Idling"
        else:
            return "Full load"


    def info(self, text):
        tk.messagebox.showinfo("Info", text)

    def warning(self, text):
        tk.messagebox.showwarning("Warning", text)

    def set_port(self, value):
        try:
            self.ser.close()
        except:
            pass

        self.ser = serial.Serial(self.var.get(), 2000000, timeout = 0.1)
        time.sleep(1)
        self.port = self.var.get()
        print(self.port + " is set")

    def focus_text(self, event):
        self.error_text.config(state='normal')
        self.error_text.focus()
        self.error_text.config(state='disabled')

    def create_widgets(self, master):
        self.row1 = tk.Frame(self.master)
        self.row2 = tk.Frame(self.master)
        self.row1.pack()
        self.row2.pack()
        
        self.lRow1 = tk.Frame(self.row1, width=WIDTH * 0.3, height=HEIGHT * 0.35)
        self.rRow1 = tk.Frame(self.row1, width=WIDTH * 0.8, height=HEIGHT * 0.35)
        self.lRow2 = tk.Frame(self.row2, width=WIDTH * 0.3, height=HEIGHT * 0.65)
        self.rRow2 = tk.Frame(self.row2, width=WIDTH * 0.8, height=HEIGHT * 0.65)
        
        self.lRow1.pack_propagate(0)    #prevent from auto-resizing
        self.rRow1.pack_propagate(0)
        self.lRow2.pack_propagate(0)
        self.rRow2.pack_propagate(0)
        
        self.lRow1.pack(side=tk.LEFT)
        self.rRow1.pack(side=tk.RIGHT)
        self.lRow2.pack(side=tk.LEFT)
        self.rRow2.pack(side=tk.RIGHT)
        
        self.d_frame = tk.Frame(self.rRow1)
        self.b_frame = tk.Frame(self.rRow1)
        self.d_frame.pack_propagate(0)
        self.b_frame.pack_propagate(0)
        self.d_frame.pack()
        self.b_frame.pack()
        
        #PORT
        self.ports = serial.tools.list_ports.comports()     #ports[0][0] = '/dev/ttyUSB0', ports[0][1] = 'USB Serial'
        self.values = []
        for p in self.ports:
            self.values.append(p[0])
        if self.values:
            if "/dev/ttyUSB0" in self.values:
                self.var = tk.StringVar(value = "/dev/ttyUSB0")
            elif "COM3" in self.values:
                self.var = tk.StringVar(value = "COM3")
            else:
                self.var = tk.StringVar(value = self.values[0])
        else:
            self.warning("No ports finded!")
            sys.exit("No ports finded!")

        #UPPER LEFT(INIT, S/N, Version, Extra)
        self.serialNumber_label = tk.Label(self.lRow1, text="Serial Number", relief="sunken")
        self.version_label = tk.Label(self.lRow1, text="Version", relief="sunken")
        self.extra_label = tk.Label(self.lRow1, text="Extra info",relief="sunken")
        self.serialNumber_label.pack(fill='x', padx=2, pady=10)
        self.version_label.pack(fill='x', padx=2, pady=10)
        self.extra_label.pack(fill='x', padx=2, pady=10)
        
        #LOWER LEFT(Get Error, Clear Error, Port)
        self.error_button = tk.Button(self.lRow2, text="Get Error(s)", command=self.ev_get_errors)
        self.clear_button = tk.Button(self.lRow2, text="Clear Error(s)", command=self.ev_clear_errors)
        self.menuport = tk.OptionMenu(self.lRow2, self.var, *self.values, command = self.set_port)
        self.init_button = tk.Button(self.lRow2, text="INIT", command=self.init_com)
        self.error_button.pack(pady=5)
        self.clear_button.pack(pady=10)
        self.menuport.pack(pady=5)
        self.init_button.pack(pady=10)
        self.set_port(self.var)

        #UPPER RIGHT(Group descriptions, Groups values, Groups buttons)
        self.d1_label = tk.Label(self.d_frame, text="_", width=15, relief="sunken")
        self.d2_label = tk.Label(self.d_frame, text="_", width=15, relief="sunken")
        self.d3_label = tk.Label(self.d_frame, text="_", width=15, relief="sunken")
        self.d4_label = tk.Label(self.d_frame, text="_", width=15, relief="sunken")
        self.d1_label.grid(row=0, column=0, padx=5, pady=10)
        self.d2_label.grid(row=0, column=1, padx=5, pady=10)
        self.d3_label.grid(row=0, column=2, padx=5, pady=10)
        self.d4_label.grid(row=0, column=3, padx=5, pady=10)
        self.v1_label = tk.Label(self.d_frame, text="_", width=15, relief="sunken")
        self.v2_label = tk.Label(self.d_frame, text="_", width=15, relief="sunken")
        self.v3_label = tk.Label(self.d_frame, text="_", width=15, relief="sunken")
        self.v4_label = tk.Label(self.d_frame, text="_", width=15, relief="sunken")
        self.v1_label.grid(row=1, column=0, padx=5, pady=5)
        self.v2_label.grid(row=1, column=1, padx=5, pady=5)
        self.v3_label.grid(row=1, column=2, padx=5, pady=5)
        self.v4_label.grid(row=1, column=3, padx=5, pady=5)
        self.g_button = []
        for i in range(1, 9):
            if i == 5:
                continue
            name = "G" + str(i)
            self.g_button.append(tk.Button(self.b_frame, text=name, relief="raised", command=lambda i=i:self.ev_get_group(str(i))))
        for i in range(7):
            self.g_button[i].grid(row=0, column=i, padx=10, pady=10)
        self.defaultColour = self.g_button[0].cget('bg')

        #LOWER RIGHT(Error codes)
        self.scrolly = tk.Scrollbar(self.rRow2)
        self.scrolly.pack(side = tk.RIGHT, fill = tk.Y)

        self.error_title_label = tk.Label(self.rRow2, text="ERROR CODES")
        self.error_title_label.pack(side=TOP)
        self.error_text = tk.Text(self.rRow2, height=1, relief="sunken")
        self.error_text.insert(1.0, 'lol')
        self.error_text.configure(state="disabled")
        self.error_text.pack(fill="both", expand="yes")
        self.error_text.bind('<Button-1>', self.focus_text)
        self.scrolly.config(command = self.error_text.yview)


    def ev_get_errors(self):
        print("Request command to send: \"Get Errors\"")
        self.clear_group_values()
        self.cmd = CMD_ERROR

    def ev_clear_errors(self):
        print("Request command to send: \"Clear Errors\"")
        self.clear_group_values()
        self.cmd = CMD_CLEAR

    def ev_get_group(self, idGroup):
        print("Request command to send: \"Measuring Group " + idGroup + "\"")
        self.cmd = "M" + idGroup + chr(10)
        self.reset_g_button_colour()
        id_ = int(idGroup) - 1
        if(id_ > 4):
            id_ = id_ - 1
        self.g_button[id_].config(bg="yellow")

    def reset_g_button_colour(self):
        for g in self.g_button:
            g.config(bg=self.defaultColour)


    def waitokay(self):
        bad = 0
        while True:
            s = self.ser.readline().decode()
            if s == "OK\r\n":
                break
            else:
                bad = bad + 1
            if bad > 50:
                self.warning("Error timeout...")
                sys.exit("oops, error timeout...")




    

root = tk.Tk()
w = WIDTH
h = HEIGHT
ws = root.winfo_screenwidth()
hs = root.winfo_screenheight()
x = (ws/2) - (w/2)
y = (hs/2) - (h/2)
root.geometry('%dx%d+%d+%d' % (w, h, x, y))
app = Application(master = root)
app.master.title("VAGCOMINATOR")
app.mainloop()
