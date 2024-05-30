import serial
from collections.abc import Callable
from tkinter import *
from typing import Tuple
import numpy as np
import cv2
from PIL import Image, ImageTk
import sys
###import RPi.GPIO as GPIO
import time
###import board
###import adafruit_dht

###dhtDevice = adafruit_dht.DHT22(board.D4, use_pulseio=False)



class VideoWidget(Frame):
    def __init__(self, parent, video_source=0):
        super().__init__(parent)
        self.video_source = video_source
        self.video = cv2.VideoCapture(self.video_source)
        self.video_label = Label(self)
        self.video_label.pack()
        
        self.speed_label = Label(self, text="Speed: ", font=('Arial', 45))
        self.speed_label.place(x=20, y=30)

        self.distance_label = Label(self, text="Distance: ", font=('Arial', 45))
        self.distance_label.place(x=20, y=100)

        self.temp_label = Label(self, text="Temperature: ", font=('Arial', 45))
        self.temp_label.place(x=20, y=170)

        self.time_label = Label(self, text="Time: ", font=('Arial', 45))
        self.time_label.place(x=20, y=240)

        self.serial_data_label = Label(self, text="", font=('Arial', 45))  # Add a label for serial data
        self.serial_data_label.place(x=20, y=310)
        
        #self.next_data_button = Button(self, text="Next Data", font=('Arial', 20), command=self.show_next_data)
        #self.next_data_button.place(x=20, y=380)

        self.pack()
        self.update()


    def update(self):
        ret, frame = self.video.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            frame = cv2.resize(frame, (1920, 1080))
            frame = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image=frame)
            self.video_label.configure(image=photo)
            self.video_label.image = photo
        self.after(10, self.update)

    def update_info_labels(self, speed_str, distance_str, temp_str, time_str):
        self.speed_label.config(text=speed_str)
        self.distance_label.config(text=distance_str)
        self.temp_label.config(text=temp_str)
        self.time_label.config(text=time_str)

    def update_serial_data_label(self, serial_data):
        self.serial_data_label.config(text=serial_data)  # Update serial data label



desired_ports = ['V', 'I', 'PPV']

