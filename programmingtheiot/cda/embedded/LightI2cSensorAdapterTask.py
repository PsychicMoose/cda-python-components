#####
# 
# This class is part of the Programming the Internet of Things project.
# 

import logging
from sense_hat import SenseHat

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.data.SensorData import SensorData

class LightI2cSensorAdapterTask():
    """
    Light sensor using SenseHat color sensor.
    Reads RGB values and calculates perceived brightness.
    """

    def __init__(self):
        self.sense = SenseHat()
        self.sense.color.gain = 64
        self.sense.color.integration_cycles = 64
        logging.info("Light sensor initialized")
    
    def generateTelemetry(self) -> SensorData:
        """Generate sensor data with brightness value"""
        sensorData = SensorData()
        sensorData.setName(ConfigConst.LIGHT_SENSOR_NAME)
        sensorData.setTypeID(ConfigConst.LIGHT_SENSOR_TYPE)
        
        brightness = self.getTelemetryValue()
        sensorData.setValue(brightness)
        
        return sensorData
    
    def getTelemetryValue(self) -> float:
        """Get brightness value from color sensor"""
        try:
            r = self.sense.color.red
            g = self.sense.color.green
            b = self.sense.color.blue
            
            # Calculate perceived luminance
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            
            logging.debug(f"Light sensor: R={r}, G={g}, B={b}, Brightness={brightness:.2f}")
            return brightness
        except Exception as e:
            logging.error(f"Light sensor error: {e}")
            return 0.0