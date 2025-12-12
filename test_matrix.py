"""
Test LED Matrix - send simple patterns
"""
import numpy as np
import requests
import time

ESP32_IP = "10.0.0.172"
MATRIX_SIZE = 64

def send_frame(frame):
    """Send 64x64 RGB frame to ESP32 as RGB565"""
    # Convert RGB888 to RGB565
    data = bytearray(8192)  # 64*64*2 bytes
    for y in range(64):
        for x in range(64):
            r, g, b = frame[y, x]
            rgb565 = ((int(r) & 0xF8) << 8) | ((int(g) & 0xFC) << 3) | (int(b) >> 3)
            idx = (y * 64 + x) * 2
            data[idx] = rgb565 & 0xFF
            data[idx + 1] = (rgb565 >> 8) & 0xFF
    
    try:
        files = {'frame': ('frame.bin', bytes(data), 'application/octet-stream')}
        response = requests.post(f"http://{ESP32_IP}/frame", files=files, timeout=2)
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

print(f"[Matrix] Testing connection to {ESP32_IP}...")

# Test 1: Solid RED
print("[Matrix] Test 1: RED")
frame = np.zeros((64, 64, 3), dtype=np.uint8)
frame[:, :] = [255, 0, 0]  # Red
if send_frame(frame):
    print("[Matrix] ✓ RED sent successfully")
else:
    print("[Matrix] ✗ Failed to send RED")
time.sleep(2)

# Test 2: Solid GREEN
print("[Matrix] Test 2: GREEN")
frame[:, :] = [0, 255, 0]  # Green
if send_frame(frame):
    print("[Matrix] ✓ GREEN sent successfully")
else:
    print("[Matrix] ✗ Failed to send GREEN")
time.sleep(2)

# Test 3: Solid BLUE
print("[Matrix] Test 3: BLUE")
frame[:, :] = [0, 0, 255]  # Blue
if send_frame(frame):
    print("[Matrix] ✓ BLUE sent successfully")
else:
    print("[Matrix] ✗ Failed to send BLUE")
time.sleep(2)

# Test 4: Text "HI"
print("[Matrix] Test 4: Text")
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (64, 64), (0, 0, 0))
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
except:
    font = ImageFont.load_default()
draw.text((10, 16), "HI", fill=(255, 255, 255), font=font)
frame = np.array(img)
if send_frame(frame):
    print("[Matrix] ✓ Text sent successfully")
else:
    print("[Matrix] ✗ Failed to send text")

print("[Matrix] Test complete!")