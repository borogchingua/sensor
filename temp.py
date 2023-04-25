import time
import glob
import os
import RPi.GPIO as GPIO
from RPLCD import CharLCD

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
sensor_locations = glob.glob('/sys/bus/w1/devices/28-*/w1_slave')
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
# dedicated output pins available on raspberry pi
gpio_pin_array = [22, 29, 31, 32, 35, 36, 37, 38]
error_logs = {}

# Initialize the LCD (assuming the 16x2 LCD connected to the Raspberry Pi)
lcd = CharLCD(numbering_mode=GPIO.BOARD, cols=16, rows=2,
              pin_rs=15, pin_e=16, pins_data=[56, 59, 61, 62])

# Function to display temperature data on the LCD


class Temp_zone:
    def __init__(self, sensor_ID, zone_ID, gpio_signal_pin, low_temp_value=0):
        '''
        Parameters
        ----------
        sensor_ID : String: local_address+ID+/w1_slave
            sensor ID access address from the root directory

        zone_ID : Numeric value of zone

        GPIO_pin : int
            dedicated GPIO output pin -> to relay

        low_temp_value : int
            Global variable input from user to establish lowest viable temperature

        Returns
        -------
        None.
        '''

        self.sensor_ID = sensor_ID
        self.zone_ID = zone_ID
        self.gpio_signal_pin = gpio_signal_pin
        self.current_temp = 0
        self.temp_logs = {}

        self.threshold = low_temp_value + (0.125 * low_temp_value)

        self.threshold_flag = False

    def temp_check(self):
        '''
        Compares current temperature against minimum threshold
        Updates threshold flag to turn on or off
        '''
        if self.current_temp <= self.threshold:
            self.threshold_flag = True

        elif self.current_temp > self.threshold:
            self.threshold_flag = False

    def gpio_pin_output(self):
        '''
        Sends signal to dedicated GPIO_pin to control heating element
        '''
        GPIO.output(self.gpio_signal_pin, self.threshold_flag)

    def get_temp(self):
        # Accesses raw temperature data in the form of a 2 line string from the DS18B20 Sensor
        # Uses string manipulation & typecasting to retrieve the temperature reading
        try:

            with open(self.sensor_ID, 'r') as f:
                lines = f.readlines()

                temp_in_string = lines[1].find('t=')
                temp_string = lines[1][temp_in_string + 2:]
                temp_c = float(temp_string) / 1000.0
                temp_f = (temp_c * 1.8) + 32

                self.current_temp = temp_f

                t = time.localtime()
                current_time = time.strftime("%H:%M:%S", t)
                self.temp_logs[current_time] = self.current_temp

        except FileNotFoundError:
            t = time.localtime()
            current_time = time.strftime("%H:%M:%S", t)
            error_logs[current_time] = self.sensor_ID
            print(f"Sensor file for {self.sensor_ID} not found.")

    def return_temp(self):
        return self.current_temp

    def return_status(self):
        return self.threshold_flag


def display_temp_on_lcd(zone_id, temperature, status):
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(f"Zone {zone_id}: {temperature:.1f}F")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("Heating: " + ("ON" if status else "OFF"))

# Rest of the code remains the same, just modify the arctic_spark function:


def arctic_spark(arr):
    '''
    Main runtime function that iterates through sensor_array of Temp_zones and
    calls the methods to
    1. receive data from corresponding sensor and update values
    2. compare temperature
    '''
    for zone in arr:
        zone.get_temp()
        zone.temp_check()
        zone.gpio_pin_output()
        print("Zone {} is currently {} degrees\n".format(
            zone.zone_ID, zone.return_temp()))
        if zone.return_status() == True:
            print("Actively Heating Zone {}\n".format(zone.zone_ID))

        # Display temperature data on the LCD
        display_temp_on_lcd(
            zone.zone_ID, zone.return_temp(), zone.return_status())

        time.sleep(3)


if __name__ == "__main__":

    sensor_array = []
    temp_zone_lows = []
    i = 0
    sensor_list_size = 0

    for sensor in sensor_locations:
        sensor_list_size += 1

    for pin in gpio_pin_array:
        GPIO.setup(pin, GPIO.OUT, initial=0)

    for x in range(0, sensor_list_size):
        user_input = int(
            input("Enter the minimum temperature(F) for zone {}:\t".format(x + 1)))
        temp_zone_lows.append(user_input)

    for sensor in sensor_locations:
        sensor_array.append(
            Temp_zone(sensor, (i + 1), gpio_pin_array[i], temp_zone_lows[i]))
        i += 1

    print("Initiating system operation\n")

    try:
        while True:
            arctic_spark(sensor_array)

    except KeyboardInterrupt:
        print("Operation Ended")

    # !!! To Do
    # Flutter/Python control integration
    # Implement multiple zone modes (8, 16, 24)
