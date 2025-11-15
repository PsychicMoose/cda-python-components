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

class SensorResource(resource.Resource):
    """Resource for handling sensor data GET requests"""
    
    def __init__(self, dataMsgListener=None):
        super().__init__()
        self.dataMsgListener = dataMsgListener
        self.dataUtil = DataUtil()
        
    async def render_get(self, request):
        logging.info("GET request received for sensor resource")
        
        if self.dataMsgListener:
            # Try to get any sensor data from cache
            sensor_data = None
            # Try common sensor names
            for name in ["Temperature", "Humidity", "Pressure", None]:
                sensor_data = self.dataMsgListener.getLatestSensorDataFromCache(name)
                if sensor_data:
                    break
                    
            if sensor_data:
                payload = self.dataUtil.sensorDataToJson(sensor_data)
                logging.info(f"Returning sensor data: {payload[:100]}...")
            else:
                payload = '{"status": "No sensor data available yet"}'
                logging.info("No sensor data available")
        else:
            payload = '{"error": "No data listener configured"}'
            
        return aiocoap.Message(payload=payload.encode('utf-8'))

class SystemPerformanceResource(resource.Resource):
    """Resource for handling system performance GET requests"""
    
    def __init__(self, dataMsgListener=None):
        super().__init__()
        self.dataMsgListener = dataMsgListener
        self.dataUtil = DataUtil()
        
    async def render_get(self, request):
        logging.info("GET request received for system performance resource")
        
        if self.dataMsgListener:
            # Get system performance data from cache
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

class ActuatorCommandResource(resource.Resource):
    """Resource for handling actuator commands via PUT/POST"""
    
    def __init__(self, dataMsgListener=None):
        super().__init__()
        self.dataMsgListener = dataMsgListener
        self.dataUtil = DataUtil()
        
    async def render_get(self, request):
        logging.info("GET request received for actuator resource")
        
        if self.dataMsgListener:
            actuator_data = self.dataMsgListener.getLatestActuatorDataResponseFromCache()
            
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
            
            # Convert JSON to ActuatorData
            actuator_data = self.dataUtil.jsonToActuatorData(payload_str)
            
            if actuator_data and self.dataMsgListener:
                # Process the actuator command
                response_data = self.dataMsgListener.handleActuatorCommandMessage(actuator_data)
                
                if response_data:
                    response_payload = self.dataUtil.actuatorDataToJson(response_data)
                    logging.info("Actuator command processed successfully")
                else:
                    response_payload = '{"status": "Command processed"}'
            else:
                response_payload = '{"error": "Invalid command or no listener"}'
                
        except Exception as e:
            logging.error(f"Error processing PUT request: {e}")
            response_payload = f'{{"error": "{str(e)}"}}'
            
        return aiocoap.Message(payload=response_payload.encode('utf-8'))
    
    async def render_post(self, request):
        # POST behaves the same as PUT for actuator commands
        return await self.render_put(request)

# Add this new class after your other resource classes
class DiscoveryResource(resource.Resource):
    """Resource for handling .well-known/core discovery requests"""
    
    def __init__(self, root):
        super().__init__()
        self.root = root
        
    async def render_get(self, request):
        # Build discovery response in CoRE Link Format
        links = []
        
        # Add all registered resources
        links.append('</sensor>;rt="sensor"')
        links.append('</sysperf>;rt="sysperf"')
        links.append('</actuator>;rt="actuator"')
        links.append('</constrained-device/sensor-msg>;rt="sensor"')
        links.append('</constrained-device/sys-perf-msg>;rt="sysperf"')
        links.append('</constrained-device/actuator-cmd>;rt="actuator"')
        
        # Add PIOT standard paths that GDA expects
        links.append('</PIOT/ConstrainedDevice/SensorMsg>;rt="sensor"')
        links.append('</PIOT/ConstrainedDevice/SystemPerfMsg>;rt="sysperf"')
        links.append('</PIOT/ConstrainedDevice/ActuatorCmd>;rt="actuator"')
        
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
        
        logging.info(f"CoAP server configured for: {self.serverUri}")
        
    def startServer(self):
        """Start the CoAP server in a separate thread"""
        logging.info("Starting CoAP server...")
        
        if self.thread and self.thread.is_alive():
            logging.warning("Server already running")
            return
            
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        
        # Give it time to start
        threading.Event().wait(1.0)
        
        logging.info("\n\n***** CoAP server started *****")
        logging.info(f"Test endpoints:")
        logging.info(f"  GET {self.serverUri}/sensor")
        logging.info(f"  GET {self.serverUri}/sysperf")
        logging.info(f"  GET {self.serverUri}/actuator")
        logging.info(f"  PUT {self.serverUri}/actuator")
        
    def stopServer(self):
        """Stop the CoAP server"""
        logging.info("Stopping CoAP server...")
        
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            
        if self.thread:
            self.thread.join(timeout=5)
            
        logging.info("CoAP server stopped")
        
    def _run_server(self):
        """Run the async CoAP server in its own event loop"""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Run the async server
            self.loop.run_until_complete(self._async_server())
            
        except Exception as e:
            logging.error(f"Error in CoAP server: {e}")
            
    async def _async_server(self):
        """Async CoAP server setup and run"""
        try:
            # Create the resource tree
            root = resource.Site()
            
            # Add discovery resource
            root.add_resource(['.well-known', 'core'], DiscoveryResource(root))
            
            # Add resources with simple paths
            root.add_resource(['sensor'], SensorResource(self.dataMsgListener))
            root.add_resource(['sysperf'], SystemPerformanceResource(self.dataMsgListener))
            root.add_resource(['actuator'], ActuatorCommandResource(self.dataMsgListener))
            
            # Add resources with full paths too
            root.add_resource(['constrained-device', 'sensor-msg'], SensorResource(self.dataMsgListener))
            root.add_resource(['constrained-device', 'sys-perf-msg'], SystemPerformanceResource(self.dataMsgListener))
            root.add_resource(['constrained-device', 'actuator-cmd'], ActuatorCommandResource(self.dataMsgListener))
            
            # Add PIOT standard paths that match ResourceNameEnum
            root.add_resource(['PIOT', 'ConstrainedDevice', 'SensorMsg'], SensorResource(self.dataMsgListener))
            root.add_resource(['PIOT', 'ConstrainedDevice', 'SystemPerfMsg'], SystemPerformanceResource(self.dataMsgListener))
            root.add_resource(['PIOT', 'ConstrainedDevice', 'ActuatorCmd'], ActuatorCommandResource(self.dataMsgListener))
            
            # Create server context
            self.context = await aiocoap.Context.create_server_context(
                root, 
                bind=(self.host, self.port)
            )
            
            logging.info(f"AioCoAP server listening on {self.host}:{self.port}")
            
            # Run forever
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