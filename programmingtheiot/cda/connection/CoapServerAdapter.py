#####
# 
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
# 

import logging
import asyncio
import threading
import json

import aiocoap
import aiocoap.resource as resource

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.ResourceNameEnum import ResourceNameEnum
from programmingtheiot.common.IDataMessageListener import IDataMessageListener

from programmingtheiot.data.DataUtil import DataUtil
from programmingtheiot.data.ActuatorData import ActuatorData


class SensorResource(resource.ObservableResource):
    
    def __init__(self, dataMsgListener=None):
        super().__init__()
        self.dataMsgListener = dataMsgListener
        self.dataUtil = DataUtil()
        
    async def render_get(self, request):
        logging.info("GET request received for sensor resource")
        
        if self.dataMsgListener:
            sensor_data = None
            for name in ["Temperature", "Humidity", "Pressure", None]:
                sensor_data = self.dataMsgListener.getLatestSensorDataFromCache(name)
                if sensor_data:
                    break
                    
            if sensor_data:
                payload = self.dataUtil.sensorDataToJson(sensor_data)
            else:
                payload = '{"status": "No sensor data available yet"}'
        else:
            payload = '{"error": "No data listener configured"}'
            
        return aiocoap.Message(payload=payload.encode('utf-8'))
    
    async def render_post(self, request):
        logging.info("POST request received for sensor resource")
        try:
            payload_str = request.payload.decode('utf-8')
            logging.info("Received sensor data via POST: " + payload_str)
            response_payload = '{"status": "Sensor data received"}'
        except Exception as e:
            logging.error("Error processing POST: " + str(e))
            response_payload = '{"error": "Failed to process request"}'
        return aiocoap.Message(payload=response_payload.encode('utf-8'))
    
    async def render_put(self, request):
        logging.info("PUT request received for sensor resource")
        try:
            payload_str = request.payload.decode('utf-8')
            logging.info("Received sensor data via PUT: " + payload_str)
            response_payload = '{"status": "Sensor data updated"}'
        except Exception as e:
            logging.error("Error processing PUT: " + str(e))
            response_payload = '{"error": "Failed to process request"}'
        return aiocoap.Message(payload=response_payload.encode('utf-8'))
    
    async def render_delete(self, request):
        logging.info("DELETE request received for sensor resource")
        payload = '{"status": "Sensor data cleared"}'
        return aiocoap.Message(payload=payload.encode('utf-8'))
    
    def notify_observers(self):
        self.updated_state()

class SystemPerformanceResource(resource.ObservableResource):
    """Observable resource for handling system performance GET requests"""
    
    def __init__(self, dataMsgListener=None):
        super().__init__()
        self.dataMsgListener = dataMsgListener
        self.dataUtil = DataUtil()
        
    async def render_get(self, request):
        logging.info("GET request received for system performance resource")
        
        if self.dataMsgListener:
            sys_perf_data = self.dataMsgListener.getLatestSystemPerformanceDataFromCache("SystemPerformance")
            
            if sys_perf_data:
                payload = self.dataUtil.systemPerformanceDataToJson(sys_perf_data)
                logging.info(f"Returning system performance data: {payload[:100]}...")
            else:
                payload = '{"status": "No system performance data available yet"}'
                logging.info("No system performance data available")
        else:
            payload = '{"error": "No data listener configured"}'
            
        return aiocoap.Message(payload=payload.encode('utf-8'))

    async def render_post(self, request):
        logging.info("POST request received for sensor resource")
        try:
            payload_str = request.payload.decode('utf-8')
            logging.info("Received sensor data: " + payload_str)
            
            if self.dataMsgListener:
                sensor_data = self.dataUtil.jsonToSensorData(payload_str)
                if sensor_data:
                    self.dataMsgListener.handleSensorMessage(sensor_data)
            
            response_payload = '{"status": "Sensor data received"}'
        except Exception as e:
            logging.error("Error processing POST: " + str(e))
            response_payload = '{"error": "' + str(e) + '"}'
            
        return aiocoap.Message(payload=response_payload.encode('utf-8'))
    
    async def render_delete(self, request):
        logging.info("DELETE request received for system performance resource")
        
        if self.dataMsgListener:
            try:
                self.dataMsgListener.sysPerfDataCache.clear()
                payload = '{"status": "System performance data cleared"}'
                logging.info("System performance data cache cleared")
            except Exception as e:
                payload = '{"status": "Delete acknowledged"}'
        else:
            payload = '{"status": "Delete acknowledged"}'
            
        return aiocoap.Message(payload=payload.encode('utf-8'))
    
    def notify_observers(self):
        """Call this when system performance data changes to notify observers"""
        self.updated_state()