class SolarCar(object):
    def __init__(self,
                 get_speed: Callable,
                 get_pos: Callable,
                 gps_dim: Tuple,
                 get_touch: Callable,
                 one_cycle_len: float,
                 get_temp: Callable,
                 live_video: Callable,
                 serial_port: str = '/dev/ttyUSB0',  # Default serial port
                 baud_rate: int = 19200):  # Pass the VideoWidget instance
        if (gps_dim[0] > gps_dim[2]) or (gps_dim[1] > gps_dim[3]):
            print('Wrong GPS boundary')
            sys.exit(1)
        self.root = Tk()
        self.root.geometry('1920x1080')
        self.root.title('Kent Solar Car')

        ser = serial.Serial('/dev/ttyUSB0', 19200)
        self.video_widget = VideoWidget(self.root, video_source=0)
        self.setup_serial_communication(serial_port, baud_rate)

        self.data = {key: 'NA' for key in desired_ports}
        self.update_serial_data_label() 
        self.update_serial_data_label_str()
        

        self.frame = Frame(self.root)
        self.frame.pack()

        self.speed_update_interval = 1000
        self.is_km = 1
        self.previous_distance = 0
        self.distance = 0
        self.start_time = time.time()
        self.one_cycle_len = one_cycle_len
        self.get_touch = get_touch
        self.gps_dim = gps_dim
        self.get_speed = get_speed
        self.get_pos = get_pos
        self.get_temp = get_temp
        self.live_video = live_video
        self.rot_counter = 0
        self.previous_state = 1
        self.speed_str = StringVar()
        self.touch_sensor_str = StringVar()
        self.time_str = StringVar()
        self.temp_str = StringVar()

        self.update_speed()
        self.update_distance()
        self.update_temp()
        self.update_time()
        self.setup_serial_communication(serial_port, baud_rate)  # Setup serial communication

    def setup_serial_communication(self, serial_port, baud_rate):
        self.ser = serial.Serial(serial_port, baud_rate)

    def update_serial_data_label(self):
        try:
            line = self.ser.readline().decode('latin-1').strip()
            line_key, line = line.split('\t')
            if line_key in desired_ports:
                self.data[line_key] = line
        except Exception as e:
            print(f"Failed to read data from serial port: {e}")
        self.root.after(200, self.update_serial_data_label)
    
    def update_serial_data_label_str(self):
        tmp = ''
        for line_key in desired_ports:
            if line_key == 'V' and self.data[line_key] != 'NA':
                tmp += f'{line_key}: {float(self.data[line_key]) / 1000} | '
            else:
                tmp += f'{line_key}: {self.data[line_key]} | '
        self.video_widget.update_serial_data_label(tmp)
        self.root.after(1000, self.update_serial_data_label_str)

    def update_temp(self):
        try:
            c, f = self.get_temp()
            self.temp_str.set(f'Temp: {c:.2f} C | {f:.2f} F')
            self.video_widget.update_info_labels(self.speed_str.get(), self.touch_sensor_str.get(), self.temp_str.get(), self.time_str.get())  # Update VideoWidget
            self.root.after(1000, self.update_temp)
        except:
            return

    def update_time(self):
        x = time.time() - self.start_time
        x /= 60
        self.time_str.set(f'Time: {x:.2f} min')
        self.video_widget.update_info_labels(self.speed_str.get(), self.touch_sensor_str.get(), self.temp_str.get(), self.time_str.get())  # Update VideoWidget
        self.root.after(500, self.update_time)

    def update_distance(self):
        x = self.get_touch()
        if (self.previous_state != x) and (self.previous_state == 1):
            self.rot_counter += 1
        self.previous_state = x
        distance = self.rot_counter * self.one_cycle_len / 1000
        if self.is_km:
            self.touch_sensor_str.set(f'Distance: {distance:.3f} km')
        else:
            self.touch_sensor_str.set(f'Distance: {(distance / 1.61):.3f} mil ')
        self.distance = self.rot_counter * self.one_cycle_len
        self.video_widget.update_info_labels(self.speed_str.get(), self.touch_sensor_str.get(), self.temp_str.get(), self.time_str.get())  # Update VideoWidget
        self.root.after(1, self.update_distance)

    def update_speed(self):
        # get current time
        time_passed = self.speed_update_interval / 1000 / 60 / 60  # h
        distance_covered = (self.distance - self.previous_distance) / 1000  # km
        current_speed = distance_covered / time_passed

        if self.is_km:
            self.speed_str.set(f'Speed: {current_speed:.2f} kmph')
        else:
            self.speed_str.set(f'Speed: {current_speed / 1.61:.3f} mph')
        self.previous_distance = self.distance
        self.video_widget.update_info_labels(self.speed_str.get(), self.touch_sensor_str.get(), self.temp_str.get(), self.time_str.get())  # Update VideoWidget
        self.root.after(self.speed_update_interval, self.update_speed)

    def start_loop(self):
        self.root.mainloop()

def get_speed():
    return float(np.random.rand())

def get_pos():
    x_len = gps_dim[2] - gps_dim[0]
    y_len = gps_dim[3] - gps_dim[1]
    x_base = gps_dim[0]
    y_base = gps_dim[1]
    return float(np.random.rand() * x_len + x_base), float(np.random.rand() * y_len + y_base)

def setup_touch_sensor(input_pin=27):
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(input_pin, GPIO.IN)
    except:
        print('No GPIO')
        return

def get_touch_sensor(input_pin=27):
    try:
        return GPIO.input(input_pin)
    except:
        return

def get_temp():
    try:
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        return temperature_c, temperature_f
    except:
        print('Temp Sensor failure')
        return -1, -1


#video = cv2.VideoCapture(0)
def live_video():
    ret, image = video.read()
    if not ret:
        print('failed')
    else:
        return image


gps_dim = (41.72454112609995, -73.4811918422402, 41.72635922342008, -73.47515215049468)
setup_touch_sensor()


#video_widget = VideoWidget(self.root)  # Create an instance of VideoWidget
solar = SolarCar(get_speed, get_pos, gps_dim, get_touch_sensor, 2.153412, get_temp, live_video, serial_port='/dev/ttyUSB0', baud_rate=19200)  # Pass video_widget as an argument
solar.start_loop()
