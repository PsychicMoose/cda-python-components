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

from programmingtheiot.cda.connection.CoapClientConnector import CoapClientConnector
from programmingtheiot.cda.connection.MqttClientConnector import MqttClientConnector
from programmingtheiot.cda.connection.CoapServerAdapter import CoapServerAdapter


from programmingtheiot.cda.system.ActuatorAdapterManager import ActuatorAdapterManager
from programmingtheiot.cda.system.SensorAdapterManager import SensorAdapterManager
from programmingtheiot.cda.system.SystemPerformanceManager import SystemPerformanceManager

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.IDataMessageListener import IDataMessageListener
from programmingtheiot.common.ResourceNameEnum import ResourceNameEnum
from programmingtheiot.common.ISystemPerformanceDataListener import ISystemPerformanceDataListener
from programmingtheiot.common.ITelemetryDataListener import ITelemetryDataListener

from programmingtheiot.data.DataUtil import DataUtil
from programmingtheiot.data.ActuatorData import ActuatorData
from programmingtheiot.data.SensorData import SensorData
from programmingtheiot.data.SystemPerformanceData import SystemPerformanceData

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s:%(message)s', level=logging.DEBUG, force=True)

class DeviceDataManager(IDataMessageListener):
	"""
	Central data manager for the Constrained Device Application (CDA).

	This class acts as the hub for managing all device-level data operations.
	It implements IDataMessageListener, allowing it to receive and process messages
	from system performance managers, sensor managers, and actuator managers.

	Responsibilities:
	- Initialize and manage subsystem managers:
	- SystemPerformanceManager (CPU, memory metrics).
	- SensorAdapterManager (sensor data acquisition).
	- ActuatorAdapterManager (actuator control and command handling).
	- Handle callbacks for incoming sensor, actuator, and system performance data.
	- Cache latest data objects for quick retrieval (sensors, actuators, system metrics).
	- Apply on-device logic (e.g., HVAC temperature control thresholds).
	- Delegate transmission of data upstream via CoAP/MQTT clients (if enabled).
	- Provide extension points for telemetry and performance listeners.

	This class forms the "glue" between the CDA's local system state and external
	communication channels, ensuring consistent lifecycle management and message flow.
	"""
	
	def __init__(self):
		self.configUtil = ConfigUtil()
		
		self.enableSystemPerf = \
			self.configUtil.getBoolean( \
				section = ConfigConst.CONSTRAINED_DEVICE, key = ConfigConst.ENABLE_SYSTEM_PERF_KEY)
			
		self.enableSensing = \
			self.configUtil.getBoolean( \
				section = ConfigConst.CONSTRAINED_DEVICE, key = ConfigConst.ENABLE_SENSING_KEY)
		
		# NOTE: this can also be retrieved from the configuration file
		self.enableActuation = True
		
		self.sysPerfMgr = None
		self.sensorAdapterMgr = None
		self.actuatorAdapterMgr = None
		
		# Initialize caches for latest data
		self.sensorDataCache = {}
		self.actuatorResponseCache = {}
		self.sysPerfDataCache = {}
		
		# Initialize connection clients
		self.mqttClient = None
		self.coapClient = None
		self.coapServer = None
		
		# Initialize data utility
		self.dataUtil = DataUtil()
		
		if self.enableSystemPerf:
			self.sysPerfMgr = SystemPerformanceManager()
			self.sysPerfMgr.setDataMessageListener(self)
			logging.info("Local system performance tracking enabled")
		
		if self.enableSensing:
			self.sensorAdapterMgr = SensorAdapterManager()
			self.sensorAdapterMgr.setDataMessageListener(self)
			logging.info("Local sensor tracking enabled")
			
		if self.enableActuation:
			self.actuatorAdapterMgr = ActuatorAdapterManager(dataMsgListener = self)
			logging.info("Local actuation capabilities enabled")
		
		self.handleTempChangeOnDevice = \
			self.configUtil.getBoolean( \
				ConfigConst.CONSTRAINED_DEVICE, ConfigConst.HANDLE_TEMP_CHANGE_ON_DEVICE_KEY)
			
		self.triggerHvacTempFloor = \
			self.configUtil.getFloat( \
				ConfigConst.CONSTRAINED_DEVICE, ConfigConst.TRIGGER_HVAC_TEMP_FLOOR_KEY)
				
		self.triggerHvacTempCeiling = \
			self.configUtil.getFloat( \
				ConfigConst.CONSTRAINED_DEVICE, ConfigConst.TRIGGER_HVAC_TEMP_CEILING_KEY)
		
		# Enable MQTT client if configured
		self.enableMqttClient = self.configUtil.getBoolean(
			section=ConfigConst.CONSTRAINED_DEVICE,
			key=ConfigConst.ENABLE_MQTT_CLIENT_KEY
		)
		
		if self.enableMqttClient:
			logging.info("MQTT client support enabled.")
			self.mqttClient = MqttClientConnector()
			self.mqttClient.setDataMessageListener(self)
		
		# Enable CoAP server if configured
		self.enableCoapServer = self.configUtil.getBoolean(
			section=ConfigConst.CONSTRAINED_DEVICE,
			key=ConfigConst.ENABLE_COAP_SERVER_KEY
		)
		
		if self.enableCoapServer:
			logging.info("CoAP server support enabled.")
			self.coapServer = CoapServerAdapter(dataMsgListener = self)
		
	def getLatestActuatorDataResponseFromCache(self, name: str = None) -> ActuatorData:
		"""
		Retrieves the named actuator data (response) item from the internal data cache.
		
		@param name
		@return ActuatorData
		"""
		if name and name in self.actuatorResponseCache:
			return self.actuatorResponseCache[name]
		return None
		
	def getLatestSensorDataFromCache(self, name: str = None) -> SensorData:
		"""
		Retrieves the named sensor data item from the internal data cache.
		
		@param name
		@return SensorData
		"""
		if name and name in self.sensorDataCache:
			return self.sensorDataCache[name]
		return None
	
	def getLatestSystemPerformanceDataFromCache(self, name: str = None) -> SystemPerformanceData:
		"""
		Retrieves the named system performance data from the internal data cache.
		
		@param name
		@return SystemPerformanceData
		"""
		if name and name in self.sysPerfDataCache:
			return self.sysPerfDataCache[name]
		return None
	
	def handleActuatorCommandMessage(self, data: ActuatorData = None) -> ActuatorData:
		"""
		This callback method will be invoked by the connection that's handling
		an incoming ActuatorData command message.
		
		@param data The incoming ActuatorData command message.
		@return ActuatorData
		"""
		logging.info("Actuator command data: " + str(data))
		
		if data:
			logging.info("Processing actuator command message.")
			return self.actuatorAdapterMgr.sendActuatorCommand(data)
		else:
			logging.warning("Incoming actuator command is invalid (null). Ignoring.")
			return None
	
	def handleActuatorCommandResponse(self, data: ActuatorData = None) -> bool:
		"""
		Handle the response from an actuator after command execution.
		
		@param data The ActuatorData response from the actuator
		@return boolean
		"""
		if data:
			logging.debug("Incoming actuator response received (from actuator manager): " + str(data))
			
			# Store the data in the cache
			self.actuatorResponseCache[data.getName()] = data
			
			# Convert ActuatorData to JSON and get the msg resource
			actuatorMsg = self.dataUtil.actuatorDataToJson(data)
			resourceName = ResourceNameEnum.CDA_ACTUATOR_RESPONSE_RESOURCE
			
			# Delegate to the transmit function any potential upstream comm's
			self._handleUpstreamTransmission(resourceName = resourceName, msg = actuatorMsg)
			
			return True
		else:
			logging.warning("Incoming actuator response is invalid (null). Ignoring.")
			return False
		
	def handleIncomingMessage(self, resourceEnum: ResourceNameEnum, msg: str) -> bool:
		"""
		This callback method is generic and designed to handle any incoming string-based
		message, which will likely be JSON-formatted and need to be converted to the appropriate
		data type.
		
		@param resourceEnum The resource type
		@param msg The incoming JSON message
		@return boolean
		"""
		if msg:
			logging.info("Incoming message received for resource: " + str(resourceEnum))
			self._handleIncomingDataAnalysis(msg)
			return True
		else:
			logging.warning("Incoming message is invalid (null). Ignoring.")
			return False
	
	def handleSensorMessage(self, data: SensorData = None) -> bool:
		"""
		Handle incoming sensor data messages.
		
		@param data The SensorData message
		@return boolean
		"""
		if data:
			logging.debug("Incoming sensor data received (from sensor manager): " + str(data))
			
			# Store the data in the cache
			self.sensorDataCache[data.getName()] = data
			
			# Perform any local analysis
			self._handleSensorDataAnalysis(data = data)
			
			# Convert SensorData to JSON and get the msg resource
			sensorMsg = self.dataUtil.sensorDataToJson(data)
			resourceName = ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE
			
			# Delegate to the transmit function any potential upstream comm's
			self._handleUpstreamTransmission(resourceName = resourceName, msg = sensorMsg)
			
			return True
		else:
			logging.warning("Incoming sensor data is invalid (null). Ignoring.")
			return False

	def handleSystemPerformanceMessage(self, data: SystemPerformanceData = None) -> bool:
		"""
		Handle incoming system performance messages.
		
		@param data The SystemPerformanceData message
		@return boolean
		"""
		if data:
			logging.debug("Incoming system performance message received (from sys perf manager): " + str(data))
			
			# Store the data in the cache
			self.sysPerfDataCache[data.getName()] = data
			
			# Convert SystemPerformanceData to JSON and get the msg resource
			sysPerfMsg = self.dataUtil.systemPerformanceDataToJson(data)
			resourceName = ResourceNameEnum.CDA_SYSTEM_PERF_MSG_RESOURCE
			
			# Delegate to the transmit function any potential upstream comm's
			self._handleUpstreamTransmission(resourceName = resourceName, msg = sysPerfMsg)
			
			return True
		else:
			logging.warning("Incoming system performance data is invalid (null). Ignoring.")
			return False
	
	def setSystemPerformanceDataListener(self, listener: ISystemPerformanceDataListener = None):
		"""
		Set a listener for system performance data events.
		
		@param listener The ISystemPerformanceDataListener instance
		"""
		pass
			
	def setTelemetryDataListener(self, name: str = None, listener: ITelemetryDataListener = None):
		"""
		Set a listener for telemetry data events.
		
		@param name The name of the telemetry source
		@param listener The ITelemetryDataListener instance
		"""
		pass
			
	def startManager(self):
		"""
		Start the DeviceDataManager and all sub-managers.
		"""
		logging.info("Starting DeviceDataManager...")
		
		if self.sysPerfMgr:
			self.sysPerfMgr.startManager()
		
		if self.sensorAdapterMgr:
			self.sensorAdapterMgr.startManager()
			
		if self.mqttClient:
			# Connect to MQTT broker
			self.mqttClient.connectClient()
			
			# Subscribe to actuator command topic
			self.mqttClient.subscribeToTopic(
				resource = ResourceNameEnum.CDA_ACTUATOR_CMD_RESOURCE,
				callback = None,  # Uses the default callback in MqttClientConnector
				qos = ConfigConst.DEFAULT_QOS
			)
		
		if self.coapServer:
			# Start the CoAP server
			self.coapServer.startServer()
			
		logging.info("Started DeviceDataManager.")

	def stopManager(self):
		"""
		Stop the DeviceDataManager and all sub-managers.
		"""
		logging.info("Stopping DeviceDataManager...")
		
		if self.sysPerfMgr:
			self.sysPerfMgr.stopManager()
		
		if self.sensorAdapterMgr:	
			self.sensorAdapterMgr.stopManager()

		if self.mqttClient:
			# Unsubscribe from topics
			self.mqttClient.unsubscribeFromTopic(
				resource = ResourceNameEnum.CDA_ACTUATOR_CMD_RESOURCE
			)
			
			# Disconnect from broker
			self.mqttClient.disconnectClient()
		
		if self.coapServer:
			# Stop the CoAP server
			self.coapServer.stopServer()

		logging.info("Stopped DeviceDataManager.")
		
	def _handleIncomingDataAnalysis(self, msg: str):
		"""
		Call this from handleIncomingMessage() to determine if there's
		any action to take on the message. Steps to take:
		1) Validate msg: Most will be ActuatorData, but you may pass other info as well.
		2) Convert msg: Use DataUtil to convert if appropriate.
		3) Act on msg: Determine what - if any - action is required, and execute.
		"""
		try:
			# Try to parse as ActuatorData first
			actuatorData = self.dataUtil.jsonToActuatorData(msg)
			if actuatorData:
				logging.info("Converted incoming JSON to ActuatorData")
				self.handleActuatorCommandMessage(actuatorData)
		except Exception as e:
			logging.warning("Failed to parse incoming message as ActuatorData: " + str(e))
		
	def _handleSensorDataAnalysis(self, data: SensorData = None):
		"""
		Analyze sensor data and potentially trigger actuator commands.
		
		@param data The SensorData to analyze
		"""
		if self.handleTempChangeOnDevice and data.getTypeID() == ConfigConst.TEMP_SENSOR_TYPE:
			logging.info("Handle temp change: %s - type ID: %s", str(self.handleTempChangeOnDevice), str(data.getTypeID()))
			
			ad = ActuatorData(typeID = ConfigConst.HVAC_ACTUATOR_TYPE)
			
			if data.getValue() > self.triggerHvacTempCeiling:
				ad.setCommand(ConfigConst.COMMAND_ON)
				ad.setValue(self.triggerHvacTempCeiling)
			elif data.getValue() < self.triggerHvacTempFloor:
				ad.setCommand(ConfigConst.COMMAND_ON)
				ad.setValue(self.triggerHvacTempFloor)
			else:
				ad.setCommand(ConfigConst.COMMAND_OFF)
				
			# NOTE: ActuatorAdapterManager and its associated actuator
			# task implementations contain logic to avoid processing
			# duplicative actuator commands - for the purposes
			# of this exercise, the logic for filtering commands is
			# left to ActuatorAdapterManager and its associated actuator
			# task implementations, and not this function
			self.handleActuatorCommandMessage(ad)

	def _handleUpstreamTransmission(self, resourceName: ResourceNameEnum, msg: str):
		"""
		Call this from handleActuatorCommandResponse(), handleSensorMessage(), and handleSystemPerformanceMessage()
		to determine if the message should be sent upstream. Steps to take:
		1) Check connection: Is there a client connection configured (and valid) to a remote MQTT or CoAP server?
		2) Act on msg: If # 1 is true, send message upstream using one (or both) client connections.
		
		@param resourceName The resource name enum for the message type
		@param msg The JSON message to transmit
		"""
		logging.debug("Upstream transmission invoked for resource: " + str(resourceName))
		
		# Check if MQTT client is available and connected
		if self.mqttClient:
			try:
				# Publish the message to the appropriate topic
				success = self.mqttClient.publishMessage(
					resource = resourceName,
					msg = msg,
					qos = ConfigConst.DEFAULT_QOS
				)
				
				if success:
					logging.info("Successfully published message to MQTT broker for resource: " + str(resourceName))
				else:
					logging.warning("Failed to publish message to MQTT broker for resource: " + str(resourceName))
					
			except Exception as e:
				logging.error("Error publishing to MQTT: " + str(e))
		
		# Future: Add CoAP client transmission here when implemented
		if self.coapClient:
			# TODO: Implement CoAP transmission
			pass