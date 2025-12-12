"""Test Panopticon Desk sensors and actuators"""
import logging
import time
from programmingtheiot.cda.system.SensorAdapterManager import SensorAdapterManager
from programmingtheiot.cda.system.ActuatorAdapterManager import ActuatorAdapterManager
from programmingtheiot.data.ActuatorData import ActuatorData
import programmingtheiot.common.ConfigConst as ConfigConst

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print("[Test] Initializing Panopticon Desk...")

sensorMgr = SensorAdapterManager()
actuatorMgr = ActuatorAdapterManager()

sensorMgr.startManager()

print("[Test] System running. Testing for 30 seconds...")
print("[Test] Move around, make noise, look at/away from camera")
print(f"[Test] Location ID: {sensorMgr.locationID}")

try:
    for i in range(6):
        time.sleep(5)
        print(f"\n[Test] {5 * (i+1)} seconds elapsed...")
        
        if i == 2:
            print("[Test] Sending RED alert to LED Matrix...")
            cmd = ActuatorData()
            cmd.setLocationID(sensorMgr.locationID)  # Use actual location ID
            cmd.setTypeID(ConfigConst.LED_MATRIX_ACTUATOR_TYPE)
            cmd.setCommand(ConfigConst.COMMAND_CUSTOM)
            cmd.setStateData("UNFOCUSED")
            actuatorMgr.sendActuatorCommand(cmd)
        elif i == 4:
            print("[Test] Sending GREEN confirmation to LED Matrix...")
            cmd = ActuatorData()
            cmd.setLocationID(sensorMgr.locationID)  # Use actual location ID
            cmd.setTypeID(ConfigConst.LED_MATRIX_ACTUATOR_TYPE)
            cmd.setCommand(ConfigConst.COMMAND_CUSTOM)
            cmd.setStateData("FOCUSED")
            actuatorMgr.sendActuatorCommand(cmd)

except KeyboardInterrupt:
    print("\n[Test] Stopping...")

sensorMgr.stopManager()
print("[Test] Test complete!")