#Valve controller 
import sys
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QWidget, QGridLayout, QPushButton
from qtwidgets import AnimatedToggle
from functools import partial
from PyQt5 import QtCore
import time
import keyboard
import serial
import re
from tqdm import tqdm

def relayOn(n):
    relay_number = n-1
    write_data = "L" + chr(relay_number)
    ser.write(write_data.encode())
    
    #time.sleep(1)
    #Empty the input buffer
    #ser.flushInput()

'''Relay OFF''' 
def relayOff(n):
    relay_number = n-1
    write_data = "H" + chr(relay_number)
    ser.write(write_data.encode())
    
    #time.sleep(1)
    #Empty the input buffer
    #ser.flushInput()

def relayAllOff():
    for i in range(1, 32):
        relayOff(i)

def relayAllOn():
    for i in range(1, 32):
        relayOn(i)


def generatePulse(valve1=1,valve2=5,time1=0.5,time2=2,time3=4):
        relayOff(1)
        relayOff(3)
        relayOff(16)
        time.sleep(time1)
        relayOn(1)
        relayOn(3)
        time.sleep(time2)
        relayOff(2)
        time.sleep(0.5)
        relayOff(5)
        time.sleep(time3)
        relayOff(3)
        relayOn(5)
        time.sleep(time3)
        relayOn(3)
        relayOn(2)





def  getNumber(valve_names,valve_name):

    for number in valve_names:
        if valve_names[number] == valve_name:
            return_number = number
    return return_number


#Open port for communication	
ser = serial.Serial('COM4', 9600, timeout=1)

relayAllOn()

valve_states = {}

valve_names = {
    1: 'A 1',
    2: 'A 2',
    3: 'A 3',
    4: 'A 4',
    5: 'A 5',
    6: 'A 6',
    7: 'A 7',
    8: 'A 8',
    9: 'B 1',
    10: 'B 2',
    11: 'B 3',
    12: 'B 4',
    13: 'B5',
    14: 'B6',
    15: 'B7',
    16: 'B8',
    17: 'Valve 17',
    18: 'Valve 18',
    19: 'Valve 19',
    20: 'Valve 20',
    21: 'Valve 21',
    22: 'Valve 22',
    23: 'Valve 23',
    24: 'Valve 24',
    25: 'Valve 25',
    26: 'Valve 26',
    27: 'Valve 27',
    28: 'Valve 28',
    29: 'Valve 29',
    30: 'Valve 30'}



def toggle_valve(valve_name):
    valve_states[valve_name] = not valve_states[valve_name]

def update_valve_state(valve_name):
    if valve_states[valve_name] == True:
        # Code to turn on the valve
        relayOff(getNumber(valve_names,valve_name))
        toggle_valve(valve_name)
        #print(f" '{valve_name}' turned OFF")
    else:
        # Code to turn off the valve
        relayOn(getNumber(valve_names,valve_name))
        toggle_valve(valve_name)
        #print(f" '{valve_name}' turned ON")

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Valve control panel')
        self.setGeometry(100, 100, 400, 400)
        #self.setStyleSheet('background-color: black;')
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QGridLayout()
        central_widget.setLayout(layout)

        rows = 4
        columns = 8
        button_count = 30

        for i in range(24):
            button = AnimatedToggle(
                checked_color="#68C16E",
                pulse_checked_color="#44FFB000"
            )
            valve_name = valve_names[i+1]
            valve_states[valve_name] = True
            button.setCheckable(True)
            button.setChecked(True)
            button.clicked.connect(partial(update_valve_state, valve_name))
            label = QLabel(valve_names[i+1])
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label, 2 * (i // columns), (i % columns))
            layout.addWidget(button, 2 * (i // columns) + 1, (i % columns))




        ############additional valve
        button1 = QPushButton('123')
        button1.setText("generate Pulse")
        #button1.move(64,32)
        button1.clicked.connect(generatePulse)
        layout.addWidget(button1, 12 , 2)






        exit_button = QPushButton('Exit')
        exit_button.clicked.connect(relayAllOn)
        exit_button.clicked.connect(QApplication.instance().quit)
        exit_button.clicked.connect(QApplication.closeAllWindows)
        exit_button.clicked.connect(QApplication.exit)
        layout.addWidget(exit_button, 2 * (button_count // columns), 0, 1, columns)

        self.show()

relayAllOn()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    sys.exit(app.exec_())





