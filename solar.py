from collections.abc import Callable
from tkinter import *
from typing import Tuple
import numpy as np
import cv2
from PIL import Image, ImageTk
import sys
import RPi.GPIO as GPIO
import time
import board
import adafruit_dht

dhtDevice = adafruit_dht.DHT22(board.D4, use_pulseio=False)

class SolarCar(object):
    def __init__(self,
                 get_speed: Callable,
                 get_pos: Callable,
                 gps_dim: Tuple,
                 get_touch: Callable,
                 one_cycle_len: float,
                 get_temp: Callable,
                 live_video: Callable):
        if (gps_dim[0] > gps_dim[2]) or (gps_dim[1] > gps_dim[3]):
            print('Wrong GPS boundary')
            sys.exit(1)
        root = Tk()
        root.geometry('1024x600')
        root.title('Kent Solar Car')

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
        self.root = root
        self.speed_str = StringVar()
        self.touch_sensor_str = StringVar()
        self.time_str = StringVar()
        self.temp_str = StringVar()
        self.speed_label = Label(self.root,
                                 textvariable=self.speed_str,
                                 font=('Arial', 15, 'bold'))
        self.touch_sensor_label = Label(self.root,
                                 textvariable=self.touch_sensor_str,
                                 font=('Arial', 15, 'bold'))
        self.time_label = Label(self.root,
                                 textvariable=self.time_str,
                                 font=('Arial', 15, 'bold'))
        self.temp_label = Label(self.root,
                                 textvariable=self.temp_str,
                                 font=('Arial', 15, 'bold'))
        self.speed_entry = Entry(self.root,
                                 textvariable=self.speed_str)
        self.reset_button = Button(self.root, text='Reset', command=self.reset_all)
        self.change_unit_button = Button(self.root, text='KM/MILE', command=self.change_unit)
        self.map = Label(self.root)

        self.speed_label.pack(pady=20)
        self.touch_sensor_label.pack(pady=20)
        self.time_label.pack(pady=20)
        self.temp_label.pack(pady=20)
        #self.reset_button.pack(pady=20)
        #self.change_unit_button.pack(pady=20)
        self.map.pack()

        self.update_live_video()
        self.update_speed()
        self.update_distance()
        self.update_temp()
        self.update_time()
        #self.speed_entry.pack()

    def update_temp(self):
        c, f = self.get_temp()
        self.temp_str.set(f'Temp: {c : .2f} C | {f : .2f} F')
        self.root.after(1000, self.update_temp)

    def change_unit(self):
        self.is_km ^= 1

    def update_time(self):
        x = time.time() - self.start_time
        x /= 60
        self.time_str.set(f'Time: {x : .2f} min')
        self.root.after(500, self.update_time)
        

    def update_distance(self):
        x = self.get_touch()
        if (self.previous_state != x) and (self.previous_state == 1):
            self.rot_counter += 1
        self.previous_state = x
        distance = self.rot_counter * self.one_cycle_len / 1000
        if self.is_km:
            self.touch_sensor_str.set(f'Distance: {distance : .3f} km')
        else:
            self.touch_sensor_str.set(f'Distance: {(distance / 1.61) : .3f} mil ')
        self.distance = self.rot_counter * self.one_cycle_len
        self.touch_sensor_label.after(1, self.update_distance)

    def update_speed(self):
        # get current time
        time_passed = self.speed_update_interval / 1000 / 60 / 60 # h
        distance_covered = (self.distance - self.previous_distance) / 1000 # km
        current_speed = distance_covered / time_passed

        if self.is_km:
            self.speed_str.set(f'Speed: {current_speed : .2f} kmph')
        else:
            self.speed_str.set(f'Speed: {current_speed / 1.61 : .3f} mph')
        self.previous_distance = self.distance
        self.root.after(self.speed_update_interval, self.update_speed)
    
    def get_window_dim(self):
        return self.root.winfo_width(), self.root.winfo_height()

    def get_map_dim(self):
        return self.map.winfo_width(), self.map.winfo_height()

    def update_live_video(self):
        m_x, m_y = self.get_map_dim()
        map_image_resized = cv2.cvtColor(self.live_video(), cv2.COLOR_BGR2RGBA)
        map_image_resized = Image.fromarray(map_image_resized)
        
        self.map_image_tk = ImageTk.PhotoImage(image=map_image_resized)
        self.map.configure(image=self.map_image_tk)
        self.map.after(10, self.update_live_video)

    def gps_to_map(self, x):
        if (x[0] < self.gps_dim[0]) or \
           (x[0] > self.gps_dim[2]) or \
           (x[1] < self.gps_dim[1]) or \
           (x[1] > self.gps_dim[3]):
               print('Out of boundary')
               return 0, 0
        m_x, m_y = self.get_map_dim()
        current_x = (x[0] - self.gps_dim[0]) / (self.gps_dim[2] - self.gps_dim[0])
        current_y = (x[1] - self.gps_dim[1]) / (self.gps_dim[3] - self.gps_dim[1])
        current_x *= m_x
        current_y *= m_y
        return current_x, current_y

    def start_loop(self):
        self.root.mainloop()

    def reset_all(self):
        self.start_time = time.time()
        self.distance = 0
        self.previous_distance = 0
        self.previous_state = 1
        self.rot_counter = 0

    def get_image_dim():
        return self.live_video_canvas.winfo_width(), self.live_video_canvas.winfo_height()

        

def get_speed():
    return float(np.random.rand())

def get_pos():
    x_len = gps_dim[2] - gps_dim[0]
    y_len = gps_dim[3] - gps_dim[1]
    x_base = gps_dim[0]
    y_base = gps_dim[1]
    return float(np.random.rand() * x_len + x_base), float(np.random.rand() * y_len + y_base)

def setup_touch_sensor(input_pin=27):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(input_pin, GPIO.IN)

def get_touch_sensor(input_pin=27):
    return GPIO.input(input_pin)

def get_temp():
    try:
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        return temperature_c, temperature_f
    except:
        print('Temp Sensor failure')
        return -1, -1

video = cv2.VideoCapture(0)

def live_video():
    ret, image = video.read()
    if not ret:
        print('failed')
    else:
        return image
        #print(image.min(), image.max(), image.mean())
    #cv2.waitKey(1)


gps_dim = (41.72454112609995, -73.4811918422402, 41.72635922342008, -73.47515215049468)
setup_touch_sensor()
solar = SolarCar(get_speed, get_pos, gps_dim, get_touch_sensor, 2.153412, get_temp, live_video)
solar.start_loop()
