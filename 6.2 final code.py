import RPi.GPIO as GPIO
import time
import threading

# --- GPIO Configuration (BCM) ---
TRIG_PINS = [17, 27, 22]
ECHO_PINS = [18, 23, 24]
MOTOR_PINS = [16, 20, 21]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Initialize pins
for i in range(3):
    GPIO.setup(TRIG_PINS[i], GPIO.OUT)
    GPIO.setup(ECHO_PINS[i], GPIO.IN)
    GPIO.setup(MOTOR_PINS[i], GPIO.OUT)

# Setup PWM for motors (Frequency: 100Hz)
motors = [GPIO.PWM(pin, 100) for pin in MOTOR_PINS]
for m in motors:
    m.start(0)

# The "Talking Stick" Lock to prevent acoustic crosstalk
sensor_lock = threading.Lock()

def measure_distance(index):
    #Calculates distance, ensuring only one sensor fires at a time.
    
    # Wait until no other sensor is pinging
    with sensor_lock: 
        GPIO.output(TRIG_PINS[index], True)
        time.sleep(0.00001)
        GPIO.output(TRIG_PINS[index], False)

        pulse_start = time.time()
        pulse_end = time.time()
        
        # Timeout after 0.02s (prevents the thread from freezing)
        timeout = time.time() + 0.02

        while GPIO.input(ECHO_PINS[index]) == 0 and time.time() < timeout:
            pulse_start = time.time()
        while GPIO.input(ECHO_PINS[index]) == 1 and time.time() < timeout:
            pulse_end = time.time()

        # Add a tiny 10-millisecond delay before giving up the lock
        # This lets the physical sound waves "die out" in the room 
        time.sleep(0.01)

    duration = pulse_end - pulse_start
    distance = (duration * 34300) / 2 
    return distance

def haptic_logic(index):
    #Independently controls haptic feedback for a specific zone.
    while True:
        dist = measure_distance(index)
        
        # THE REALITY CHECK: Ignore standard HC-SR04 glitch values
        if dist < 2.0 or dist > 400.0:
            dist = 200.0 # Force a "safe" distance to keep the motor off
        
        # Intensity Mapping based on your custom distance thresholds
        if dist > 60:
            intensity = 0    # No vibration
        elif dist > 30:
            intensity = 10   # Weak vibration
        elif dist > 20:
            intensity = 20   # Medium vibration
        else:
            intensity = 30   # Strong vibration
            
        motors[index].ChangeDutyCycle(intensity)
        time.sleep(0.05)

# --- Main Thread Execution ---
print("Pathfinder Upgraded Prototype Online: 3-Zone Fusion Active")
try:
    threads = []
    for i in range(3):
        t = threading.Thread(target=haptic_logic, args=(i,))
        t.daemon = True
        t.start()
        threads.append(t)
    
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n\nTesting complete. Forcing pins LOW.")
    for i in range(3):
        motors[i].ChangeDutyCycle(0) 
        motors[i].stop()             
        GPIO.output(MOTOR_PINS[i], GPIO.LOW) # Actively drive to 0V
        
    time.sleep(0.5)
    print("System safely parked. Ghost eliminated.")
