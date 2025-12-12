#!/usr/bin/env python3
"""
MQTT Protocol Packet Decoder using tcpdump
Captures and decodes all 14 MQTT control packet types
Requires: sudo privileges to run tcpdump
"""

import subprocess
import sys
import struct
import threading
import queue
from datetime import datetime
import time

# MQTT Control Packet Types
MQTT_PACKET_TYPES = {
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

# MQTT Connect Return Codes
CONNACK_CODES = {
    0: "Connection Accepted",
    1: "Unacceptable protocol version",
    2: "Identifier rejected",
    3: "Server unavailable",
    4: "Bad username or password",
    5: "Not authorized"
}

class MQTTDecoder:
    def __init__(self):
        self.packet_queue = queue.Queue()
        self.tcp_stream = {}  # Store TCP stream data
        
    def decode_remaining_length(self, data, offset):
        """Decode MQTT variable length encoding"""
        multiplier = 1
        value = 0
        idx = offset
        
        while idx < len(data):
            byte = data[idx]
            value += (byte & 0x7F) * multiplier
            if (byte & 0x80) == 0:
                break
            multiplier *= 128
            idx += 1
            if multiplier > 128 * 128 * 128:
                return None, idx
                
        return value, idx + 1
    
    def decode_string(self, data, offset):
        """Decode MQTT UTF-8 string"""
        if len(data) < offset + 2:
            return None, offset
        
        length = struct.unpack('>H', data[offset:offset+2])[0]
        if len(data) < offset + 2 + length:
            return None, offset
            
        string = data[offset+2:offset+2+length].decode('utf-8', errors='ignore')
        return string, offset + 2 + length
    
    def decode_connect(self, data, offset):
        """Decode CONNECT packet"""
        info = {}
        
        # Protocol Name
        proto_name, offset = self.decode_string(data, offset)
        info['protocol'] = proto_name
        
        if len(data) < offset + 4:
            return info
        
        # Protocol Level
        info['level'] = data[offset]
        offset += 1
        
        # Connect Flags
        flags = data[offset]
        info['clean_session'] = bool(flags & 0x02)
        info['will'] = bool(flags & 0x04)
        info['will_qos'] = (flags & 0x18) >> 3
        info['will_retain'] = bool(flags & 0x20)
        info['password'] = bool(flags & 0x40)
        info['username'] = bool(flags & 0x80)
        offset += 1
        
        # Keep Alive
        info['keep_alive'] = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        
        # Client ID
        client_id, offset = self.decode_string(data, offset)
        info['client_id'] = client_id
        
        # Will Topic and Message
        if info['will']:
            will_topic, offset = self.decode_string(data, offset)
            will_msg, offset = self.decode_string(data, offset)
            info['will_topic'] = will_topic
            info['will_message'] = will_msg
        
        # Username
        if info['username']:
            username, offset = self.decode_string(data, offset)
            info['username_val'] = username
        
        # Password
        if info['password']:
            password, offset = self.decode_string(data, offset)
            info['password_val'] = '***hidden***'
        
        return info
    
    def decode_connack(self, data, offset):
        """Decode CONNACK packet"""
        info = {}
        
        if len(data) < offset + 2:
            return info
        
        # Session Present flag
        info['session_present'] = bool(data[offset] & 0x01)
        offset += 1
        
        # Return Code
        return_code = data[offset]
        info['return_code'] = return_code
        info['return_msg'] = CONNACK_CODES.get(return_code, f"Unknown ({return_code})")
        
        return info
    
    def decode_publish(self, data, offset, flags):
        """Decode PUBLISH packet"""
        info = {}
        
        # QoS and flags
        info['dup'] = bool(flags & 0x08)
        info['qos'] = (flags & 0x06) >> 1
        info['retain'] = bool(flags & 0x01)
        
        # Topic Name
        topic, offset = self.decode_string(data, offset)
        info['topic'] = topic
        
        # Packet ID (only for QoS > 0)
        if info['qos'] > 0:
            if len(data) >= offset + 2:
                info['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
                offset += 2
        
        # Payload
        payload = data[offset:]
        try:
            info['payload'] = payload.decode('utf-8')
            info['payload_type'] = 'text'
        except:
            info['payload'] = payload.hex()
            info['payload_type'] = 'hex'
        
        return info
    
    def decode_subscribe(self, data, offset):
        """Decode SUBSCRIBE packet"""
        info = {}
        
        # Packet ID
        if len(data) >= offset + 2:
            info['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
            offset += 2
        
        # Topic Filters
        topics = []
        while offset < len(data):
            topic, offset = self.decode_string(data, offset)
            if topic and offset < len(data):
                qos = data[offset]
                topics.append({'topic': topic, 'qos': qos})
                offset += 1
            else:
                break
        
        info['topics'] = topics
        return info
    
    def decode_packet(self, data):
        """Main packet decoder"""
        try:
            if len(data) < 2:
                return None
            
            # Fixed Header
            byte1 = data[0]
            packet_type = (byte1 >> 4) & 0x0F
            flags = byte1 & 0x0F
            
            if packet_type not in MQTT_PACKET_TYPES:
                return None
            
            # Remaining Length
            remaining_length, offset = self.decode_remaining_length(data, 1)
            if remaining_length is None:
                return None
            
            result = {
                'type': MQTT_PACKET_TYPES[packet_type],
                'type_code': packet_type,
                'flags': flags,
                'remaining_length': remaining_length,
                'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3]
            }
            
            # Decode based on packet type
            if packet_type == 1:  # CONNECT
                result['details'] = self.decode_connect(data, offset)
            elif packet_type == 2:  # CONNACK
                result['details'] = self.decode_connack(data, offset)
            elif packet_type == 3:  # PUBLISH
                result['details'] = self.decode_publish(data, offset, flags)
            elif packet_type == 4:  # PUBACK
                if len(data) >= offset + 2:
                    result['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
            elif packet_type == 5:  # PUBREC
                if len(data) >= offset + 2:
                    result['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
            elif packet_type == 6:  # PUBREL
                if len(data) >= offset + 2:
                    result['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
            elif packet_type == 7:  # PUBCOMP
                if len(data) >= offset + 2:
                    result['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
            elif packet_type == 8:  # SUBSCRIBE
                result['details'] = self.decode_subscribe(data, offset)
            elif packet_type == 9:  # SUBACK
                if len(data) >= offset + 2:
                    result['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
                    result['return_codes'] = list(data[offset+2:])
            elif packet_type == 10:  # UNSUBSCRIBE
                if len(data) >= offset + 2:
                    result['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
                    topics = []
                    offset += 2
                    while offset < len(data):
                        topic, offset = self.decode_string(data, offset)
                        if topic:
                            topics.append(topic)
                    result['topics'] = topics
            elif packet_type == 11:  # UNSUBACK
                if len(data) >= offset + 2:
                    result['packet_id'] = struct.unpack('>H', data[offset:offset+2])[0]
            # PINGREQ (12) and PINGRESP (13) have no payload
            # DISCONNECT (14) has no payload
            
            return result
            
        except Exception as e:
            return None
    
    def print_packet(self, packet_info, direction=""):
        """Pretty print decoded packet"""
        print(f"\n[{packet_info['timestamp']}] {direction} {packet_info['type']} Packet")
        print(f"  Type Code: {packet_info['type_code']}")
        print(f"  Flags: 0x{packet_info['flags']:02x}")
        print(f"  Length: {packet_info['remaining_length']} bytes")
        
        if 'packet_id' in packet_info:
            print(f"  Packet ID: {packet_info['packet_id']}")
        
        if 'details' in packet_info:
            details = packet_info['details']
            
            if packet_info['type'] == 'CONNECT':
                print(f"  Protocol: {details.get('protocol', 'N/A')}")
                print(f"  Client ID: {details.get('client_id', 'N/A')}")
                print(f"  Clean Session: {details.get('clean_session', False)}")
                print(f"  Keep Alive: {details.get('keep_alive', 0)}s")
                if details.get('username'):
                    print(f"  Username: {details.get('username_val', 'N/A')}")
                if details.get('will'):
                    print(f"  Will Topic: {details.get('will_topic', 'N/A')}")
                    
            elif packet_info['type'] == 'CONNACK':
                print(f"  Session Present: {details.get('session_present', False)}")
                print(f"  Return Code: {details.get('return_msg', 'N/A')}")
                
            elif packet_info['type'] == 'PUBLISH':
                print(f"  Topic: {details.get('topic', 'N/A')}")
                print(f"  QoS: {details.get('qos', 0)}")
                print(f"  Retain: {details.get('retain', False)}")
                print(f"  DUP: {details.get('dup', False)}")
                if 'packet_id' in details:
                    print(f"  Packet ID: {details['packet_id']}")
                payload = details.get('payload', '')
                if len(payload) > 100:
                    payload = payload[:100] + '...'
                print(f"  Payload ({details.get('payload_type', 'unknown')}): {payload}")
                
            elif packet_info['type'] == 'SUBSCRIBE':
                print(f"  Topics:")
                for topic in details.get('topics', []):
                    print(f"    - {topic['topic']} (QoS: {topic['qos']})")
        
        if 'return_codes' in packet_info:
            print(f"  Return Codes: {packet_info['return_codes']}")
        
        if 'topics' in packet_info and packet_info['type'] == 'UNSUBSCRIBE':
            print(f"  Topics:")
            for topic in packet_info['topics']:
                print(f"    - {topic}")

def capture_packets(decoder, interface='any', port=1883):
    """Capture MQTT packets using tcpdump - listening only on specified port"""
    
    # Build tcpdump command to capture raw bytes
    cmd = [
        'tcpdump',
        '-i', interface,
        '-w', '-',  # Write to stdout
        '-U',       # Unbuffered
        '-s', '0',  # Capture full packet
        f'tcp port {port}'  # Only MQTT port
    ]
    
    print(f"Starting MQTT packet capture on port {port} only...")
    print("Press Ctrl+C to stop\n")
    print("Waiting for MQTT packets...\n")
    
    try:
        # Start tcpdump process
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        # Read pcap header (24 bytes)
        pcap_header = proc.stdout.read(24)
        
        while True:
            # Read packet header (16 bytes)
            pkt_header = proc.stdout.read(16)
            if len(pkt_header) < 16:
                break
            
            # Parse packet length
            pkt_len = struct.unpack('I', pkt_header[8:12])[0]
            
            # Read packet data
            pkt_data = proc.stdout.read(pkt_len)
            if len(pkt_data) < pkt_len:
                break
            
            # Parse Ethernet header (14 bytes)
            eth_header = pkt_data[:14]
            
            # Parse IP header (starts at byte 14)
            ip_header = pkt_data[14:34]
            ip_header_len = (ip_header[0] & 0x0F) * 4
            
            # Parse TCP header (starts after IP header)
            tcp_start = 14 + ip_header_len
            tcp_header = pkt_data[tcp_start:tcp_start + 20]
            tcp_header_len = ((tcp_header[12] >> 4) & 0x0F) * 4
            
            # Get source and destination ports
            src_port = struct.unpack('>H', tcp_header[0:2])[0]
            dst_port = struct.unpack('>H', tcp_header[2:4])[0]
            
            # TCP flags
            tcp_flags = tcp_header[13]
            
            # MQTT payload starts after TCP header
            mqtt_start = tcp_start + tcp_header_len
            mqtt_data = pkt_data[mqtt_start:]
            
            # Skip if no MQTT data
            if len(mqtt_data) == 0:
                continue
            
            # Determine direction
            if src_port == port:
                direction = "Broker->Client:"
            else:
                direction = "Client->Broker:"
            
            # Try to decode MQTT packets in the payload
            offset = 0
            while offset < len(mqtt_data):
                # Check if this looks like an MQTT packet
                if offset + 2 > len(mqtt_data):
                    break
                
                # Check for valid MQTT packet type
                packet_type = (mqtt_data[offset] >> 4) & 0x0F
                if packet_type < 1 or packet_type > 14:
                    break
                
                # Try to decode the packet
                packet = decoder.decode_packet(mqtt_data[offset:])
                if packet:
                    decoder.print_packet(packet, direction)
                    
                    # Move offset past this packet
                    packet_len = 1  # Fixed header byte
                    
                    # Calculate remaining length bytes
                    rem_len = 0
                    multiplier = 1
                    i = offset + 1
                    while i < len(mqtt_data):
                        byte = mqtt_data[i]
                        rem_len += (byte & 0x7F) * multiplier
                        packet_len += 1
                        if (byte & 0x80) == 0:
                            break
                        multiplier *= 128
                        i += 1
                    
                    packet_len += rem_len
                    offset += packet_len
                else:
                    break
    
    except KeyboardInterrupt:
        print("\n\nCapture stopped.")
        print("\nSummary: All captured MQTT packets have been decoded.")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to run with sudo privileges")
        print("Example: sudo python3 mqtt_decoder.py")
    finally:
        if 'proc' in locals():
            proc.terminate()

def main():
    # Check if running with appropriate privileges
    import os
    if os.geteuid() != 0 and sys.platform != 'win32':
        print("This script requires sudo privileges to capture packets.")
        print("Please run: sudo python3 mqtt_decoder.py")
        sys.exit(1)
    
    # Parse arguments
    interface = 'any'
    port = 1883
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        interface = sys.argv[2]
    
    print("="*60)
    print(" MQTT Protocol Packet Decoder")
    print("="*60)
    print(f"Interface: {interface}")
    print(f"Port: {port} (listening ONLY on this port)")
    print("="*60)
    
    decoder = MQTTDecoder()
    capture_packets(decoder, interface, port)

if __name__ == "__main__":
    main()