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

from programmingtheiot.common.IDataMessageListener import IDataMessageListener
from programmingtheiot.common.ResourceNameEnum import ResourceNameEnum

from programmingtheiot.data.DataUtil import DataUtil
from programmingtheiot.data.ActuatorData import ActuatorData

class UpdateActuatorResourceHandler(Resource):
	"""
	Standard resource that will handle an incoming actuation command,
	and return the command response.
	
	This extends the CoAPthon Resource class to handle PUT/POST requests
	for actuator commands.
	"""

	def __init__(self, name="ActuatorCommandResource", coap_server=None, dataMsgListener: IDataMessageListener = None):
		"""
		Initialize the actuator command resource handler.
		
		@param name The resource name
		@param coap_server The CoAP server instance
		@param dataMsgListener The data message listener for handling commands
		"""
		super(UpdateActuatorResourceHandler, self).__init__(name, coap_server, visible=True, observable=False)
		
		self.dataUtil = DataUtil()
		self.dataMsgListener = dataMsgListener
		
		# Set the payload content type to JSON
		self.content_type = "application/json"
		
		# Initialize with empty payload
		self.payload = "{}"
		
		logging.info(f"Created UpdateActuatorResourceHandler: {name}")
		
	def render_GET(self, request):
		"""
		Handle GET requests for actuator status.
		
		@param request The CoAP request
		@return The resource with actuator status
		"""
		logging.debug(f"GET request received for actuator resource: {self.name}")
		
		# For GET requests, return the latest actuator response from cache
		if self.dataMsgListener:
			# Get the latest actuator response data from cache
			actuatorData = self.dataMsgListener.getLatestActuatorDataResponseFromCache()
			
			if actuatorData:
				self.payload = self.dataUtil.actuatorDataToJson(actuatorData)
				logging.debug(f"Returning actuator status: {self.payload}")
			else:
				self.payload = '{"status": "No actuator data available"}'
				logging.debug("No actuator data available")
		else:
			self.payload = '{"error": "No data message listener configured"}'
			
		return self
		
	def render_PUT(self, request):
		"""
		Handle PUT requests for actuator commands.
		
		@param request The CoAP request with actuator command
		@return The resource with command response
		"""
		logging.info(f"PUT request received for actuator resource: {self.name}")
		
		try:
			# Get the payload from the request
			if request.payload:
				payload_str = request.payload.decode('utf-8') if isinstance(request.payload, bytes) else request.payload
				logging.debug(f"Received actuator command payload: {payload_str}")
				
				# Convert JSON payload to ActuatorData
				actuatorData = self.dataUtil.jsonToActuatorData(payload_str)
				
				if actuatorData and self.dataMsgListener:
					# Send the actuator command via the data message listener
					# This will trigger handleActuatorCommandMessage in DeviceDataManager
					responseData = self.dataMsgListener.handleActuatorCommandMessage(actuatorData)
					
					if responseData:
						# Convert response to JSON
						self.payload = self.dataUtil.actuatorDataToJson(responseData)
						logging.info(f"Actuator command processed successfully: {actuatorData.getName()}")
					else:
						self.payload = '{"error": "Failed to process actuator command"}'
						logging.warning("Failed to process actuator command")
				else:
					self.payload = '{"error": "Invalid actuator data or no listener configured"}'
					logging.warning("Invalid actuator data or no data message listener")
			else:
				self.payload = '{"error": "No payload provided"}'
				logging.warning("No payload in PUT request")
				
		except Exception as e:
			error_msg = f"Error processing PUT request: {str(e)}"
			logging.error(error_msg)
			self.payload = f'{{"error": "{error_msg}"}}'
			
		return self
		
	def render_POST(self, request):
		"""
		Handle POST requests for actuator commands.
		
		@param request The CoAP request with actuator command
		@return The resource with command response
		"""
		logging.info(f"POST request received for actuator resource: {self.name}")
		
		try:
			# Get the payload from the request
			if request.payload:
				payload_str = request.payload.decode('utf-8') if isinstance(request.payload, bytes) else request.payload
				logging.debug(f"Received actuator command payload: {payload_str}")
				
				# Convert JSON payload to ActuatorData
				actuatorData = self.dataUtil.jsonToActuatorData(payload_str)
				
				if actuatorData and self.dataMsgListener:
					# Send the actuator command via the data message listener
					responseData = self.dataMsgListener.handleActuatorCommandMessage(actuatorData)
					
					if responseData:
						# Convert response to JSON
						self.payload = self.dataUtil.actuatorDataToJson(responseData)
						logging.info(f"Actuator command processed successfully: {actuatorData.getName()}")
					else:
						self.payload = '{"error": "Failed to process actuator command"}'
						logging.warning("Failed to process actuator command")
				else:
					self.payload = '{"error": "Invalid actuator data or no listener configured"}'
					logging.warning("Invalid actuator data or no data message listener")
			else:
				self.payload = '{"error": "No payload provided"}'
				logging.warning("No payload in POST request")
				
		except Exception as e:
			error_msg = f"Error processing POST request: {str(e)}"
			logging.error(error_msg)
			self.payload = f'{{"error": "{error_msg}"}}'
			
		return self
		
	def render_DELETE(self, request):
		"""
		Handle DELETE requests (not supported for actuator commands).
		
		@param request The CoAP request
		@return The resource with error response
		"""
		logging.warning(f"DELETE request not supported for actuator resource: {self.name}")
		self.payload = '{"error": "DELETE not supported for actuator resource"}'
		return self
		
	def setDataMessageListener(self, listener: IDataMessageListener):
		"""
		Set the data message listener for handling actuator commands.
		
		@param listener The IDataMessageListener instance
		"""
		self.dataMsgListener = listener
		logging.debug(f"Data message listener set for actuator resource: {self.name}")