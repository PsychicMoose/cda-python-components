#####
# 
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
# 
# Copyright (c) 2020 - 2025 by Andrew D. King
# 

import logging
import unittest
import time
import json
from datetime import datetime

from programmingtheiot.cda.connection.MqttClientConnector import MqttClientConnector
from programmingtheiot.common.ResourceNameEnum import ResourceNameEnum
from programmingtheiot.data.DataUtil import DataUtil
from programmingtheiot.data.SensorData import SensorData

class MqttClientConnectorTest(unittest.TestCase):
	"""
	MQTT Performance test that works with current broker configuration
	"""
	NS_IN_MILLIS = 1000000
	MAX_TEST_RUNS = 10000
	
	@classmethod
	def setUpClass(self):
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		
		# Set up logging
		logging.basicConfig(
			format='%(asctime)s:%(module)s:%(levelname)s:%(message)s',
			level=logging.DEBUG,
			handlers=[
				logging.StreamHandler(),
				logging.FileHandler(f'mqtt_performance_{timestamp}.log')
			]
		)
		
		# Load existing results if they exist, or create new
		self.results_filename = 'mqtt_performance_results.json'
		try:
			with open(self.results_filename, 'r') as f:
				self.all_results = json.load(f)
				logging.info(f"Loaded existing results from {self.results_filename}")
		except:
			self.all_results = {
				'max_test_runs': MqttClientConnectorTest.MAX_TEST_RUNS,
				'test_runs': []
			}
			logging.info("Created new results file")
		
	def setUp(self):
		self.mqttClient = MqttClientConnector(clientID='CDAMqttClientPerformanceTest001')
		
		# Log current configuration
		config_info = {
			'timestamp': datetime.now().isoformat(),
			'tls_enabled': self.mqttClient.enableCrypt,
			'port': self.mqttClient.port,
			'host': self.mqttClient.host,
			'results': {}
		}
		
		logging.info("=" * 80)
		logging.info(f"MQTT Configuration: TLS={'Enabled' if self.mqttClient.enableCrypt else 'Disabled'}, Port={self.mqttClient.port}")
		logging.info("=" * 80)
		
		# Store this test run info
		self.current_run = config_info

	def tearDown(self):
		try:
			self.mqttClient.disconnectClient()
		except:
			pass
			
		# Save this test run to results
		if hasattr(self, 'current_run') and self.current_run.get('results'):
			self.__class__.all_results['test_runs'].append(self.current_run)
			self._saveResults()

	def testConnectAndDisconnect(self):
		startTime = time.time_ns()
		
		self.assertTrue(self.mqttClient.connectClient())
		self.assertTrue(self.mqttClient.disconnectClient())
		
		endTime = time.time_ns()
		elapsedMillis = (endTime - startTime) / self.NS_IN_MILLIS
		
		logging.info(f"Connect and Disconnect: {elapsedMillis:.2f} ms")
		self.current_run['results']['connect_disconnect'] = elapsedMillis
		
	def testPublishQoS0(self):
		self._execTestPublish(self.MAX_TEST_RUNS, 0)

	def testPublishQoS1(self):
		self._execTestPublish(self.MAX_TEST_RUNS, 1)

	def testPublishQoS2(self):
		self._execTestPublish(self.MAX_TEST_RUNS, 2)

	def _execTestPublish(self, maxTestRuns: int, qos: int):
		self.assertTrue(self.mqttClient.connectClient())
		
		sensorData = SensorData()
		payload = DataUtil().sensorDataToJson(sensorData)
		payloadLen = len(payload)
		
		startTime = time.time_ns()
		
		for seqNo in range(0, maxTestRuns):
			self.mqttClient.publishMessage(
				resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
				msg=payload,
				qos=qos
			)
			
		endTime = time.time_ns()
		elapsedMillis = (endTime - startTime) / self.NS_IN_MILLIS
		
		self.assertTrue(self.mqttClient.disconnectClient())
		
		logging.info(
			f"QoS {qos}: {elapsedMillis:.2f}ms for {maxTestRuns} messages "
			f"({elapsedMillis/maxTestRuns:.4f}ms per message)"
		)
		
		# Store results
		self.current_run['results'][f'qos_{qos}'] = {
			'elapsed_ms': elapsedMillis,
			'messages': maxTestRuns,
			'payload_size': payloadLen,
			'avg_per_msg': elapsedMillis/maxTestRuns
		}
		
		# If QoS > 0, compare to QoS 0
		if qos > 0 and 'qos_0' in self.current_run['results']:
			baseline = self.current_run['results']['qos_0']['elapsed_ms']
			diff = ((elapsedMillis/baseline) - 1) * 100
			logging.info(f"  -> {diff:+.1f}% vs QoS 0")

	def _saveResults(self):
		with open(self.__class__.results_filename, 'w') as f:
			json.dump(self.__class__.all_results, f, indent=2)
			
	@classmethod
	def tearDownClass(cls):
		"""Print comparison if we have multiple test runs"""
		if len(cls.all_results['test_runs']) > 1:
			logging.info("\n" + "=" * 80)
			logging.info("COMPARISON OF ALL TEST RUNS")
			logging.info("=" * 80)
			
			for i, run in enumerate(cls.all_results['test_runs']):
				tls_status = "TLS" if run['tls_enabled'] else "Non-TLS"
				logging.info(f"\nRun {i+1}: {tls_status} on port {run['port']} at {run['timestamp']}")
				
				if 'connect_disconnect' in run['results']:
					logging.info(f"  Connect/Disconnect: {run['results']['connect_disconnect']:.2f}ms")
				
				for qos in [0, 1, 2]:
					key = f'qos_{qos}'
					if key in run['results']:
						result = run['results'][key]
						logging.info(f"  QoS {qos}: {result['elapsed_ms']:.2f}ms")
			
			# If we have both TLS and non-TLS runs, show comparison
			tls_runs = [r for r in cls.all_results['test_runs'] if r['tls_enabled']]
			non_tls_runs = [r for r in cls.all_results['test_runs'] if not r['tls_enabled']]
			
			if tls_runs and non_tls_runs:
				# Get the most recent of each type
				tls = tls_runs[-1]['results']
				non_tls = non_tls_runs[-1]['results']
				
				logging.info("\n" + "=" * 80)
				logging.info("TLS vs Non-TLS Comparison (most recent runs)")
				logging.info("=" * 80)
				
				for test in ['connect_disconnect', 'qos_0', 'qos_1', 'qos_2']:
					if test in tls and test in non_tls:
						if test == 'connect_disconnect':
							tls_time = tls[test]
							non_tls_time = non_tls[test]
							label = "Connect/Disconnect"
						else:
							tls_time = tls[test]['elapsed_ms']
							non_tls_time = non_tls[test]['elapsed_ms']
							label = f"QoS {test[-1]}"
						
						overhead = ((tls_time/non_tls_time) - 1) * 100
						logging.info(f"{label}:")
						logging.info(f"  Non-TLS: {non_tls_time:.2f}ms")
						logging.info(f"  TLS:     {tls_time:.2f}ms")
						logging.info(f"  Overhead: {overhead:+.1f}%")
		
		logging.info(f"\nAll results saved to: {cls.results_filename}")

if __name__ == "__main__":
	unittest.main()