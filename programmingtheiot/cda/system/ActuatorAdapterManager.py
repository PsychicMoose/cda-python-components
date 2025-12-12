#####
# 
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
# 

import logging
import time

from importlib import import_module

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.IDataMessageListener import IDataMessageListener

from programmingtheiot.data.ActuatorData import ActuatorData

from programmingtheiot.cda.sim.HvacActuatorSimTask import HvacActuatorSimTask
from programmingtheiot.cda.sim.HumidifierActuatorSimTask import HumidifierActuatorSimTask

# Panopticon Desk actuator
from programmingtheiot.cda.embedded.LedMatrixActuatorTask import LedMatrixActuatorTask

class ActuatorAdapterManager(object):
	"""
	Manager for coordinating all actuator adapters.
	"""
	
	def __init__(self, dataMsgListener: IDataMessageListener = None):
		self.dataMsgListener = dataMsgListener
		
		self.configUtil = ConfigUtil()
		
		self.useSimulator = self.configUtil.getBoolean(
			section = ConfigConst.CONSTRAINED_DEVICE, 
			key = ConfigConst.ENABLE_SIMULATOR_KEY
		)
		self.useEmulator = self.configUtil.getBoolean(
			section = ConfigConst.CONSTRAINED_DEVICE, 
			key = ConfigConst.ENABLE_EMULATOR_KEY
		)
		self.deviceID = self.configUtil.getProperty(
			section = ConfigConst.CONSTRAINED_DEVICE, 
			key = ConfigConst.DEVICE_LOCATION_ID_KEY, 
			defaultVal = ConfigConst.NOT_SET
		)
		self.locationID = self.configUtil.getProperty(
			section = ConfigConst.CONSTRAINED_DEVICE, 
			key = ConfigConst.DEVICE_LOCATION_ID_KEY, 
			defaultVal = ConfigConst.NOT_SET
		)
		
		self.humidifierActuator = None
		self.hvacActuator = None
		self.ledDisplayActuator = None
		
		# Panopticon Desk actuator
		self.ledMatrixActuator = None
		
		self._initEnvironmentalActuationTasks()
		self._initPanopticonActuators()


	def _initPanopticonActuators(self):
		"""Initialize Panopticon Desk actuators"""
		try:
			logging.info("Initializing Panopticon Desk actuators...")
			
			# LED Matrix actuator
			self.ledMatrixActuator = LedMatrixActuatorTask()
			logging.info("LED Matrix actuator initialized")
			
			# Start clock display thread
			self._start_clock_update_thread()
			
		except Exception as e:
			logging.error(f"Failed to initialize Panopticon actuators: {e}")

	def _start_clock_update_thread(self):
		"""Start background thread to update clock display"""
		def update_clock():
			while True:
				try:
					# Only update clock if no alarm is active
					if self.ledMatrixActuator and not self.ledMatrixActuator.alarm_active:
						frame = self.ledMatrixActuator._create_clock_frame()
						self.ledMatrixActuator._send_frame(frame)
				except Exception as e:
					logging.error(f"Clock update error: {e}")
				
				time.sleep(60)  # Update every minute
		
		import threading
		clock_thread = threading.Thread(target=update_clock, daemon=True)
		clock_thread.start()
		logging.info("Clock update thread started")


	def _initEnvironmentalActuationTasks(self):
		if not self.useEmulator:
			# Simulator path (default)
			self.humidifierActuator = HumidifierActuatorSimTask()
			self.hvacActuator = HvacActuatorSimTask()
			logging.info("Loaded simulated actuator tasks (HVAC, Humidifier).")
		else:
			try:
				# Humidifier emulator
				hueModule = import_module(
					'programmingtheiot.cda.emulated.HumidifierEmulatorTask',
					'HumidifierEmulatorTask'
				)
				hueClazz = getattr(hueModule, 'HumidifierEmulatorTask')
				self.humidifierActuator = hueClazz()

				# HVAC emulator
				hveModule = import_module(
					'programmingtheiot.cda.emulated.HvacEmulatorTask',
					'HvacEmulatorTask'
				)
				hveClazz = getattr(hveModule, 'HvacEmulatorTask')
				self.hvacActuator = hveClazz()

				# LED display emulator
				leModule = import_module(
					'programmingtheiot.cda.emulated.LedDisplayEmulatorTask',
					'LedDisplayEmulatorTask'
				)
				leClazz = getattr(leModule, 'LedDisplayEmulatorTask')
				self.ledDisplayActuator = leClazz()

				logging.info("Loaded SenseHAT emulator actuator tasks (HVAC, Humidifier, LED Display).")

			except Exception as e:
				logging.error("Failed to load actuator emulator tasks: %s", e)
				raise

	def _initPanopticonActuators(self):
		"""Initialize Panopticon Desk actuators"""
		try:
			logging.info("Initializing Panopticon Desk actuators...")
			
			# LED Matrix actuator
			self.ledMatrixActuator = LedMatrixActuatorTask()
			logging.info("LED Matrix actuator initialized")
			
		except Exception as e:
			logging.error(f"Failed to initialize Panopticon actuators: {e}")
			# Don't raise - allow system to continue without these actuators

	def sendActuatorCommand(self, data: ActuatorData) -> ActuatorData:
		if data and not data.isResponseFlagEnabled():
			# Check if the actuation event is destined for this device
			if data.getLocationID() == self.locationID:
				logging.info("Actuator command received for location ID %s. Processing...", str(data.getLocationID()))
				
				aType = data.getTypeID()
				responseData = None
				
				if aType == ConfigConst.HUMIDIFIER_ACTUATOR_TYPE and self.humidifierActuator:
					responseData = self.humidifierActuator.updateActuator(data)
				elif aType == ConfigConst.HVAC_ACTUATOR_TYPE and self.hvacActuator:
					responseData = self.hvacActuator.updateActuator(data)
				elif aType == ConfigConst.LED_DISPLAY_ACTUATOR_TYPE and self.ledDisplayActuator:
					responseData = self.ledDisplayActuator.updateActuator(data)
				elif aType == ConfigConst.LED_MATRIX_ACTUATOR_TYPE and self.ledMatrixActuator:
					responseData = self.ledMatrixActuator.updateActuator(data)
				else:
					logging.warning("No valid actuator type. Ignoring actuation for type: %s", data.getTypeID())

				return responseData
			else:
				logging.warning("Location ID doesn't match. Ignoring actuation: (me) %s != (you) %s", str(self.locationID), str(data.getLocationID()))
		else:
			logging.warning("Actuator request received. Message is empty or response. Ignoring.")
		
		return None

	def setDataMessageListener(self, listener: IDataMessageListener) -> bool:
		if listener:
			self.dataMsgListener = listener