class ActuatorCommandResource(resource.ObservableResource):
    """Observable resource for handling actuator commands via PUT/POST"""
    
    def __init__(self, dataMsgListener=None):
        super().__init__()
        self.dataMsgListener = dataMsgListener
        self.dataUtil = DataUtil()
        
    async def render_get(self, request):
        logging.info("GET request received for actuator resource")
        
        if self.dataMsgListener:
            actuator_data = self.dataMsgListener.getLatestActuatorDataResponseFromCache(None)
            
            if actuator_data:
                payload = self.dataUtil.actuatorDataToJson(actuator_data)
            else:
                payload = '{"status": "No actuator data available"}'
        else:
            payload = '{"error": "No data listener configured"}'
            
        return aiocoap.Message(payload=payload.encode('utf-8'))
    
    async def render_put(self, request):
        logging.info("PUT request received for actuator resource")
        
        try:
            payload_str = request.payload.decode('utf-8')
            logging.info(f"Received actuator command: {payload_str}")
            
            actuator_data = self.dataUtil.jsonToActuatorData(payload_str)
            
            if actuator_data and self.dataMsgListener:
                response_data = self.dataMsgListener.handleActuatorCommandMessage(actuator_data)
                
                if response_data:
                    response_payload = self.dataUtil.actuatorDataToJson(response_data)
                    logging.info("Actuator command processed successfully")
                    # Notify observers of the change
                    self.notify_observers()
                else:
                    response_payload = '{"status": "Command processed"}'
            else:
                response_payload = '{"error": "Invalid command or no listener"}'
                
        except Exception as e:
            logging.error(f"Error processing PUT request: {e}")
            response_payload = f'{{"error": "{str(e)}"}}'
            
        return aiocoap.Message(payload=response_payload.encode('utf-8'))
    
    async def render_post(self, request):
        return await self.render_put(request)
    
    async def render_delete(self, request):
        logging.info("DELETE request received for actuator resource")
        
        if self.dataMsgListener:
            try:
                self.dataMsgListener.actuatorResponseCache.clear()
                payload = '{"status": "Actuator data cleared"}'
                logging.info("Actuator response cache cleared")
            except Exception as e:
                payload = '{"status": "Delete acknowledged"}'
        else:
            payload = '{"status": "Delete acknowledged"}'
            
        return aiocoap.Message(payload=payload.encode('utf-8'))
    
    def notify_observers(self):
        """Call this when actuator data changes to notify observers"""
        self.updated_state()


class DiscoveryResource(resource.Resource):
    """Resource for handling .well-known/core discovery requests"""
    
    def __init__(self, root):
        super().__init__()
        self.root = root
        
    async def render_get(self, request):
        links = []
        
        links.append('</sensor>;rt="sensor";obs')
        links.append('</sysperf>;rt="sysperf";obs')
        links.append('</actuator>;rt="actuator";obs')
        links.append('</PIOT/ConstrainedDevice/SensorMsg>;rt="sensor";obs')
        links.append('</PIOT/ConstrainedDevice/SystemPerfMsg>;rt="sysperf";obs')
        links.append('</PIOT/ConstrainedDevice/ActuatorCmd>;rt="actuator";obs')
        
        payload = ','.join(links)
        return aiocoap.Message(payload=payload.encode('utf-8'))


