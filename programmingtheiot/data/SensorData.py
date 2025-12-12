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

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.data.BaseIotData import BaseIotData

class SensorData(BaseIotData):
	"""
		Data model for capturing sensor readings.

		This class extends BaseIotData and adds:
		- value: A float representing the measured sensor value.

		It provides methods to:
		- get and set the sensor value (updating the timestamp automatically),
		- merge or update this object from another SensorData instance 
		(via _handleUpdateData, useful for future multi-sensor fusion).
		
	"""
	
	def __init__(self, typeID: int = ConfigConst.DEFAULT_SENSOR_TYPE, name = ConfigConst.NOT_SET, d = None):
		super(SensorData, self).__init__(name = name, typeID = typeID, d = d)

		self.value = ConfigConst.DEFAULT_VAL

	def __str__(self):
		"""
		Returns a string representation of this instance, including the sensor value.
		"""
		baseStr = super().__str__()
		return f"{baseStr},value={self.value}"

	def getValue(self) -> float:
		return self.value
		
	def setValue(self, newVal: float):
		self.value = newVal
		self.updateTimeStamp()
			
	def _handleUpdateData(self, data):
		if data and isinstance(data, SensorData):
			self.value = data.getValue()

			