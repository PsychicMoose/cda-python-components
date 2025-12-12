"""
Simple USB mic test - capture audio and calculate noise level (dB)
"""
import subprocess
import audioop
import time
import numpy as np

# Audio config
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_DURATION = 30  # ms
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)
BYTES_PER_FRAME = FRAME_SIZE * CHANNELS * 2  # 16-bit = 2 bytes

# Start arecord process
cmd = [
    "arecord", "-D", "plughw:CARD=Device,DEV=0",
    "-r", str(SAMPLE_RATE), "-f", "S16_LE", "-c", str(CHANNELS),
    "--buffer-time=1000000", "--period-time=100000", "-q"
]

print("[Mic Test] Starting audio capture...")
print("[Mic Test] Make some noise to test! Press Ctrl+C to stop.")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=BYTES_PER_FRAME * 2)

try:
    while True:
        # Read one frame
        frame = proc.stdout.read(BYTES_PER_FRAME)
        if len(frame) < BYTES_PER_FRAME:
            continue
        
        # Calculate RMS (Root Mean Square) amplitude
        rms = audioop.rms(frame, 2)  # 2 = sample width in bytes
        
        # Convert to decibels (relative to max 16-bit value)
        if rms > 0:
            db = 20 * np.log10(rms / 32768.0)  # 32768 = max value for 16-bit
        else:
            db = -96.0  # Silence floor
        
        # Print bar graph
        normalized = max(0, min(50, int((db + 60) / 60 * 50)))  # Scale -60dB to 0dB as 0-50 chars
        bar = "█" * normalized
        print(f"\rNoise: {db:6.1f} dB [{bar:<50}]", end="", flush=True)
        
        time.sleep(0.1)  # Update 10 times per second

except KeyboardInterrupt:
    print("\n[Mic Test] Stopping...")
    proc.terminate()
    print("[Mic Test] Done!")