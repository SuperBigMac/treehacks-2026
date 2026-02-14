import serial
import time

PORT = "COM11"
BAUD = 9600
message = "2"

# initialize serial connection
ser = serial.Serial(port=PORT, baudrate=BAUD)
time.sleep(2)   # wait for Arduino to boot and reach loop()

# send message to Arduino
ser.write(message.encode("utf-8"))
time.sleep(1)
ser.write(message.encode("utf-8"))
time.sleep(1)
ser.write(message.encode("utf-8"))
time.sleep(1)

ser.close()
