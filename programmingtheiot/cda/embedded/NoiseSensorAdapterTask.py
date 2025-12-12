#####
# 
# This class is part of the Programming the Internet of Things project.
# 

import logging
import subprocess
import audioop
import numpy as np
import threading
import queue

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.data.SensorData import SensorData

class NoiseSensorAdapterTask():
    """
    Noise sensor using USB microphone.
    Continuously captures audio and calculates dB level.
    """

    def __init__(self):
        self.SAMPLE_RATE = 16000
        self.CHANNELS = 1
        self.FRAME_DURATION = 30  # ms
        self.FRAME_SIZE = int(self.SAMPLE_RATE * self.FRAME_DURATION / 1000)
        self.BYTES_PER_FRAME = self.FRAME_SIZE * self.CHANNELS * 2
        
        self.current_db = 0.0
        self.running = False
        self.audio_queue = queue.Queue(maxsize=10)
        
        # Start audio capture thread
        self._start_capture()
        logging.info("Noise sensor initialized")
    
    def _start_capture(self):
        """Start background audio capture"""
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def _capture_loop(self):
        """Background thread to continuously capture audio"""
        cmd = [
            "arecord", "-D", "plughw:CARD=Device,DEV=0",
            "-r", str(self.SAMPLE_RATE), "-f", "S16_LE", "-c", str(self.CHANNELS),
            "--buffer-time=1000000", "--period-time=100000", "-q"
        ]
        
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=self.BYTES_PER_FRAME * 2)
            
            while self.running:
                frame = proc.stdout.read(self.BYTES_PER_FRAME)
                if len(frame) < self.BYTES_PER_FRAME:
                    continue
                
                # Calculate RMS and dB
                rms = audioop.rms(frame, 2)
                if rms > 0:
                    db = 20 * np.log10(rms / 32768.0)
                else:
                    db = -96.0
                
                # Update current value (thread-safe with queue)
                if not self.audio_queue.full():
                    try:
                        self.audio_queue.put_nowait(db)
                    except:
                        pass
                
        except Exception as e:
            logging.error(f"Audio capture error: {e}")
        finally:
            if proc:
                proc.terminate()
    
    def generateTelemetry(self) -> SensorData:
        """Generate sensor data with noise level"""
        sensorData = SensorData()
        sensorData.setName(ConfigConst.NOISE_SENSOR_NAME)
        sensorData.setTypeID(ConfigConst.NOISE_SENSOR_TYPE)
        
        noise_level = self.getTelemetryValue()
        sensorData.setValue(noise_level)
        
        return sensorData
    
    def getTelemetryValue(self) -> float:
        """Get current noise level in dB"""
        try:
            # Get most recent value from queue
            while not self.audio_queue.empty():
                self.current_db = self.audio_queue.get_nowait()
            
            logging.debug(f"Noise level: {self.current_db:.1f} dB")
            return self.current_db
        except Exception as e:
            logging.error(f"Noise sensor error: {e}")
            return self.current_db
    
    def cleanup(self):
        """Stop audio capture"""
        self.running = False
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1)