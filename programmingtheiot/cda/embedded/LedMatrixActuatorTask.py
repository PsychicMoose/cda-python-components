#####
# 
# This class is part of the Programming the Internet of Things project.
# 

import logging
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.data.ActuatorData import ActuatorData

import threading
import time as time_module
from datetime import datetime

class LedMatrixActuatorTask():
    """LED Matrix actuator for displaying productivity information."""

    def __init__(self):
        self.esp_ip = "10.0.0.172"
        self.matrix_size = 64
        self.current_mode = "clock"
        self.alarm_active = False
        self.alarm_thread = None
        
        # Timer state
        self.timer_active = False
        self.timer_seconds_remaining = 0
        self.timer_thread = None
        self.timer_lock = threading.Lock()
        
        logging.info(f"LED Matrix actuator initialized (ESP32: {self.esp_ip})")
        
        # Show clock immediately on startup
        try:
            frame = self._create_clock_frame()
            self._send_frame(frame)
            logging.info("Initial clock display sent")
        except Exception as e:
            logging.error(f"Failed to send initial clock: {e}")
    
    def _send_frame(self, frame: np.ndarray) -> bool:
        """Send 64x64 RGB frame to ESP32"""
        # Convert RGB888 to RGB565
        data = bytearray(8192)
        for y in range(64):
            for x in range(64):
                r, g, b = frame[y, x]
                rgb565 = ((int(r) & 0xF8) << 8) | ((int(g) & 0xFC) << 3) | (int(b) >> 3)
                idx = (y * 64 + x) * 2
                data[idx] = rgb565 & 0xFF
                data[idx + 1] = (rgb565 >> 8) & 0xFF
        
        try:
            files = {'frame': ('frame.bin', bytes(data), 'application/octet-stream')}
            response = requests.post(
                f"http://{self.esp_ip}/frame", 
                files=files, 
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            logging.error(f"Failed to send frame to LED matrix: {e}")
            return False
    
    def _create_clock_frame(self) -> np.ndarray:
        """Create frame with current time at top"""
        img = Image.new('RGB', (64, 64), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        # Get current time
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        
        # Center text at top
        bbox = draw.textbbox((0, 0), time_str, font=font)
        text_width = bbox[2] - bbox[0]
        x = (64 - text_width) // 2
        
        draw.text((x, 5), time_str, fill=(0, 255, 0), font=font)
        
        return np.array(img)
    
    def _create_clock_with_timer_frame(self) -> np.ndarray:
        """Create frame with clock at top and timer below"""
        img = Image.new('RGB', (64, 64), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            clock_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
            timer_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        except:
            clock_font = ImageFont.load_default()
            timer_font = ImageFont.load_default()
        
        # Draw clock at top
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        bbox = draw.textbbox((0, 0), time_str, font=clock_font)
        text_width = bbox[2] - bbox[0]
        x = (64 - text_width) // 2
        draw.text((x, 5), time_str, fill=(0, 255, 0), font=clock_font)
        
        # Draw timer below in blue
        with self.timer_lock:
            minutes = self.timer_seconds_remaining // 60
            seconds = self.timer_seconds_remaining % 60
            timer_str = f"{minutes:02d}:{seconds:02d}"
        
        bbox = draw.textbbox((0, 0), timer_str, font=timer_font)
        text_width = bbox[2] - bbox[0]
        x = (64 - text_width) // 2
        draw.text((x, 35), timer_str, fill=(0, 100, 255), font=timer_font)
        
        return np.array(img)
    
    def _create_alarm_frame(self) -> np.ndarray:
        """Create red alarm frame with text and creepy monitoring eye"""
        # Red background
        frame_rgb = np.zeros((64, 64, 3), dtype=np.uint8)
        frame_rgb[:, :] = [255, 0, 0]  # Solid red
        
        # Convert to PIL for drawing
        img = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(img)
        
        # Draw text at top with custom spacing
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
        except:
            font = ImageFont.load_default()
        
        # Manual positioning for each line
        lines = [
            ("      GET", 1),
            ("     BACK", 11),
            ("  TO WORK", 21)
        ]
        
        for text, y_pos in lines:
            draw.text((2, y_pos), text, fill=(255, 255, 0), font=font)
    
        
        # Draw creepy eye below (centered, larger)
        eye_center_x = 32
        eye_center_y = 42
        
        # Outer eye shape (almond/ellipse)
        # White of eye
        draw.ellipse([eye_center_x-18, eye_center_y-10, eye_center_x+18, eye_center_y+10], 
                    fill=(240, 240, 240), outline=(0, 0, 0), width=2)
        
        # Iris (blue/green creepy color)
        draw.ellipse([eye_center_x-10, eye_center_y-9, eye_center_x+10, eye_center_y+9], 
                    fill=(0, 150, 200))
        
        # Pupil (black, dilated for creepiness)
        draw.ellipse([eye_center_x-6, eye_center_y-6, eye_center_x+6, eye_center_y+6], 
                    fill=(0, 0, 0))
        
        # Highlight for depth (small white dot)
        draw.ellipse([eye_center_x-2, eye_center_y-3, eye_center_x+1, eye_center_y], 
                    fill=(255, 255, 255))
        
        # Veins/details for creepiness (red lines radiating)
        for angle in [30, 60, 120, 150, 210, 240, 300, 330]:
            import math
            rad = math.radians(angle)
            x1 = eye_center_x + int(8 * math.cos(rad))
            y1 = eye_center_y + int(6 * math.sin(rad))
            x2 = eye_center_x + int(16 * math.cos(rad))
            y2 = eye_center_y + int(9 * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=(180, 0, 0), width=1)
        
        return np.array(img)

    def _create_eye_blink_frame(self) -> np.ndarray:
        frame_rgb = np.zeros((64, 64, 3), dtype=np.uint8)
        frame_rgb[:, :] = [255, 0, 0]  # Solid red
        
        # Convert to PIL for drawing
        img = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(img)
        
        # Draw text at top with custom spacing
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
        except:
            font = ImageFont.load_default()
        
        # Manual positioning for each line
        lines = [
            ("      GET", 1),
            ("     BACK", 11),
            ("  TO WORK", 21)
        ]
        
        for text, y_pos in lines:
            draw.text((2, y_pos), text, fill=(255, 255, 0), font=font)
    
        
        # Closed eye (horizontal line with slight curve)
        eye_center_x = 32
        eye_center_y = 42
        
        # Draw closed eyelid
        draw.arc([eye_center_x-18, eye_center_y-3, eye_center_x+18, eye_center_y+3], 
                0, 180, fill=(0, 0, 0), width=3)
        
        # Eyelashes for effect
        for offset in [-12, -6, 0, 6, 12]:
            draw.line([(eye_center_x+offset, eye_center_y), 
                    (eye_center_x+offset, eye_center_y-5)], 
                    fill=(0, 0, 0), width=1)
        
        return np.array(img)

    def _timer_countdown_loop(self):
        """Background thread to count down timer - only when NOT in alarm state"""
        while self.timer_active:
            time_module.sleep(1)
            
            # Only decrement if NOT in alarm (focused time only)
            if not self.alarm_active:
                with self.timer_lock:
                    if self.timer_seconds_remaining > 0:
                        self.timer_seconds_remaining -= 1
                        remaining = self.timer_seconds_remaining
                    else:
                        # Timer finished!
                        logging.info("Work timer completed!")
                        self.timer_active = False
                        remaining = -1
                
                # Update display OUTSIDE the lock
                if remaining >= 0:
                    frame = self._create_clock_with_timer_frame()
                    self._send_frame(frame)
                    
                    # Log every minute
                    if remaining % 60 == 0:
                        mins = remaining // 60
                        logging.info(f"Timer: {mins} minutes remaining")
                elif remaining == -1:
                    # Flash completion
                    self._flash_completion()
                    frame = self._create_clock_frame()
                    self._send_frame(frame)
                    
    def _flash_completion(self):
        """Victory animation when timer completes"""
        # Create victory frame with smiley and text
        victory_frame = np.zeros((64, 64, 3), dtype=np.uint8)
        victory_frame[:, :] = [255, 255, 0]  # Yellow background
        
        img = Image.fromarray(victory_frame)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)
        except:
            font = ImageFont.load_default()
        
        # Draw "YOU DID IT!" text at top
        text_lines = [
            ("  YOU DID", 2),
            ("     IT!", 12)
        ]
        
        for text, y_pos in text_lines:
            draw.text((2, y_pos), text, fill=(0, 0, 0), font=font)
        
        # Draw big smiley face
        face_center_x = 32
        face_center_y = 42
        
        # Face outline (circle)
        draw.ellipse([face_center_x-15, face_center_y-15, face_center_x+15, face_center_y+15], 
                    outline=(0, 0, 0), width=2)
        
        # Left eye
        draw.ellipse([face_center_x-10, face_center_y-8, face_center_x-4, face_center_y-2], 
                    fill=(0, 0, 0))
        
        # Right eye
        draw.ellipse([face_center_x+4, face_center_y-8, face_center_x+10, face_center_y-2], 
                    fill=(0, 0, 0))
        
        # Big smile (arc)
        draw.arc([face_center_x-10, face_center_y-5, face_center_x+10, face_center_y+10], 
                0, 180, fill=(0, 0, 0), width=3)
        
        victory_frame = np.array(img)
        
        # Flash yellow/black 3 times, then hold victory screen
        black_frame = np.zeros((64, 64, 3), dtype=np.uint8)
        
        for _ in range(3):
            self._send_frame(victory_frame)
            time_module.sleep(0.4)
            self._send_frame(black_frame)
            time_module.sleep(0.4)
        
        # Hold victory screen for 3 seconds
        self._send_frame(victory_frame)
        time_module.sleep(300)

    def _start_timer(self, minutes: int):
        """Start work timer countdown"""
        # Stop existing timer if running
        self._stop_timer()
        
        with self.timer_lock:
            self.timer_seconds_remaining = minutes * 60
            self.timer_active = True
        
        # Start countdown thread
        self.timer_thread = threading.Thread(target=self._timer_countdown_loop, daemon=True)
        self.timer_thread.start()
        
        # Show initial timer display
        frame = self._create_clock_with_timer_frame()
        self._send_frame(frame)
        
        logging.info(f"Work timer started: {minutes} minutes")

    def _stop_timer(self):
        """Stop the timer"""
        if self.timer_active:
            self.timer_active = False
            if self.timer_thread:
                self.timer_thread.join(timeout=2)
            logging.info("Timer stopped")

    def _alarm_loop(self):
        """Background thread to alternate between clock and creepy eye alarm"""
        show_alarm = True
        blink_counter = 0
        
        while self.alarm_active:
            if show_alarm:
                # Every 6 cycles (3 seconds), make it blink
                if blink_counter % 6 == 5:
                    frame = self._create_eye_blink_frame()
                else:
                    frame = self._create_alarm_frame()
                blink_counter += 1
            else:
                # If timer is active, show clock with timer
                if self.timer_active:
                    frame = self._create_clock_with_timer_frame()
                else:
                    frame = self._create_clock_frame()
            
            self._send_frame(frame)
            show_alarm = not show_alarm
            time_module.sleep(0.5)
        
        # When alarm stops, return to appropriate display
        self.current_mode = "clock"
        if self.timer_active:
            self._send_frame(self._create_clock_with_timer_frame())
        else:
            self._send_frame(self._create_clock_frame())
        
    def _start_alarm(self):
        """Start alarm flashing"""
        if not self.alarm_active:
            self.alarm_active = True
            self.alarm_thread = threading.Thread(target=self._alarm_loop, daemon=True)
            self.alarm_thread.start()
            logging.info("Alarm started - flashing red")
    
    def _stop_alarm(self):
        """Stop alarm flashing"""
        if self.alarm_active:
            self.alarm_active = False
            if self.alarm_thread:
                self.alarm_thread.join(timeout=2)
            logging.info("Alarm stopped - returning to clock")
    
    def updateActuator(self, data: ActuatorData) -> ActuatorData:
        """Update LED matrix based on actuator command"""
        if not data:
            return None
        
        response = ActuatorData()
        response.updateData(data)
        response.setAsResponse()
        
        command = data.getCommand()
        state_data = data.getStateData()
        name = data.getName()
        
        logging.info(f"LED Matrix command: {command}, state: {state_data}, name: {name}")
        
        try:
            # Check for timer command
            if name == "WorkTimer" and state_data and state_data.startswith("TIMER:"):
                # Extract minutes from state data
                minutes = int(state_data.split(":")[1])
                self._start_timer(minutes)
                logging.info(f"!!! TIMER STARTING WITH {minutes} MINUTES !!!")
                response.setStatusCode(0)
                
            elif state_data == "ALARM":
                # Start flashing alarm
                self._start_alarm()
                response.setStatusCode(0)
                
            elif state_data == "CLEAR" or command == ConfigConst.COMMAND_OFF:
                # Stop alarm, return to clock
                self._stop_alarm()
                response.setStatusCode(0)
                
            elif command == ConfigConst.COMMAND_ON:
                # Show clock or timer
                self.current_mode = "clock"
                self._stop_alarm()  # Make sure alarm is off
                
                if self.timer_active:
                    frame = self._create_clock_with_timer_frame()
                else:
                    frame = self._create_clock_frame()
                    
                success = self._send_frame(frame)
                response.setStatusCode(0 if success else 1)
            else:
                logging.warning(f"Unknown command/state: {command}/{state_data}")
                response.setStatusCode(1)
                
        except Exception as e:
            logging.error(f"LED Matrix actuator error: {e}")
            response.setStatusCode(1)
        
        return response