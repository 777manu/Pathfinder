#Test to make sure the ultrasonic sensor is working

from gpiozero import DistanceSensor
from time import sleep
# Create ultrasonic sensor object
sensor = DistanceSensor(
echo=24,
trigger=23,
max_distance=2.0
)
print("Ultrasonic sensor test started")
print("Move your hand in front of the sensor")
while True:
distance_cm = sensor.distance * 100
print(f"Distance: {distance_cm:.1f} cm")
sleep(1)