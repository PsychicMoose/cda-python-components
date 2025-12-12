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
from programmingtheiot.data.SystemPerformanceData import SystemPerformanceData

class GetSystemPerformanceResourceHandler(Resource, ITelemetryDataListener):
	"""
	Observable resource that will collect system performance data based on the
	given name from the data message listener implementation.
	
	This extends the CoAPthon Resource class to handle GET requests
	for system performance data.
	"""

	def __init__(self, name="SystemPerformanceResource", coap_server=None):
		"""
		Initialize the system performance resource handler.
		
		@param name The resource name
		@param coap_server The CoAP server instance
		"""
		super(GetSystemPerformanceResourceHandler, self).__init__(name, coap_server, visible=True, observable=True)
		
		self.dataUtil = DataUtil()
		self.dataMsgListener = None
		
		# Set the payload content type to JSON
		self.content_type = "application/json"
		
		# Initialize with empty payload
		self.payload = "{}"
		
		# Store the latest system performance data
		self.latestData = None
		
		logging.info(f"Created GetSystemPerformanceResourceHandler: {name}")
		
	def render_GET(self, request):
		"""
		Handle GET requests for system performance data.
		
		@param request The CoAP request
		@return The resource with system performance data payload
		"""

		logging.info("=" * 50)
		logging.info("GET REQUEST RECEIVED IN SYSTEM PERF HANDLER!")
		logging.info(f"Request path: {request.uri_path}")
		logging.info(f"Request options: {request.options}")
		logging.info("=" * 50)
		
		logging.debug(f"GET request received for system performance resource: {self.name}")
    
		logging.debug(f"GET request received for system performance resource: {self.name}")
		
		# Try to get the latest data from the data message listener
		if self.dataMsgListener:
			# Get the latest system performance data from cache
			# Note: Using the default name for system performance data
			self.latestData = self.dataMsgListener.getLatestSystemPerformanceDataFromCache(name=ConfigConst.SYSTEM_PERF_NAME)
			
			if self.latestData:
				# Convert to JSON
				self.payload = self.dataUtil.systemPerformanceDataToJson(self.latestData)
				logging.debug(f"Returning system performance data: {self.payload}")
			else:
				# Return empty JSON if no data available
				self.payload = "{}"
				logging.debug("No system performance data available")
		else:
			self.payload = "{}"
			logging.debug("No data message listener configured")
			
		return self
		
	def render_PUT(self, request):
		"""
		Handle PUT requests (not supported for system performance).
		
		@param request The CoAP request
		@return The resource with error response
		"""
		logging.warning(f"PUT request not supported for system performance resource: {self.name}")
		self.payload = '{"error": "PUT not supported for system performance resource"}'
		return self
		
	def render_POST(self, request):
		"""
		Handle POST requests (not supported for system performance).
		
		@param request The CoAP request
		@return The resource with error response
		"""
		logging.warning(f"POST request not supported for system performance resource: {self.name}")
		self.payload = '{"error": "POST not supported for system performance resource"}'
		return self
		
	def render_DELETE(self, request):
		"""
		Handle DELETE requests (not supported for system performance).
		
		@param request The CoAP request
		@return The resource with error response
		"""
		logging.warning(f"DELETE request not supported for system performance resource: {self.name}")
		self.payload = '{"error": "DELETE not supported for system performance resource"}'
		return self
		
	def setDataMessageListener(self, listener: IDataMessageListener):
		"""
		Set the data message listener for retrieving cached data.
		
		@param listener The IDataMessageListener instance
		"""
		self.dataMsgListener = listener
		
	def onSystemPerformanceDataUpdate(self, data: SystemPerformanceData) -> bool:
		"""
		Handle system performance data updates (for observable pattern).
		
		@param data The updated SystemPerformanceData
		@return boolean indicating success
		"""
		if data:
			self.latestData = data
			self.payload = self.dataUtil.systemPerformanceDataToJson(data)
			
			# Notify observers if this is an observable resource
			self.changed = True
			
			logging.debug(f"System performance data updated for resource: {self.name}")
			return True
		
		return False