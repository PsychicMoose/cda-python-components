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

from coapthon.resources.resource import Resource

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.ITelemetryDataListener import ITelemetryDataListener
from programmingtheiot.common.IDataMessageListener import IDataMessageListener

from programmingtheiot.data.DataUtil import DataUtil
from programmingtheiot.data.SensorData import SensorData

class GetTelemetryResourceHandler(Resource, ITelemetryDataListener):
	"""
	Observable resource that will collect telemetry based on the given
	name from the data message listener implementation.
	
	This extends the CoAPthon Resource class to handle GET requests
	for telemetry data.
	"""

	def __init__(self, name="TelemetryResource", coap_server=None):
		"""
		Initialize the telemetry resource handler.
		
		@param name The resource name
		@param coap_server The CoAP server instance
		"""
		super(GetTelemetryResourceHandler, self).__init__(name, coap_server, visible=True, observable=True)
		
		self.dataUtil = DataUtil()
		self.dataMsgListener = None
		
		# Set the payload content type to JSON
		self.content_type = "application/json"
		
		# Initialize with empty payload
		self.payload = "{}"
		
		# Store the latest sensor data
		self.latestData = None
		
		logging.info(f"Created GetTelemetryResourceHandler: {name}")
		
	def render_GET(self, request):
		"""
		Handle GET requests for telemetry data.
		
		@param request The CoAP request
		@return The resource with telemetry data payload
		"""
		logging.debug(f"GET request received for telemetry resource: {self.name}")
		
		# Try to get the latest data from the data message listener
		if self.dataMsgListener:
			# Get the latest sensor data from cache
			self.latestData = self.dataMsgListener.getLatestSensorDataFromCache()
			
			if self.latestData:
				# Convert to JSON
				self.payload = self.dataUtil.sensorDataToJson(self.latestData)
				logging.debug(f"Returning sensor data: {self.payload}")
			else:
				# Return empty JSON if no data available
				self.payload = "{}"
				logging.debug("No sensor data available")
		else:
			self.payload = "{}"
			logging.debug("No data message listener configured")
			
		return self
		
	def render_PUT(self, request):
		"""
		Handle PUT requests (not supported for telemetry).
		
		@param request The CoAP request
		@return The resource with error response
		"""
		logging.warning(f"PUT request not supported for telemetry resource: {self.name}")
		self.payload = '{"error": "PUT not supported for telemetry resource"}'
		return self
		
	def render_POST(self, request):
		"""
		Handle POST requests (not supported for telemetry).
		
		@param request The CoAP request
		@return The resource with error response
		"""
		logging.warning(f"POST request not supported for telemetry resource: {self.name}")
		self.payload = '{"error": "POST not supported for telemetry resource"}'
		return self
		
	def render_DELETE(self, request):
		"""
		Handle DELETE requests (not supported for telemetry).
		
		@param request The CoAP request
		@return The resource with error response
		"""
		logging.warning(f"DELETE request not supported for telemetry resource: {self.name}")
		self.payload = '{"error": "DELETE not supported for telemetry resource"}'
		return self
		
	def setDataMessageListener(self, listener: IDataMessageListener):
		"""
		Set the data message listener for retrieving cached data.
		
		@param listener The IDataMessageListener instance
		"""
		self.dataMsgListener = listener
		
	def onSensorDataUpdate(self, data: SensorData = None) -> bool:
		"""
		Handle sensor data updates (for observable pattern).
		
		@param data The updated SensorData
		@return boolean indicating success
		"""
		if data:
			self.latestData = data
			self.payload = self.dataUtil.sensorDataToJson(data)
			
			# Notify observers if this is an observable resource
			self.changed = True
			
			logging.debug(f"Sensor data updated for resource: {self.name}")
			return True
		
		return False