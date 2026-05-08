import os
import sys
import argparse
import time
import cv2
import numpy as np
import threading
import RPi.GPIO as GPIO
from ultralytics import YOLO


#                                                           1. PATHFINDER HARDWARE CONFIGURATION

TRIG_PINS = [17, 27, 22]
ECHO_PINS = [18, 23, 24]
MOTOR_PINS = [16, 20, 21]
MAX_VIBRATION = 55  # Capped for safety/comfort

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for i in range(3):
    GPIO.setup(TRIG_PINS[i], GPIO.OUT)
    GPIO.setup(ECHO_PINS[i], GPIO.IN)
    GPIO.setup(MOTOR_PINS[i], GPIO.OUT)

motors = [GPIO.PWM(pin, 100) for pin in MOTOR_PINS]
for m in motors: m.start(0)

# Shared Telemetry
sensor_lock = threading.Lock()
vision_lock = threading.Lock() # New lock to prevent camera read/write crashes

current_distances = [200.0, 200.0, 200.0]
current_intensities = [0, 0, 0]
current_classes = ["none", "none", "none"]

# Shared Vision Variables
latest_frame = None
latest_detections = [] 


#                                                           2. HAPTIC & SENSOR THREADING LOGIC

def measure_distance(index):
    with sensor_lock: 
        GPIO.output(TRIG_PINS[index], True)
        time.sleep(0.00001)
        GPIO.output(TRIG_PINS[index], False)

        pulse_start, pulse_end = time.time(), time.time()
        timeout = time.time() + 0.02 

        while GPIO.input(ECHO_PINS[index]) == 0 and time.time() < timeout:
            pulse_start = time.time()
        while GPIO.input(ECHO_PINS[index]) == 1 and time.time() < timeout:
            pulse_end = time.time()

        time.sleep(0.01) 
    return ((pulse_end - pulse_start) * 34300) / 2 

def haptic_logic(index):
    global current_distances, current_intensities, current_classes
    
    while True:
        dist = measure_distance(index)
        detected_object = current_classes[index]
        
        if dist < 2.0 or dist > 400.0: dist = 200.0 
        if dist > 80:
            motors[index].ChangeDutyCycle(0)
            current_distances[index] = round(dist, 1)
            time.sleep(0.1)
            continue
            
        base_intensity = int(((100 - ((dist - 20) * 1.5)) / 100.0) * MAX_VIBRATION)
        if base_intensity > MAX_VIBRATION: base_intensity = MAX_VIBRATION
        if base_intensity < 0: base_intensity = 0

        current_distances[index] = round(dist, 1)

        # SEMANTIC VIBRATION PATTERNS
        if detected_object == "person":
            motors[index].ChangeDutyCycle(base_intensity)
            time.sleep(0.1)
            motors[index].ChangeDutyCycle(0)
            time.sleep(0.05)
            motors[index].ChangeDutyCycle(base_intensity)
            time.sleep(0.1)
            motors[index].ChangeDutyCycle(0)
            time.sleep(0.2) 
        elif detected_object in ["chair", "couch", "bed", "suitcase"]:
            motors[index].ChangeDutyCycle(base_intensity)
            time.sleep(0.3)
            motors[index].ChangeDutyCycle(0)
        elif detected_object in ["stop sign", "fire hydrant", "traffic light"]:
            motors[index].ChangeDutyCycle(base_intensity)
            time.sleep(0.05)
            motors[index].ChangeDutyCycle(0)
            time.sleep(0.05)
        elif detected_object == "elevated":
            motors[index].ChangeDutyCycle(base_intensity)
            time.sleep(0.15)
            motors[index].ChangeDutyCycle(base_intensity // 2) 
            time.sleep(0.15)
            motors[index].ChangeDutyCycle(0)
        else:
            motors[index].ChangeDutyCycle(base_intensity)
            time.sleep(0.1)
            motors[index].ChangeDutyCycle(0)
            time.sleep(dist / 200.0) 
            
        # Do not clear the class here anymore, let the AI thread manage it


#                                                           3. ASYNCHRONOUS YOLO AI THREAD

def ai_vision_worker():
    """Runs continuously in the background, grabbing the newest frame and finding objects."""
    global latest_frame, latest_detections, current_classes
    
    while True:
        # 1. Safely grab a copy of the newest frame
        with vision_lock:
            if latest_frame is None:
                time.sleep(0.05)
                continue
            frame_to_process = latest_frame.copy()
            
        # 2. Run the AI (Using imgsz=320 hack for double speed)
        results = model(frame_to_process, verbose=False)
        detections = results[0].boxes
        
        new_boxes = []
        new_classes = ["none", "none", "none"]
        
        for i in range(len(detections)):
            xyxy = detections[i].xyxy.cpu().numpy().squeeze()
            xmin, ymin, xmax, ymax = xyxy.astype(int)
            classidx = int(detections[i].cls.item())
            conf = detections[i].conf.item()
            classname = labels[classidx]
            
            if conf > args.thresh:
                # Add to drawing list
                new_boxes.append((xmin, ymin, xmax, ymax, classname, conf, classidx))
                
                # Spatial Mapping for Motors
                x_center = (xmin + xmax) / 2
                if x_center < (resW / 3): zone = 0 
                elif x_center < (resW * 0.66): zone = 1 
                else: zone = 2 
                    
                if ymax < (resH / 2): new_classes[zone] = "elevated"
                else: new_classes[zone] = classname
                    
        # 3. Update the shared variables so the UI and Motors can use them
        with vision_lock:
            latest_detections = new_boxes
            current_classes = new_classes


#                                                            4. MAIN SETUP & UI LOOP (Runs at 30 FPS)

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True)
parser.add_argument('--source', required=True)
parser.add_argument('--thresh', default=0.5, type=float)
parser.add_argument('--resolution', default="640x480")
args = parser.parse_args()

