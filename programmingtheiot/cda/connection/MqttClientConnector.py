import logging
import paho.mqtt.client as mqttClient
import time

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.IDataMessageListener import IDataMessageListener
from programmingtheiot.common.ResourceNameEnum import ResourceNameEnum
from programmingtheiot.cda.connection.IPubSubClient import IPubSubClient


class MqttClientConnector(IPubSubClient):

    def __init__(self, clientID: str = None):
        self.config = ConfigUtil()

        # Configuration
        self.host = self.config.getProperty(ConfigConst.MQTT_GATEWAY_SERVICE, ConfigConst.HOST_KEY)
        self.port = self.config.getInteger(ConfigConst.MQTT_GATEWAY_SERVICE, ConfigConst.PORT_KEY, ConfigConst.DEFAULT_MQTT_PORT)
        self.keepAlive = self.config.getInteger(ConfigConst.MQTT_GATEWAY_SERVICE, ConfigConst.KEEP_ALIVE_KEY, ConfigConst.DEFAULT_KEEP_ALIVE)
        self.qos = self.config.getInteger(ConfigConst.MQTT_GATEWAY_SERVICE, ConfigConst.DEFAULT_QOS_KEY, ConfigConst.DEFAULT_QOS)
        self.enableAuth = self.config.getBoolean(ConfigConst.MQTT_GATEWAY_SERVICE, ConfigConst.ENABLE_AUTH_KEY)
        self.enableCrypt = self.config.getBoolean(ConfigConst.MQTT_GATEWAY_SERVICE, ConfigConst.ENABLE_CRYPT_KEY)

        self.clientID = clientID if clientID else "CDAClient"
        self.dataMsgListener: IDataMessageListener = None

        # MQTT client
        self.mqttClient = mqttClient.Client(client_id=self.clientID, clean_session=True)
        self.mqttClient.on_connect = self.onConnect
        self.mqttClient.on_disconnect = self.onDisconnect
        self.mqttClient.on_message = self.onMessage
        self.mqttClient.on_publish = self.onPublish
        self.mqttClient.on_subscribe = self.onSubscribe

        # Log setup info
        logging.info(f"MQTT Client ID:   {self.clientID}")
        logging.info(f"MQTT Broker Host: {self.host}")
        logging.info(f"MQTT Broker Port: {self.port}")
        logging.info(f"MQTT Keep Alive:  {self.keepAlive}")

    # ----- Core Connection Methods -----

    def connectClient(self) -> bool:
        try:
            logging.info("Connecting to MQTT broker...")
            self.mqttClient.connect(self.host, self.port, self.keepAlive)
            self.mqttClient.loop_start()
            logging.info("Connected successfully.")
            return True
        except Exception as e:
            logging.error(f"MQTT connection failed: {e}")
            return False

    def disconnectClient(self) -> bool:
        try:
            self.mqttClient.loop_stop()
            self.mqttClient.disconnect()
            logging.info("Disconnected from MQTT broker.")
            return True
        except Exception as e:
            logging.error(f"Disconnection failed: {e}")
            return False

    # ----- Callbacks -----

    def onConnect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("MQTT connection established (rc=0)")
            logging.info(f"MQTT client connected to broker: {client}")
        else:
            logging.warning(f"MQTT connection failed: rc={rc}")

    def onDisconnect(self, client, userdata, rc):
        logging.info(f"MQTT client disconnected (rc={rc})")
        logging.info(f"MQTT client disconnected from broker: {client}")

    def onMessage(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8") if msg.payload else None
        if payload:
            logging.info(f"MQTT message received on {msg.topic}: {payload}")
        else:
            logging.info(f"MQTT message received on {msg.topic} with no payload.")

        if self.dataMsgListener:
            self.dataMsgListener.handleIncomingMessage(msg.topic, payload)

    def onPublish(self, client, userdata, mid):
        logging.info(f"MQTT message published. mid={mid}")

    def onSubscribe(self, client, userdata, mid, granted_qos):
        logging.info(f"MQTT client subscribed. mid={mid}, qos={granted_qos}")

    # ----- Topic Management -----

    def publishMessage(self, resource: ResourceNameEnum = None, msg: str = None, qos: int = None) -> bool:
        """
        Publishes a message to the given MQTT topic.
        
        Validates topic, message, and QoS. For QoS 1 and 2, waits briefly for acknowledgment.
        """
        # Check validity of resource (topic)
        if not resource:
            logging.warning('No topic specified. Cannot publish message.')
            return False

        # Check validity of message
        if not msg:
            logging.warning('No message specified. Cannot publish message to topic: ' + resource.value)
            return False

        # Set QoS to default if not specified or invalid
        if qos is None:
            qos = self.qos
        elif qos < 0 or qos > 2:
            qos = ConfigConst.DEFAULT_QOS

        try:
            # Publish message
            logging.info(f"Publishing message to topic {resource.value} with QoS {qos}")
            msgInfo = self.mqttClient.publish(topic=resource.value, payload=msg, qos=qos)
            
            # Only wait for publish on QoS > 0, with a timeout
            if qos > 0:
                # Wait up to 5 seconds for publish to complete
                msgInfo.wait_for_publish(timeout=5.0)
            
            logging.info(f"Message published to topic {resource.value}: {msg}")
            return True
        except Exception as e:
            logging.error(f"Publish failed: {e}")
            return False

    def subscribeToTopic(self, resource: ResourceNameEnum = None, callback=None, qos: int = None) -> bool:
        """
        Subscribes to the given MQTT topic, validating QoS and topic.
        """
        # Check validity of resource (topic)
        if not resource:
            logging.warning('No topic specified. Cannot subscribe.')
            return False

        # Set QoS to default if not specified or invalid
        if qos is None:
            qos = self.qos
        elif qos < 0 or qos > 2:
            qos = ConfigConst.DEFAULT_QOS

        try:
            logging.info(f'Subscribing to topic {resource.value}')
            self.mqttClient.subscribe(resource.value, qos)
            
            if callback:
                self.mqttClient.message_callback_add(resource.value, callback)
                
            return True
        except Exception as e:
            logging.error(f"Subscribe failed: {e}")
            return False

    def unsubscribeFromTopic(self, resource: ResourceNameEnum = None) -> bool:
        """
        Unsubscribes from the given MQTT topic, validating the topic.
        """
        # Check validity of resource (topic)
        if not resource:
            logging.warning('No topic specified. Cannot unsubscribe.')
            return False

        try:
            logging.info(f'Unsubscribing from topic {resource.value}')
            self.mqttClient.unsubscribe(resource.value)
            return True
        except Exception as e:
            logging.error(f"Unsubscribe failed: {e}")
            return False

    def setDataMessageListener(self, listener: IDataMessageListener = None) -> bool:
        """
        Sets the data message listener for handling incoming messages.
        """
        self.dataMsgListener = listener
        logging.info("DataMessageListener set.")
        return True