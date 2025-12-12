#####
# 
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
#

import json
import logging
from decimal import Decimal
from json import JSONEncoder

from programmingtheiot.data.ActuatorData import ActuatorData
from programmingtheiot.data.SensorData import SensorData
from programmingtheiot.data.SystemPerformanceData import SystemPerformanceData


class DataUtil():
	"""
	Utility class for serializing and deserializing IoT data objects
	(ActuatorData, SensorData, SystemPerformanceData) to and from JSON.
	"""

	def __init__(self, encodeToUtf8 = False):
		self.encodeToUtf8 = encodeToUtf8
		logging.info("Created DataUtil instance.")
	
	def actuatorDataToJson(self, data: ActuatorData = None, useDecForFloat: bool = False):
		if not data:
			logging.debug("ActuatorData is null. Returning empty string.")
			return ""
		return self._generateJsonData(obj = data, useDecForFloat = useDecForFloat)
	
	def jsonToActuatorData(self, jsonData: str = None, useDecForFloat: bool = False):
		if not jsonData:
			logging.warning("JSON data is empty or null. Returning null.")
			return None
		jsonStruct = self._formatDataAndLoadDictionary(jsonData, useDecForFloat)
		ad = ActuatorData()
		self._updateIotData(jsonStruct, ad)
		return ad

	def sensorDataToJson(self, data: SensorData = None, useDecForFloat: bool = False):
		if not data:
			logging.debug("SensorData is null. Returning empty string.")
			return ""
		return self._generateJsonData(obj = data, useDecForFloat = useDecForFloat)

	def systemPerformanceDataToJson(self, data: SystemPerformanceData = None, useDecForFloat: bool = False):
		if not data:
			logging.debug("SystemPerformanceData is null. Returning empty string.")
			return ""
		return self._generateJsonData(obj = data, useDecForFloat = useDecForFloat)

	def jsonToSensorData(self, jsonData: str = None, useDecForFloat: bool = False):
		if not jsonData:
			logging.warning("JSON data is empty or null. Returning null.")
			return None
		jsonStruct = self._formatDataAndLoadDictionary(jsonData, useDecForFloat)
		sd = SensorData()
		self._updateIotData(jsonStruct, sd)
		return sd

	def jsonToSystemPerformanceData(self, jsonData: str = None, useDecForFloat: bool = False):
		if not jsonData:
			logging.warning("JSON data is empty or null. Returning null.")
			return None
		jsonStruct = self._formatDataAndLoadDictionary(jsonData, useDecForFloat)
		sp = SystemPerformanceData()
		self._updateIotData(jsonStruct, sp)
		return sp

	def _updateIotData(self, jsonStruct, obj):
		# Update object attributes with values from parsed JSON
		varStruct = vars(obj)
		for key in jsonStruct:
			if key in varStruct:
				setattr(obj, key, jsonStruct[key])
			else:
				logging.warning("JSON data contains key not mappable to object: %s", key)

	def _formatDataAndLoadDictionary(self, jsonData: str, useDecForFloat: bool = False) -> dict:
		# Fix up Python-style JSON (quotes and bools) and load into a dict
		jsonData = jsonData.replace("\'", "\"").replace('False', 'false').replace('True', 'true')
		if useDecForFloat:
			jsonStruct = json.loads(jsonData, parse_float = Decimal)
		else:
			jsonStruct = json.loads(jsonData)
		return jsonStruct
		
	def _generateJsonData(self, obj, useDecForFloat: bool = False) -> str:
		# Convert an object into a JSON string (optionally UTF-8 encoded)
		if self.encodeToUtf8:
			jsonData = json.dumps(obj, cls = JsonDataEncoder).encode('utf8')
		else:
			jsonData = json.dumps(obj, cls = JsonDataEncoder, indent = 4)
		
		# Normalize quotes and booleans
		if jsonData:
			jsonData = jsonData.replace("\'", "\"").replace('False', 'false').replace('True', 'true')
		
		return jsonData


class JsonDataEncoder(JSONEncoder):
	# Custom encoder for serializing IoT data classes to JSON
	def default(self, o):
		return o.__dict__
