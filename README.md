# Pathfinder: Vision-Guided Haptic Navigation Belt

**Pathfinder** is a wearable, edge-compute assistive navigation device designed to enhance spatial awareness for visually impaired users. It fuses ultrasonic distance sensing with real-time computer vision (YOLOv8) to translate complex environmental data into an intuitive "Tactile Language" via haptic feedback.

**Author:** Emmanuel Alase Obron  
**Institution:** The University of Roehampton  
**Degree:** BSc Computer Science  

---

##  Key Features

* **Semantic Haptics (The Tactile Language):** Unlike traditional white canes that only provide proximity alerts, Pathfinder tells the user *what* the object is. 
  *  **Humans (Dynamic):** "Heartbeat" double-pulse
  *  **Static Objects (Boxes/Chairs):** Solid, heavy vibration
  *  **Poles/Signage:** Rapid "staccato" clicking
  *  **Elevated Hazards:** High-to-low sweeping pulse
* **Asynchronous Multi-Threaded Pipeline:** Decouples the 5 FPS AI inference from the high-frequency UI/Haptic daemon threads (20+ Hz), ensuring zero-latency collision avoidance even under heavy compute loads.
* **Edge-AI Processing:** Runs completely offline on a Raspberry Pi 4 using an NCNN-optimized YOLOv8 model for maximum privacy and performance.
* **Multi-Zone Spatial Mapping:** 3 independent sensor-motor pairs provide Left, Center, and Right directional awareness.

---

##  Hardware Architecture (The "Mirror Bridge")

The system is built on a custom "Mirror Bridge" circuit that safely isolates 5V logic from high-current actuators.

* **Compute:** Raspberry Pi 4 Model B (running headless via `systemd`)
* **Vision:** Raspberry Pi Camera Module (CSI Ribbon)
* **Sensing:** 3x HC-SR04 Ultrasonic Sensors (Scaled to 3.3V via voltage dividers)
* **Actuation:** 3x DC Coreless Motors (1.5v-3v Waterproof Micro Vibration, 8000-24000rpm)
* **Power Control:** IRLZ34N MOSFET Transistors & 1N4007 Flyback Diodes

---

##  Software Stack

* **Language:** Python 3
* **Computer Vision:** OpenCV, YOLOv8 (Exported to NCNN)
* **Hardware Interfacing:** `gpiozero`, `RPi.GPIO`, `libcamera`
* **Concurrency:** Python `threading` module

### The Asynchronous Pipeline
To overcome ARM architecture bottlenecks, the software utilizes three parallel execution threads:
1. **Main Thread (30 FPS):** Pulls native frames via libcamera and saves to shared memory.
2. **AI Inference Thread (5 FPS):** Grabs the latest frame, downscales to 320x320, calculates semantics, and pushes labels to a hardware lock.
3. **Haptic Daemon Threads (20+ Hz):** Instantly monitors ultrasonic sensors and AI locks to adjust motor PWM scaling linearly based on distance.

---

##  Build Process & Prototype Testing

* **Video Demonstration:** [Watch the step-by-step creation and testing of the Pathfinder prototype](https://youtu.be/svJ_Te5VOBk)
*(This video covers the entire journey—from building the hardware step-by-step to the real-world testing of the finished prototype).*
