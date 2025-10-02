#####
# 
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
# 
# You may find it more helpful to your design to adjust the
# functionality, constants and interfaces (if there are any)
# provided within in order to meet the needs of your specific
# Programming the Internet of Things project.
# 

import logging
import random

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.data.SensorData import SensorData
from programmingtheiot.cda.sim.SensorDataGenerator import SensorDataSet

class BaseSensorSimTask():
	"""
	Abstract base class for simulating a sensor task.
	It can generate SensorData either randomly within a specified range
	or from a predefined dataset (SensorDataSet).
	Subclasses should implement getLatestTelemetry to return
	either the current SensorData instance or a copy.

	Attributes:
	- name: The name of the sensor.
	- typeID: The type identifier for the sensor.
	- dataSet: An optional SensorDataSet for predefined data.
	- minVal: Minimum value for random data generation.
	- maxVal: Maximum value for random data generation.
	- latestSensorData: The most recently generated SensorData instance.
	- dataSetIndex: Index to track the current position in the dataset.
	- useRandomizer: Flag to indicate if random data generation is used.	

	"""


	DEFAULT_MIN_VAL = ConfigConst.DEFAULT_VAL
	DEFAULT_MAX_VAL = 100.0
	
	def __init__(self, name: str = ConfigConst.NOT_SET, typeID: int = ConfigConst.DEFAULT_SENSOR_TYPE, dataSet: SensorDataSet = None, minVal: float = DEFAULT_MIN_VAL, maxVal: float = DEFAULT_MAX_VAL):
		self.dataSet = dataSet
		self.name = name
		self.typeID = typeID
		self.dataSetIndex = 0
		self.useRandomizer = False
		
		self.latestSensorData = None
		
		if not self.dataSet:
			self.useRandomizer = True
			self.minVal = minVal
			self.maxVal = maxVal
	
	def generateTelemetry(self) -> SensorData:
		sensorData = SensorData(typeID = self.getTypeID(), name = self.getName())
		sensorVal = ConfigConst.DEFAULT_VAL
		
		if self.useRandomizer:
			sensorVal = random.uniform(self.minVal, self.maxVal)
		else:
			sensorVal = self.dataSet.getDataEntry(index = self.dataSetIndex)
			self.dataSetIndex = self.dataSetIndex + 1
			
			if self.dataSetIndex >= self.dataSet.getDataEntryCount() - 1:
				self.dataSetIndex = 0
				
		sensorData.setValue(sensorVal)
		
		self.latestSensorData = sensorData
		
		return self.latestSensorData
	
	def getTelemetryValue(self) -> float:
		if not self.latestSensorData:
			self.generateTelemetry()
		
		return self.latestSensorData.getValue()
		
	def getLatestTelemetry(self) -> SensorData:
		"""
		This can return the current SensorData instance or a copy.
		"""
		pass
	
	def getName(self) -> str:
		return self.name
	
	def getTypeID(self) -> int:
		return self.typeID
