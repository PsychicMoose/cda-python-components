#####
# 
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
# 

import logging

from importlib import import_module

from apscheduler.schedulers.background import BackgroundScheduler

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.IDataMessageListener import IDataMessageListener

from programmingtheiot.cda.sim.SensorDataGenerator import SensorDataGenerator
from programmingtheiot.cda.sim.HumiditySensorSimTask import HumiditySensorSimTask
from programmingtheiot.cda.sim.TemperatureSensorSimTask import TemperatureSensorSimTask
from programmingtheiot.cda.sim.PressureSensorSimTask import PressureSensorSimTask

# Panopticon Desk sensors
from programmingtheiot.cda.embedded.LightI2cSensorAdapterTask import LightI2cSensorAdapterTask
from programmingtheiot.cda.embedded.NoiseSensorAdapterTask import NoiseSensorAdapterTask
from programmingtheiot.cda.embedded.CameraSensorAdapterTask import CameraSensorAdapterTask

logging.basicConfig(level=logging.INFO)

class SensorAdapterManager(object):
	"""
	Manager for coordinating all sensor adapters.
	"""

	def __init__(self):
		self.configUtil = ConfigUtil()
		
		self.pollRate = self.configUtil.getInteger(
			section = ConfigConst.CONSTRAINED_DEVICE, 
			key = ConfigConst.POLL_CYCLES_KEY, 
			defaultVal = ConfigConst.DEFAULT_POLL_CYCLES
		)
			
		self.useEmulator = self.configUtil.getBoolean(
			section = ConfigConst.CONSTRAINED_DEVICE, 
			key = ConfigConst.ENABLE_EMULATOR_KEY
		)
			
		self.locationID = self.configUtil.getProperty(
			section = ConfigConst.CONSTRAINED_DEVICE, 
			key = ConfigConst.DEVICE_LOCATION_ID_KEY, 
			defaultVal = ConfigConst.NOT_SET
		)
			
		if self.pollRate <= 0:
			self.pollRate = ConfigConst.DEFAULT_POLL_CYCLES
			
		self.scheduler = BackgroundScheduler()
		self.scheduler.add_job(
			self.handleTelemetry, 'interval', 
			seconds = self.pollRate, 
			max_instances = 2, 
			coalesce = True, 
			misfire_grace_time = 15
		)
		
		self.dataMsgListener = None
		self.humidityAdapter = None
		self.pressureAdapter = None
		self.tempAdapter = None
		
		# Panopticon Desk sensors
		self.lightAdapter = None
		self.noiseAdapter = None
		self.cameraAdapter = None

		self._initEnvironmentalSensorTasks()
		self._initPanopticonSensors()

	def handleTelemetry(self):
		# Original sensors
		humidityData = self.humidityAdapter.generateTelemetry()
		pressureData = self.pressureAdapter.generateTelemetry()
		tempData = self.tempAdapter.generateTelemetry()
		
		humidityData.setLocationID(self.locationID)
		pressureData.setLocationID(self.locationID)
		tempData.setLocationID(self.locationID)
		
		logging.debug('Generated humidity data: ' + str(humidityData))
		logging.debug('Generated pressure data: ' + str(pressureData))
		logging.debug('Generated temp data: ' + str(tempData))
		
		if self.dataMsgListener:
			self.dataMsgListener.handleSensorMessage(humidityData)
			self.dataMsgListener.handleSensorMessage(pressureData)
			self.dataMsgListener.handleSensorMessage(tempData)
		
		# Panopticon sensors
		if self.lightAdapter:
			lightData = self.lightAdapter.generateTelemetry()
			lightData.setLocationID(self.locationID)
			logging.debug('Generated light data: ' + str(lightData))
			if self.dataMsgListener:
				self.dataMsgListener.handleSensorMessage(lightData)
		
		if self.noiseAdapter:
			noiseData = self.noiseAdapter.generateTelemetry()
			noiseData.setLocationID(self.locationID)
			logging.debug('Generated noise data: ' + str(noiseData))
			if self.dataMsgListener:
				self.dataMsgListener.handleSensorMessage(noiseData)
		
		if self.cameraAdapter:
			cameraData = self.cameraAdapter.generateTelemetry()
			cameraData.setLocationID(self.locationID)
			logging.debug('Generated camera data: ' + str(cameraData))
			if self.dataMsgListener:
				self.dataMsgListener.handleSensorMessage(cameraData)
		
	def setDataMessageListener(self, listener: IDataMessageListener):
		if listener:
			self.dataMsgListener = listener

	def startManager(self) -> bool:
		logging.info("Started SensorAdapterManager.")
		
		if not self.scheduler.running:
			self.scheduler.start()
			return True
		else:
			logging.info("SensorAdapterManager scheduler already started. Ignoring.")
			return False
		
	def stopManager(self) -> bool:
		logging.info("Stopped SensorAdapterManager.")
		
		# Cleanup Panopticon sensors
		if self.noiseAdapter:
			self.noiseAdapter.cleanup()
		if self.cameraAdapter:
			self.cameraAdapter.cleanup()
		
		try:
			self.scheduler.shutdown()
			return True
		except:
			logging.info("SensorAdapterManager scheduler already stopped. Ignoring.")
			return False

	def _initPanopticonSensors(self):
		"""Initialize Panopticon Desk sensors"""
		try:
			logging.info("Initializing Panopticon Desk sensors...")
			
			# Light sensor (SenseHat)
			self.lightAdapter = LightI2cSensorAdapterTask()
			logging.info("Light sensor initialized")
			
			# Noise sensor (USB mic)
			self.noiseAdapter = NoiseSensorAdapterTask()
			logging.info("Noise sensor initialized")
			
			# Camera sensor (focus detection)
			self.cameraAdapter = CameraSensorAdapterTask()
			logging.info("Camera sensor initialized")
			
		except Exception as e:
			logging.error(f"Failed to initialize Panopticon sensors: {e}")
			# Don't raise - allow system to continue without these sensors

	def _initEnvironmentalSensorTasks(self):
		humidityFloor = self.configUtil.getFloat(
			section = ConfigConst.CONSTRAINED_DEVICE,
			key = ConfigConst.HUMIDITY_SIM_FLOOR_KEY,
			defaultVal = SensorDataGenerator.LOW_NORMAL_ENV_HUMIDITY
		)
		humidityCeiling = self.configUtil.getFloat(
			section = ConfigConst.CONSTRAINED_DEVICE,
			key = ConfigConst.HUMIDITY_SIM_CEILING_KEY,
			defaultVal = SensorDataGenerator.HI_NORMAL_ENV_HUMIDITY
		)

		pressureFloor = self.configUtil.getFloat(
			section = ConfigConst.CONSTRAINED_DEVICE,
			key = ConfigConst.PRESSURE_SIM_FLOOR_KEY,
			defaultVal = SensorDataGenerator.LOW_NORMAL_ENV_PRESSURE
		)
		pressureCeiling = self.configUtil.getFloat(
			section = ConfigConst.CONSTRAINED_DEVICE,
			key = ConfigConst.PRESSURE_SIM_CEILING_KEY,
			defaultVal = SensorDataGenerator.HI_NORMAL_ENV_PRESSURE
		)

		tempFloor = self.configUtil.getFloat(
			section = ConfigConst.CONSTRAINED_DEVICE,
			key = ConfigConst.TEMP_SIM_FLOOR_KEY,
			defaultVal = SensorDataGenerator.LOW_NORMAL_INDOOR_TEMP
		)
		tempCeiling = self.configUtil.getFloat(
			section = ConfigConst.CONSTRAINED_DEVICE,
			key = ConfigConst.TEMP_SIM_CEILING_KEY,
			defaultVal = SensorDataGenerator.HI_NORMAL_INDOOR_TEMP
		)

		if not self.useEmulator:
			# Simulator path
			self.dataGenerator = SensorDataGenerator()

			humidityData = self.dataGenerator.generateDailyEnvironmentHumidityDataSet(
				minValue = humidityFloor, maxValue = humidityCeiling, useSeconds = False
			)
			pressureData = self.dataGenerator.generateDailyEnvironmentPressureDataSet(
				minValue = pressureFloor, maxValue = pressureCeiling, useSeconds = False
			)
			tempData = self.dataGenerator.generateDailyIndoorTemperatureDataSet(
				minValue = tempFloor, maxValue = tempCeiling, useSeconds = False
			)

			self.humidityAdapter = HumiditySensorSimTask(dataSet = humidityData)
			self.pressureAdapter = PressureSensorSimTask(dataSet = pressureData)
			self.tempAdapter = TemperatureSensorSimTask(dataSet = tempData)
		else:
			# Emulator path
			try:
				heModule = import_module('programmingtheiot.cda.emulated.HumiditySensorEmulatorTask', 'HumiditySensorEmulatorTask')
				peModule = import_module('programmingtheiot.cda.emulated.PressureSensorEmulatorTask', 'PressureSensorEmulatorTask')
				teModule = import_module('programmingtheiot.cda.emulated.TemperatureSensorEmulatorTask', 'TemperatureSensorEmulatorTask')

				heClazz = getattr(heModule, 'HumiditySensorEmulatorTask')
				peClazz = getattr(peModule, 'PressureSensorEmulatorTask')
				teClazz = getattr(teModule, 'TemperatureSensorEmulatorTask')

				self.humidityAdapter = heClazz()
				self.pressureAdapter = peClazz()
				self.tempAdapter = teClazz()

				logging.info("Loaded SenseHAT emulator tasks for humidity, pressure, and temperature.")
			except Exception as e:
				logging.error("Failed to load SenseHAT emulator tasks: %s", e)
				raise