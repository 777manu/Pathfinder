#Test to make sure the mosfet is working

from gpiozero import LED
from time import sleep
mosfet = LED(18) # LED class works for MOSFET control
while True:
print("MOSFET ON")
mosfet.on()
sleep(2)
print("MOSFET OFF")
mosfet.off()
sleep(2)
