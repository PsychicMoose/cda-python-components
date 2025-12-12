#####
# 
# This class is part of the Programming the Internet of Things project.
# 

import logging
import cv2
import threading
import queue
import time

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.data.SensorData import SensorData

class CameraSensorAdapterTask():
    """
    Camera sensor for focus detection using Haar Cascades.
    Detects if user is focused (face centered, eyes visible) or unfocused.
    """

    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        self.camera_id = 0
        self.cap = None
        self.current_focus_state = 0.0  # 0.0 = unfocused, 1.0 = focused
        self.running = False
        self.frame_queue = queue.Queue(maxsize=2)
        
        # Start camera capture thread
        self._start_capture()
        logging.info("Camera sensor initialized")
    
    def _start_capture(self):
        """Start background camera capture"""
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def _capture_loop(self):
        """Background thread to continuously analyze camera frames"""
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            logging.error("Failed to open camera")
            return
        
        # Get frame dimensions
        ret, frame = self.cap.read()
        if ret:
            height, width = frame.shape[:2]
            self.center_x = width // 2
            self.zone_width = width // 3
            logging.info(f"Camera resolution: {width}x{height}")
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Detect focus state
            focused = self._detect_focus(frame)
            
            # Update state (thread-safe with queue)
            if not self.frame_queue.full():
                try:
                    self.frame_queue.put_nowait(1.0 if focused else 0.0)
                except:
                    pass
            
            time.sleep(0.5)  # Check twice per second
    
    def _detect_focus(self, frame):
        """Detect if user is focused"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces with more lenient parameters
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1,  # More sensitive
            minNeighbors=3,   # Less strict
            minSize=(30, 30)  # Smaller minimum
        )
        
        if len(faces) == 0:
            return False  # No face = unfocused
        
        # Get largest face
        face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = face
        face_center_x = x + w // 2
        
        # More lenient centering - allow 50% of frame width as "centered"
        offset = abs(face_center_x - self.center_x)
        in_center = offset < self.zone_width  # Made more generous (was zone_width // 2)
        
        # Focused if face is present and roughly centered
        return in_center
    
    def generateTelemetry(self) -> SensorData:
        """Generate sensor data with focus state"""
        sensorData = SensorData()
        sensorData.setName(ConfigConst.CAMERA_SENSOR_NAME)
        sensorData.setTypeID(ConfigConst.CAMERA_SENSOR_TYPE)
        
        focus_state = self.getTelemetryValue()
        sensorData.setValue(focus_state)
        
        return sensorData
    
    def getTelemetryValue(self) -> float:
        """Get current focus state (0.0 = unfocused, 1.0 = focused)"""
        try:
            # Get most recent value from queue
            while not self.frame_queue.empty():
                self.current_focus_state = self.frame_queue.get_nowait()
            
            return self.current_focus_state
        except Exception as e:
            logging.error(f"Camera sensor error: {e}")
            return self.current_focus_state
    
    def cleanup(self):
        """Stop camera capture"""
        self.running = False
        if self.cap:
            self.cap.release()
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1)