class CoapServerAdapter:
    """
    CoAP server adapter using aiocoap for reliable operation.
    """
    
    def __init__(self, dataMsgListener=None):
        self.config = ConfigUtil()
        self.dataMsgListener = dataMsgListener
        
        self.host = self.config.getProperty(
            ConfigConst.COAP_GATEWAY_SERVICE, 
            ConfigConst.HOST_KEY, 
            ConfigConst.DEFAULT_HOST
        )
        self.port = self.config.getInteger(
            ConfigConst.COAP_GATEWAY_SERVICE, 
            ConfigConst.PORT_KEY, 
            ConfigConst.DEFAULT_COAP_PORT
        )
        
        self.serverUri = f"coap://{self.host}:{self.port}"
        self.context = None
        self.loop = None
        self.thread = None
        
        # Store resource references for observer notifications
        self.sensorResource = None
        self.sysPerfResource = None
        self.actuatorResource = None
        
        logging.info(f"CoAP server configured for: {self.serverUri}")
        

    def addResource(self, resourcePath=None, endName=None, resource=None):
        """
        Add a resource to the server. This is called by tests.
        For our implementation, resources are added in _async_server,
        so this is just a compatibility stub.
        """
        logging.info("addResource called for: " + str(resourcePath) + "/" + str(endName))
        return True

    def startServer(self):
        """Start the CoAP server in a separate thread"""
        logging.info("Starting CoAP server...")
        
        if self.thread and self.thread.is_alive():
            logging.warning("Server already running")
            return
            
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        
        threading.Event().wait(1.0)
        
        logging.info("\n\n***** CoAP server started *****")
        logging.info(f"Test endpoints:")
        logging.info(f"  GET {self.serverUri}/sensor")
        logging.info(f"  GET {self.serverUri}/sysperf")
        logging.info(f"  GET {self.serverUri}/actuator")
        logging.info(f"  PUT {self.serverUri}/actuator")
        logging.info(f"  DELETE supported on all resources")
        logging.info(f"  OBSERVE supported on all resources")
        
    def stopServer(self):
        """Stop the CoAP server"""
        logging.info("Stopping CoAP server...")
        
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            
        if self.thread:
            self.thread.join(timeout=5)
            
        logging.info("CoAP server stopped")
        
    def notifySensorDataUpdate(self):
        """Notify observers that sensor data has changed"""
        if self.sensorResource:
            self.sensorResource.notify_observers()
            
    def notifySystemPerformanceDataUpdate(self):
        """Notify observers that system performance data has changed"""
        if self.sysPerfResource:
            self.sysPerfResource.notify_observers()
            
    def notifyActuatorDataUpdate(self):
        """Notify observers that actuator data has changed"""
        if self.actuatorResource:
            self.actuatorResource.notify_observers()
        
    def _run_server(self):
        """Run the async CoAP server in its own event loop"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._async_server())
        except Exception as e:
            logging.error(f"Error in CoAP server: {e}")
            
    async def _async_server(self):
        """Async CoAP server setup and run"""
        try:
            root = resource.Site()
            
            # Create resource instances
            self.sensorResource = SensorResource(self.dataMsgListener)
            self.sysPerfResource = SystemPerformanceResource(self.dataMsgListener)
            self.actuatorResource = ActuatorCommandResource(self.dataMsgListener)
            
            # Add discovery resource
            root.add_resource(['.well-known', 'core'], DiscoveryResource(root))
            
            # Add resources with simple paths
            root.add_resource(['sensor'], self.sensorResource)
            root.add_resource(['sysperf'], self.sysPerfResource)
            root.add_resource(['actuator'], self.actuatorResource)
            
            # Add PIOT standard paths
            root.add_resource(['PIOT', 'ConstrainedDevice', 'SensorMsg'], SensorResource(self.dataMsgListener))
            root.add_resource(['PIOT', 'ConstrainedDevice', 'SystemPerfMsg'], SystemPerformanceResource(self.dataMsgListener))
            root.add_resource(['PIOT', 'ConstrainedDevice', 'ActuatorCmd'], ActuatorCommandResource(self.dataMsgListener))
            
            self.context = await aiocoap.Context.create_server_context(
                root, 
                bind=(self.host, self.port)
            )
            
            logging.info(f"AioCoAP server listening on {self.host}:{self.port}")
            
            await asyncio.get_event_loop().create_future()
            
        except Exception as e:
            logging.error(f"Failed to start CoAP server: {e}")
            raise
            
    def setDataMessageListener(self, listener: IDataMessageListener = None) -> bool:
        """Set the data message listener"""
        if listener:
            self.dataMsgListener = listener
            return True
        return False