print(f"Loading YOLO Model: {args.model}...")
model = YOLO(args.model, task='detect')
labels = model.names

resW, resH = int(args.resolution.split('x')[0]), int(args.resolution.split('x')[1])
is_picamera = False

if 'usb' in args.source:
    cap_arg = int(args.source[3:])
    cap = cv2.VideoCapture(cap_arg, cv2.CAP_V4L2)
    cap.set(3, resW)
    cap.set(4, resH)
else:
    from picamera2 import Picamera2
    cap = Picamera2()
    cap.configure(cap.create_video_configuration(main={"format": 'XRGB8888', "size": (resW, resH)}))
    cap.start()
    is_picamera = True

bbox_colors = [(164,120,87), (68,148,228), (93,97,209), (178,182,133), (88,159,106), 
               (96,202,231), (159,124,168), (169,162,241), (98,118,150), (172,176,184)]

# Launch all Background Threads
print("Starting Haptic Threads...")
for i in range(3):
    t = threading.Thread(target=haptic_logic, args=(i,))
    t.daemon = True
    t.start()
    
print("Starting AI Vision Thread...")
ai_thread = threading.Thread(target=ai_vision_worker)
ai_thread.daemon = True
ai_thread.start()

print("\nPathfinder System Online. Press 'q' to quit.\n")

avg_frame_rate = 0
frame_rate_buffer = []

try:
    while True:
        t_start = time.perf_counter()
        
        # 1. Pull the raw frame instantly
        if is_picamera:
            frame_bgra = cap.capture_array()
            frame = cv2.cvtColor(np.copy(frame_bgra), cv2.COLOR_BGRA2BGR)
            ret = True if frame is not None else False
        else:
            ret, frame = cap.read()
        
        if not ret or frame is None:
            break 
            
        # 2. Safely share the frame with the AI, and grab the newest bounding boxes
        with vision_lock:
            latest_frame = frame.copy()
            boxes_to_draw = latest_detections.copy()
            
        # 3. Draw the Bounding Boxes
        for (xmin, ymin, xmax, ymax, classname, conf, classidx) in boxes_to_draw:
            color = bbox_colors[classidx % 10]
            cv2.rectangle(frame, (xmin, ymin), (xmax,ymax), color, 2)
            label_text = f'{classname}: {int(conf*100)}%'
            cv2.putText(frame, label_text, (xmin, ymin-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 4. Draw HUD Overlay
        cv2.rectangle(frame, (0, resH - 40), (resW, resH), (0, 0, 0), -1)
        hud_text = f"LEFT: {current_distances[0]}cm | CENTER: {current_distances[1]}cm | RIGHT: {current_distances[2]}cm"
        cv2.putText(frame, hud_text, (10, resH - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f'Objects: {len(boxes_to_draw)} | UI FPS: {avg_frame_rate:0.1f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        #cv2.imshow('Pathfinder Semantic Fusion', frame)

        # UI FPS Calculation
        frame_rate_calc = float(1/(time.perf_counter() - t_start))
        frame_rate_buffer.append(frame_rate_calc)
        if len(frame_rate_buffer) > 30: frame_rate_buffer.pop(0)
        avg_frame_rate = np.mean(frame_rate_buffer)

        #if cv2.waitKey(1) & 0xFF == ord('q'):
        #	   break

except KeyboardInterrupt:
    pass

finally:
    print("\nInitiating Safe Hardware Shutdown...")
    for i in range(3):
        motors[i].ChangeDutyCycle(0) 
        motors[i].stop()             
        GPIO.output(MOTOR_PINS[i], GPIO.LOW)
    time.sleep(0.5)
    if is_picamera: cap.stop()
    else: cap.release()
    cv2.destroyAllWindows()
