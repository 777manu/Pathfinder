#Concept (simple)
#● Far away → no vibration
#● Medium distance → weak vibration
#● Very close → strong vibration
#using PWM (pulse width modulation).

from gpiozero import DistanceSensor, PWMLED
from time import sleep
# Ultrasonic sensor
sensor = DistanceSensor(echo=24, trigger=23, max_distance=2.0)
# MOSFET-controlled motor
motor = PWMLED(18)
print("Distance → Vibration test running")
while True:
distance_cm = sensor.distance * 100
if distance_cm > 100:
motor.value = 0.0 # No vibration
elif distance_cm > 50:
motor.value = 0.3 # Weak vibration
elif distance_cm > 20:
motor.value = 0.6 # Medium vibration
else:
motor.value = 1.0 # Strong vibration
print(f"Distance: {distance_cm:.1f} cm | Motor strength: {motor.value}")
sleep(0.1)