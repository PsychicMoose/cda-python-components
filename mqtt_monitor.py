#!/usr/bin/env python3
"""
MQTT Traffic Monitor using tcpdump
This script captures and decodes MQTT packets to provide readable logs
for monitoring CDA-GDA communication during integration testing.

Usage: sudo python3 mqtt_monitor.py [interface]
Example: sudo python3 mqtt_monitor.py lo
"""

import subprocess
import sys
import signal
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any
import struct

class MQTTMonitor:
    """Monitor and decode MQTT traffic from tcpdump output"""
    
    # MQTT packet type codes
    MQTT_TYPES = {
        1: "CONNECT",
        2: "CONNACK", 
        3: "PUBLISH",
        4: "PUBACK",
        5: "PUBREC",
        6: "PUBREL",
        7: "PUBCOMP",
        8: "SUBSCRIBE",
        9: "SUBACK",
        10: "UNSUBSCRIBE",
        11: "UNSUBACK",
        12: "PINGREQ",
        13: "PINGRESP",
        14: "DISCONNECT"
    }
    
    # Common MQTT topics for PIOT
    PIOT_TOPICS = {
        "PIOT/GatewayDevice/MgmtStatusMsg": "GDA Management Status",
        "PIOT/ConstrainedDevice/ActuatorCmd": "CDA Actuator Command",
        "PIOT/ConstrainedDevice/ActuatorResponse": "CDA Actuator Response",
        "PIOT/ConstrainedDevice/SensorMsg": "CDA Sensor Message",
        "PIOT/ConstrainedDevice/SystemPerfMsg": "CDA System Performance",
        "PIOT/GatewayDevice/SystemPerfMsg": "GDA System Performance"
    }
    
    def __init__(self, interface: str = "lo"):
        self.interface = interface
        self.process: Optional[subprocess.Popen] = None
        self.log_file = f"mqtt_traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.stats = {
            "total_packets": 0,
            "publish_count": 0,
            "subscribe_count": 0,
            "connect_count": 0,
            "errors": 0
        }
        
    def start_capture(self):
        """Start tcpdump capture for MQTT traffic"""
        print(f"Starting MQTT traffic capture on interface: {self.interface}")
        print(f"Logging to: {self.log_file}")
        print("-" * 60)
        
        # tcpdump command to capture MQTT traffic (port 1883 for non-TLS)
        # Use -A for ASCII output and -l for line buffering
        cmd = [
            "tcpdump",
            "-i", self.interface,
            "-l",  # Line buffer
            "-A",  # Print packet in ASCII
            "-nn", # Don't resolve hosts/ports
            "tcp port 1883",  # MQTT default port
            "-s", "0"  # Capture full packet
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False  # Get bytes
            )
            
            self.monitor_traffic()
            
        except PermissionError:
            print("Error: This script requires root privileges.")
            print("Please run with: sudo python3 mqtt_monitor.py")
            sys.exit(1)
        except Exception as e:
            print(f"Error starting tcpdump: {e}")
            sys.exit(1)
    
    def monitor_traffic(self):
        """Monitor and decode MQTT packets from tcpdump output"""
        packet_buffer = []
        in_packet = False
        
        with open(self.log_file, 'w') as log:
            log.write(f"MQTT Traffic Monitor - Started at {datetime.now()}\n")
            log.write("=" * 60 + "\n\n")
            
            print("\n📊 Monitoring MQTT Traffic (Press Ctrl+C to stop)...")
            print("=" * 60)
            
            for line in iter(self.process.stdout.readline, b''):
                try:
                    line_str = line.decode('utf-8', errors='ignore')
                    
                    # Detect packet boundaries
                    if re.match(r'^\d{2}:\d{2}:\d{2}\.\d+', line_str):
                        # New packet starting
                        if packet_buffer:
                            self.process_packet(packet_buffer, log)
                        packet_buffer = [line_str]
                        in_packet = True
                    elif in_packet:
                        packet_buffer.append(line_str)
                        
                except Exception as e:
                    self.stats["errors"] += 1
                    continue
    
    def process_packet(self, packet_lines: list, log_file):
        """Process and decode a complete MQTT packet"""
        self.stats["total_packets"] += 1
        
        # Join all lines to analyze the packet
        packet_text = ''.join(packet_lines)
        
        # Extract timestamp and connection info
        timestamp_match = re.match(r'^(\d{2}:\d{2}:\d{2}\.\d+)', packet_lines[0])
        timestamp = timestamp_match.group(1) if timestamp_match else "Unknown"
        
        # Try to identify MQTT packet type and content
        mqtt_info = self.decode_mqtt_content(packet_text)
        
        if mqtt_info:
            self.display_mqtt_message(timestamp, mqtt_info, log_file)
    
    def decode_mqtt_content(self, packet_text: str) -> Optional[Dict[str, Any]]:
        """Decode MQTT packet content from the captured text"""
        info = {}
        
        # Look for MQTT-specific patterns
        # Check for PUBLISH packets with PIOT topics
        for topic, description in self.PIOT_TOPICS.items():
            if topic in packet_text:
                info["type"] = "PUBLISH"
                info["topic"] = topic
                info["description"] = description
                self.stats["publish_count"] += 1
                
                # Try to extract JSON payload
                json_match = re.search(r'(\{[^}]+\})', packet_text)
                if json_match:
                    try:
                        payload = json.loads(json_match.group(1))
                        info["payload"] = payload
                    except:
                        info["payload"] = "Binary/Non-JSON data"
                
                return info
        
        # Check for CONNECT packet
        if "MQTT" in packet_text or "MQIsdp" in packet_text:
            info["type"] = "CONNECT"
            self.stats["connect_count"] += 1
            
            # Try to extract client ID
            client_match = re.search(r'(GatewayDevice|ConstrainedDevice)[^\s]*', packet_text)
            if client_match:
                info["client_id"] = client_match.group(0)
            
            return info
        
        # Check for SUBSCRIBE
        if "SUBSCRIBE" in packet_text or any(topic in packet_text for topic in self.PIOT_TOPICS.keys()):
            if "SUBSCRIBE" in packet_text:
                info["type"] = "SUBSCRIBE"
                self.stats["subscribe_count"] += 1
                return info
        
        # Check for PINGREQ/PINGRESP
        if "PING" in packet_text:
            info["type"] = "PING"
            return info
        
        return None
    
    def display_mqtt_message(self, timestamp: str, mqtt_info: Dict[str, Any], log_file):
        """Display formatted MQTT message information"""
        msg_type = mqtt_info.get("type", "UNKNOWN")
        
        # Format output based on message type
        output = f"\n[{timestamp}] {msg_type}"
        
        if msg_type == "PUBLISH":
            output += f" - {mqtt_info.get('description', 'Unknown Topic')}"
            output += f"\n  Topic: {mqtt_info.get('topic', 'Unknown')}"
            
            payload = mqtt_info.get('payload')
            if isinstance(payload, dict):
                # Format sensor/actuator data
                if 'name' in payload:
                    output += f"\n  Device: {payload.get('name')}"
                if 'value' in payload:
                    output += f"\n  Value: {payload.get('value')}"
                if 'command' in payload:
                    output += f"\n  Command: {payload.get('command')}"
                if 'cpuUtil' in payload:
                    output += f"\n  CPU: {payload.get('cpuUtil'):.1f}%"
                if 'memUtil' in payload:
                    output += f"\n  Memory: {payload.get('memUtil'):.1f}%"
                    
        elif msg_type == "CONNECT":
            if 'client_id' in mqtt_info:
                output += f" - Client: {mqtt_info['client_id']}"
                
        elif msg_type == "SUBSCRIBE":
            output += " - Subscription Request"
        
        # Color coding for terminal output
        color_codes = {
            "PUBLISH": "\033[92m",    # Green
            "CONNECT": "\033[94m",    # Blue
            "SUBSCRIBE": "\033[93m",  # Yellow
            "PING": "\033[90m",       # Gray
            "UNKNOWN": "\033[91m"     # Red
        }
        
        color = color_codes.get(msg_type, "")
        reset = "\033[0m" if color else ""
        
        # Print to console with color
        print(f"{color}{output}{reset}")
        
        # Write to log file without color codes
        log_file.write(output + "\n")
        log_file.flush()
    
    def print_statistics(self):
        """Print capture statistics"""
        print("\n" + "=" * 60)
        print("📈 MQTT Traffic Statistics:")
        print(f"  Total Packets Captured: {self.stats['total_packets']}")
        print(f"  PUBLISH Messages: {self.stats['publish_count']}")
        print(f"  CONNECT Messages: {self.stats['connect_count']}")
        print(f"  SUBSCRIBE Messages: {self.stats['subscribe_count']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"  Log file: {self.log_file}")
    
    def stop_capture(self):
        """Stop the tcpdump capture"""
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        self.print_statistics()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Stopping MQTT monitor...")
    if monitor:
        monitor.stop_capture()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get network interface from command line or use default
    interface = sys.argv[1] if len(sys.argv) > 1 else "lo"
    
    # Create and start monitor
    monitor = MQTTMonitor(interface)
    
    print("🔍 MQTT Traffic Monitor for PIOT Integration Testing")
    print("=" * 60)
    print(f"This tool monitors MQTT communication between CDA and GDA")
    print(f"Interface: {interface}")
    print(f"Port: 1883 (MQTT default)")
    print("=" * 60)
    
    try:
        monitor.start_capture()
    except KeyboardInterrupt:
        monitor.stop_capture()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)